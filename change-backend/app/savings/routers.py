from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from app.database import get_db
from app.users.dependencies import get_current_user
from app.users.models import User
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
from app.savings.notifications import notify_deposit_confirmed, notify_milestone_reached



router = APIRouter(prefix="/api/savings", tags=["savings"])


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

