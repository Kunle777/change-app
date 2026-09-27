import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from app.database import get_db
from app.Users.dependencies import get_current_user
from app.Users.models import User
from app.savings.models import SavingsVault, PendingDeposit
from app.savings.service import ensure_user_has_dva, paystack_fee
from app.savings.schemas import VaultCreate, VaultResponse
from app.savings.service import determine_milestone_tier
from fastapi import Request
from decimal import Decimal
from sqlalchemy import select
from app.savings.webhook_security import verify_paystack_signature
from app.savings.models import SavingsTransaction, TransactionType, PendingDepositStatus
from app.savings.service import check_milestones
from app.savings.models import TransactionStatus
from app.savings.notifications import (
    notify_kyc_failed,
    notify_kyc_verified,
    notify_payout_confirmed,
    notify_payout_failed,
)
from app.savings.models import VaultStatus
from app.Users.models import KYCStatus
from app.Users.security import limiter
from app.savings.service import initiate_transfer, check_daily_withdrawal_cap, validate_customer_identity, withdraw_platform_revenue
from app.savings.schemas import BankAccountSetup
from app.Users.security import hash_secret
from app.Users.security import verify_secret
from app.savings.schemas import BankAccountChangeRequest
from app.database import AsyncSessionLocal

router = APIRouter(prefix="/api/savings", tags=["savings"])


@router.get("", response_model=list[VaultResponse])
async def list_vaults(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SavingsVault)
        .where(SavingsVault.user_id == current_user.id)
        .order_by(SavingsVault.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{vault_id}/deposit-intent")
async def create_deposit_intent(
    vault_id: str,
    amount: float,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vault = await db.get(SavingsVault, vault_id)
    if not vault or vault.user_id != current_user.id:
        raise HTTPException(404, "Vault not found")  # same IDOR pattern as get_task_by_id

    dva = await ensure_user_has_dva(current_user, current_user.email_from_token, db)

    fee = paystack_fee(Decimal(str(amount)))
    # gross-up shown to free-tier users, per the already-decided fee model —
    # premium absorbs this, branching on current_user.tier deferred to Day 8's fee logic
    total_to_transfer = Decimal(str(amount)) + fee

    pending = PendingDeposit(
        vault_id=vault.id,
        user_id=current_user.id,
        expected_amount=amount,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db.add(pending)
    await db.commit()

    return {
        "account_number": dva["account_number"],
        "bank_name": dva["bank_name"],
        "account_name": dva["account_name"],
        "amount_to_transfer": str(total_to_transfer),
        "fee": str(fee),
        "expires_at": pending.expires_at,
    }


@router.post("/webhooks/paystack")
async def paystack_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    if not verify_paystack_signature(raw_body, signature):
        raise HTTPException(401, "Invalid signature")

    payload = await request.json()
    event = payload.get("event")

    if event != "charge.success":
        return {"status": "ignored"}  # this webhook is deposit-only; transfer.success is a separate handler (Day 5)

    data = payload["data"]
    reference = data["reference"]

    # Amounts from Paystack arrive in KOBO (lowest unit) — always divide by 100
    amount_naira = Decimal(str(data["amount"])) / 100

    customer_code = data["customer"]["customer_code"]

    # Idempotency check — belt AND suspenders alongside the DB unique constraint
    existing = await db.execute(
        select(SavingsTransaction).where(SavingsTransaction.paystack_reference == reference)
    )
    if existing.scalar_one_or_none():
        return {"status": "already_processed"}  # ack 200 either way — Paystack retries on non-2xx

    user_result = await db.execute(select(User).where(User.paystack_customer_code == customer_code))
    user = user_result.scalar_one_or_none()
    if not user:
        # Genuinely shouldn't happen if DVA creation flow is correct, but never trust that blindly
        return {"status": "unknown_customer", "reference": reference}

    now = datetime.now(timezone.utc)
    pending_result = await db.execute(
        select(PendingDeposit).where(
            PendingDeposit.user_id == user.id,
            PendingDeposit.status == PendingDepositStatus.pending,
            PendingDeposit.expires_at > now,
            PendingDeposit.expected_amount == amount_naira,
        ).order_by(PendingDeposit.created_at.asc())  # oldest match wins — the tie-break rule we agreed on
    )
    pending = pending_result.scalars().first()

    if not pending:
        # UNASSIGNED BALANCE case — money genuinely arrived with no matching
        # intent. Do NOT drop it. Record it against the user with no vault yet;
        # the manual-allocation UI is a later build, but the ledger entry must
        # exist now so the money is never silently unaccounted for.
        db.add(SavingsTransaction(
            vault_id=None,  # requires vault_id to be made nullable — flagging this change below
            user_id=user.id,
            amount=amount_naira,
            type=TransactionType.deposit,
            paystack_reference=reference,
        ))
        await db.commit()
        return {"status": "unassigned", "reference": reference}

    vault = await db.get(SavingsVault, pending.vault_id)
    vault.current_amount = Decimal(str(vault.current_amount)) + amount_naira

    db.add(SavingsTransaction(
        vault_id=vault.id,
        user_id=user.id,
        amount=amount_naira,
        type=TransactionType.deposit,
        paystack_reference=reference,
    ))

    pending.status = PendingDepositStatus.matched

    newly_reached = check_milestones(vault)
    if newly_reached:
        vault.milestones_reached = (vault.milestones_reached or []) + newly_reached

    await db.commit()

    from app.savings.notifications import notify_deposit_confirmed, notify_milestone_reached
    await notify_deposit_confirmed(user, vault, amount_naira)

    for pct in newly_reached:
        await notify_milestone_reached(user, vault, pct)

    return {"status": "success", "reference": reference}


@router.post("", response_model=VaultResponse)
async def create_vault(
    payload: VaultCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.kyc_status != KYCStatus.verified:
        raise HTTPException(403, "Identity verification required before creating a vault")

    now = datetime.now(timezone.utc)
    lock_until = payload.lock_until
    if lock_until.tzinfo is None or lock_until.utcoffset() is None:
        lock_until = lock_until.replace(tzinfo=timezone.utc)
    else:
        lock_until = lock_until.astimezone(timezone.utc)

    if lock_until <= now:
        raise HTTPException(400, "lock_until must be in the future")

    tier = determine_milestone_tier(now, lock_until)

    vault = SavingsVault(
        user_id=current_user.id,
        name=payload.name,
        target_amount=payload.target_amount,
        lock_until=lock_until,
        milestone_tier=tier,
    )
    db.add(vault)
    await db.commit()
    await db.refresh(vault)
    return vault



@router.post("/webhooks/paystack-transfers")
async def paystack_transfer_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    if not verify_paystack_signature(raw_body, signature):
        raise HTTPException(401, "Invalid signature")

    payload = await request.json()
    event = payload.get("event")

    if event not in ("transfer.success", "transfer.failed", "transfer.reversed"):
        return {"status": "ignored"}

    data = payload["data"]
    reference = data["reference"]

    result = await db.execute(
        select(SavingsTransaction).where(
            SavingsTransaction.paystack_reference == reference
        ).with_for_update()
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        return {"status": "untracked_reference", "reference": reference}

    if transaction.status != TransactionStatus.pending:
        return {"status": "already_processed", "reference": reference}  # idempotency

    if event == "transfer.success":
        transaction.status = TransactionStatus.success
        await db.commit()
        

    if event == "transfer.success":
        transaction.status = TransactionStatus.success
        vault = await db.get(SavingsVault, transaction.vault_id)
        user = await db.get(User, transaction.user_id)
        if vault:
            vault.status = VaultStatus.withdrawn
            vault.completed_at = datetime.now(timezone.utc)
        await db.commit()
        if vault and user:
            await notify_payout_confirmed(user, vault, transaction.amount)
        return {"status": "success", "reference": reference}

    else:
        transaction.status = TransactionStatus.failed
        vault = await db.get(SavingsVault, transaction.vault_id)
        user = await db.get(User, transaction.user_id)
        if vault:
            vault.current_amount += transaction.amount
            vault.status = VaultStatus.payout_failed
        await db.commit()
        if vault and user:
            await notify_payout_failed(user, vault, transaction.amount)
        return {"status": event, "reference": reference}


@router.post("/webhooks/paystack-identity")
async def paystack_identity_webhook(
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    """
    Handles asynchronous Paystack identity verification (KYC) callbacks.
    Updates user KYC status and stores the official NIBSS-verified name.
    """
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    # 1. Cryptographic HMAC-SHA512 Signature Verification
    if not verify_paystack_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    event = payload.get("event")

    # 2. Filter for relevant identification events
    if event not in ("customeridentification.success", "customeridentification.failed"):
        return {"status": "ignored"}

    data = payload.get("data", {})
    customer_code = data.get("customer_code")

    if not customer_code:
        return {"status": "missing_customer_code"}

    # 3. Lock user row for update to prevent concurrent race conditions
    user_result = await db.execute(
        select(User)
        .where(User.paystack_customer_code == customer_code)
        .with_for_update()
    )
    user = user_result.scalar_one_or_none()

    if not user:
        return {"status": "unknown_customer", "customer_code": customer_code}

    # 4. Idempotency Check — Skip if user is already verified
    if user.kyc_status == KYCStatus.verified:
        return {"status": "already_verified", "customer_code": customer_code}

    # 5. Process Verification Outcome
    if event == "customeridentification.success":
        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()
        
        user.kyc_status = KYCStatus.verified
        user.kyc_verified_name = f"{first_name} {last_name}".strip()
        
        await db.commit()

        # Trigger success notification
        await notify_kyc_verified(user)
        return {"status": "success", "user_id": str(user.id)}

    else:  # customeridentification.failed
        reason = data.get("reason", "Submitted identification details could not be validated.")
        
        user.kyc_status = KYCStatus.failed
        await db.commit()

        # Trigger failure notification with reason
        await notify_kyc_failed(user, reason=reason)
        return {"status": "failed", "user_id": str(user.id), "reason": reason}



# app/savings/routers.py — updating request_withdrawal from Day 6

@router.post("/{vault_id}/withdraw")
@limiter.limit("3/hour")
async def request_withdrawal(
    request: Request, vault_id: str, amount: Decimal, withdrawal_pin: str,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    if not current_user.withdrawal_pin_hash or not verify_secret(withdrawal_pin, current_user.withdrawal_pin_hash):
        raise HTTPException(401, "Incorrect withdrawal PIN")

    await check_daily_withdrawal_cap(db, str(current_user.id), amount)
    transaction = await initiate_transfer(
        db=db, user_id=str(current_user.id), vault_id=vault_id, amount=amount,
        recipient_code=current_user.paystack_recipient_code, reason="User-requested withdrawal",
    )
    return {"status": "initiated", "transaction_id": str(transaction.id)}


@router.post("/bank-account/setup")
async def setup_bank_account(
    payload: BankAccountSetup,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Customer must exist before identity validation can run against it
    await ensure_user_has_dva(current_user, current_user.email_from_token, db)

    await validate_customer_identity(
        customer_code=current_user.paystack_customer_code,
        first_name=payload.first_name, last_name=payload.last_name,
        bvn=payload.bvn, bank_code=payload.bank_code,
        account_number=payload.account_number,
    )

    current_user.kyc_status = KYCStatus.pending
    current_user.payout_bank_code = payload.bank_code
    current_user.payout_account_number = payload.account_number
    await db.commit()

    return {"status": "pending", "message": "Identity verification in progress — you'll be notified when complete."}



@router.post("/withdrawal-pin/setup")
async def setup_withdrawal_pin(
    pin: str,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    if not (pin.isdigit() and len(pin) == 6):
        raise HTTPException(400, "Withdrawal PIN must be exactly 6 digits")
    current_user.withdrawal_pin_hash = hash_secret(pin)
    await db.commit()
    return {"status": "set"}

#

BANK_CHANGE_COOLING_OFF_HOURS = 24


from app.savings.notifications import notify_bank_change_requested

@router.post("/bank-account/request-change")
async def request_bank_account_change(
    payload: BankAccountChangeRequest,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    if not current_user.withdrawal_pin_hash or not verify_secret(payload.withdrawal_pin, current_user.withdrawal_pin_hash):
        raise HTTPException(401, "Incorrect withdrawal PIN")

    unlock_at = datetime.now(timezone.utc) + timedelta(hours=BANK_CHANGE_COOLING_OFF_HOURS)

    current_user.pending_bank_change = {
        "bvn": payload.new_bvn, "bank_code": payload.new_bank_code,
        "account_number": payload.new_account_number,
        "first_name": payload.first_name, "last_name": payload.last_name,
        "unlock_at": unlock_at.isoformat(),
    }
    await db.commit()
    await notify_bank_change_requested(current_user, unlock_at)
    return {"status": "pending", "unlock_at": unlock_at}


ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")


@router.post("/admin/withdraw-revenue")
async def trigger_revenue_withdrawal(
    current_user: User = Depends(get_current_user),
):
    if not ADMIN_EMAIL:
        raise HTTPException(503, "ADMIN_EMAIL is not configured")

    if current_user.email_from_token != ADMIN_EMAIL:
        raise HTTPException(403, "Not authorized")

    async with AsyncSessionLocal() as db:
        result = await withdraw_platform_revenue(db)
    return result