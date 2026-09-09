import os
import uuid
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import func, select
from app.savings.models import (
    SavingsVault,
    SavingsTransaction,
    TransactionStatus,
    TransactionType,
    VaultStatus,
    PlatformRevenue,
)
from app.savings.paystack_client import paystack_request, PaystackError
from app.users.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from datetime import timezone, timedelta





def paystack_fee(amount: Decimal) -> Decimal:
    """
    Calculates the Paystack fee for a Dedicated Virtual Account (DVA) transfer.
    Formula: 1% of the amount, capped at ₦300.

    Always returns a Decimal rounded to 2dp — never mix float arithmetic
    into anything touching real money.
    """
    if amount <= 0:
        raise ValueError("Amount must be positive")

    raw_fee = amount * Decimal("0.01")
    capped_fee = min(raw_fee, Decimal("300"))

    return capped_fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

MILESTONE_THRESHOLDS = {
    "short": [50, 100],       # ≤3 months — sparse, avoids notification spam on a 7-day vault
    "long": [25, 50, 75, 100],  # >3 months — dense, keeps momentum over a long silent stretch
}


def determine_milestone_tier(created_at: datetime, lock_until: datetime) -> str:
    """
    Called once, at vault creation. Never recalled — locking this in avoids
    a vault silently changing its notification schedule if lock_until is edited later.
    """
    duration_days = (lock_until - created_at).days
    return "short" if duration_days <= 90 else "long"


def check_milestones(vault: SavingsVault) -> list[int]:
    """
    Returns any newly-crossed thresholds not already recorded in
    vault.milestones_reached. Caller is responsible for persisting the
    update and firing notifications — this function only detects, never mutates.
    """
    thresholds = MILESTONE_THRESHOLDS[vault.milestone_tier]
    progress_pct = (vault.current_amount / vault.target_amount) * 100
    already_reached = vault.milestones_reached or []

    newly_reached = [
        t for t in thresholds
        if progress_pct >= t and t not in already_reached
    ]
    return newly_reached


async def create_paystack_customer(user: User, email: str) -> str:
    """
    Creates a Paystack Customer record for this user. Returns the
    customer_code, which is required before a DVA can be created —
    Paystack's DVA endpoint attaches to an existing customer, it doesn't
    create one inline.
    """
    data = await paystack_request(
        "POST",
        "/customer",
        json={
            "email": email,
            "first_name": "Change",
            "last_name": "User",
            "phone": user.phone,
        },
    )
    return data["customer_code"]


async def create_dedicated_account(customer_code: str) -> dict:
    """
    Creates the actual DVA (Dedicated Virtual Account) tied to a customer.
    Returns account_number, bank name, and account name — these are what
    get shown to the user as "transfer to this account."

    Requires the customer to already have gone through Paystack's identity
    validation for this endpoint (BVN/NIN-adjacent, per memory) — if this
    call fails with a validation-related error, that's the likely cause,
    not a bug in this function.
    """
    data = await paystack_request(
        "POST",
        "/dedicated_account",
        json={
            "customer": customer_code,
            "preferred_bank": "wema-bank",  # or "titan-paystack" — confirm which your account supports
        },
    )
    return {
        "account_number": data["account_number"],
        "bank_name": data["bank"]["name"],
        "account_name": data["account_name"],
    }


async def ensure_user_has_dva(user: User,email:str, db: AsyncSession) -> dict:
    """
    Returns the user's DVA details, creating them if they don't exist yet.
    Safe to call every time a user tries to fund a vault — does nothing
    if the DVA already exists, so there's no risk of accidentally creating
    a second customer/DVA for someone who already has one.
    """
    if user.dva_account_number:
        return {
            "account_number": user.dva_account_number,
            "bank_name": user.dva_bank_name,
            "account_name": user.dva_account_name,
        }

    if not user.paystack_customer_code:
        customer_code = await create_paystack_customer(user, email)
        user.paystack_customer_code = customer_code
        await db.commit()

    dva = await create_dedicated_account(user.paystack_customer_code)

    user.dva_account_number = dva["account_number"]
    user.dva_bank_name = dva["bank_name"]
    user.dva_account_name = dva["account_name"]
    await db.commit()

    return dva



async def resolve_account_number(account_number: str, bank_code: str) -> dict:
    """
    Confirms an account number is real and returns the actual account holder's
    name as registered with the bank. This MUST happen before attaching a bank
    account to a user — never trust a user-typed name over what the bank itself
    reports, since that's exactly the gap a scammer would exploit (typing
    someone else's account number with their own fabricated 'account name').
    """
    data = await paystack_request(
        "GET",
        f"/bank/resolve?account_number={account_number}&bank_code={bank_code}",
    )
    return {
        "account_name": data["account_name"],
        "account_number": data["account_number"],
    }

async def create_transfer_recipient(account_number: str, bank_code: str, account_name: str) -> str:
    """
    Paystack requires a 'recipient' object before any transfer can be sent —
    you can't transfer directly to a raw account number. Returns recipient_code,
    stored once per user (a payout destination change means creating a NEW
    recipient, not mutating this one — Paystack recipients are treated as
    immutable references, matching how customer_code already works on the deposit side).
    """
    data = await paystack_request(
        "POST",
        "/transferrecipient",
        json={
            "type": "nuban",
            "name": account_name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": "NGN",
        },
    )
    return data["recipient_code"]



async def initiate_transfer(
    db: AsyncSession,
    user_id: str,
    vault_id: str,
    amount: Decimal,
    recipient_code: str,
    reason: str,
) -> SavingsTransaction:
    """
    Debits the vault and commits BEFORE calling Paystack — the row lock is
    held only for the brief DB operation, never across the external HTTP
    call. This avoids a slow/stuck Paystack response holding a lock that
    blocks every other operation on this vault. The tradeoff: a small
    window where the vault shows debited before Paystack has confirmed —
    acceptable, and self-correcting via the webhook's automatic refund
    path if the transfer actually fails.
    """
    vault_result = await db.execute(
        select(SavingsVault).where(
            SavingsVault.id == vault_id, SavingsVault.user_id == user_id
        ).with_for_update()
    )
    vault = vault_result.scalar_one_or_none()
    if not vault:
        raise HTTPException(404, "Vault not found")
    if vault.current_amount < amount:
        raise HTTPException(400, "Insufficient vault balance")

    vault.current_amount -= amount

    transfer_reference = f"payout_{uuid.uuid4().hex[:20]}"

    transaction = SavingsTransaction(
        vault_id=vault.id,
        user_id=user_id,
        amount=amount,
        type=TransactionType.withdrawal,
        status=TransactionStatus.pending,
        paystack_reference=transfer_reference,
    )
    db.add(transaction)
    await db.commit()  # lock released here — before any network call

    # Now, outside the lock, actually call Paystack
    amount_kobo = int(amount * 100)
    try:
        await paystack_request(
            "POST",
            "/transfer",
            json={
                "source": "balance",
                "amount": amount_kobo,
                "recipient": recipient_code,
                "reason": reason,
                "reference": transfer_reference,
            },
        )
    except PaystackError:
        # The API call itself failed to even dispatch — refund immediately,
        # don't wait for a webhook that will never arrive for a call that
        # never succeeded.
        vault.current_amount += amount
        transaction.status = TransactionStatus.failed
        await db.commit()
        raise HTTPException(502, "Payout could not be initiated. Your funds remain in the vault.")

    return transaction


async def check_and_process_matured_vaults():
    """
    Celery Beat entrypoint — same shape as get_due_reminders: no user_id
    parameter, since this is a system-wide scheduled check, not a per-request call.
    """
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(SavingsVault).where(
                SavingsVault.status == VaultStatus.active,
                SavingsVault.lock_until <= now,
            )
        )
        matured_vaults = result.scalars().all()

        for vault in matured_vaults:
            await process_single_vault_maturity(db, vault)


from app.savings.notifications import notify_add_bank_details, notify_payout_failed



async def process_single_vault_maturity(db, vault: SavingsVault):
    user = await db.get(User, vault.user_id)

    if not user.paystack_recipient_code:
        vault.status = VaultStatus.awaiting_bank_details
        await db.commit()
        await notify_add_bank_details(user, vault)
        return

    vault.status = VaultStatus.payout_initiated
    await db.commit()

    try:
        await initiate_transfer(
            db=db,
            user_id=str(user.id),
            vault_id=str(vault.id),
            amount=vault.current_amount,
            recipient_code=user.paystack_recipient_code,
            reason=f"Vault maturity payout: {vault.name}",
        )
    except HTTPException:
        vault.status = VaultStatus.payout_failed
        await db.commit()
        await notify_payout_failed(user, vault, vault.current_amount)


async def validate_customer_identity(
    customer_code: str, first_name: str, last_name: str,
    bvn: str, bank_code: str, account_number: str
) -> dict:
    """
    Kicks off Paystack's BVN validation — this call itself only confirms
    the request was accepted, NOT that identity is verified. The real
    result arrives later via the customeridentification.success/failed
    webhook. Never treat this function's return value as proof of KYC.
    """
    data = await paystack_request(
        "POST",
        f"/customer/{customer_code}/identification",
        json={
            "country": "NG",
            "type": "bank_account",
            "account_number": account_number,
            "bank_code": bank_code,
            "bvn": bvn,
            "first_name": first_name,
            "last_name": last_name,
        },
    )
    return data

DAILY_WITHDRAWAL_CAP = Decimal("500000")  # ₦500,000 per 24h, across all vaults


async def check_daily_withdrawal_cap(db: AsyncSession, user_id: str, requested_amount: Decimal) -> None:
    """
    Sums this user's withdrawals in the trailing 24h and rejects if the new
    request would exceed the cap. Deliberately checked BEFORE the atomic
    balance lock in initiate_transfer — this is a velocity/fraud guardrail,
    a separate concern from "does the vault have enough money."
    """
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    result = await db.execute(
        select(func.coalesce(func.sum(SavingsTransaction.amount), 0)).where(
            SavingsTransaction.user_id == user_id,
            SavingsTransaction.type == TransactionType.withdrawal,
            SavingsTransaction.status != TransactionStatus.failed,
            SavingsTransaction.created_at >= since,
        )
    )
    total_withdrawn_24h = result.scalar()

    if total_withdrawn_24h + requested_amount > DAILY_WITHDRAWAL_CAP:
        raise HTTPException(429, f"Daily withdrawal limit of ₦{DAILY_WITHDRAWAL_CAP:,.2f} exceeded")



PLATFORM_RECIPIENT_CODE = os.environ["PLATFORM_RECIPIENT_CODE"]
# ^ Created ONCE, manually, ahead of time: your own KunleTech business bank
#   account, registered as a Paystack transfer recipient via the same
#   create_transfer_recipient() function — but never touching user flow code.


async def withdraw_platform_revenue(db: AsyncSession) -> dict:
    """
    Sweeps all not-yet-withdrawn PlatformRevenue rows to KunleTech's own
    registered business account — a single Transfer, batched, run
    periodically (weekly/monthly), NEVER automatically per-transaction.
    Batching is deliberate: it keeps the audit trail as one clean
    reference per sweep rather than tiny scattered transfers, and it
    means you control exactly when revenue leaves the pool.
    """
    result = await db.execute(
        select(PlatformRevenue).where(PlatformRevenue.withdrawn == False)
    )
    unwithdrawn = result.scalars().all()
    if not unwithdrawn:
        return {"status": "nothing_to_withdraw"}

    total = sum(Decimal(str(r.amount)) for r in unwithdrawn)
    reference = f"revenue_sweep_{uuid.uuid4().hex[:20]}"

    await paystack_request(
        "POST", "/transfer",
        json={
            "source": "balance", "amount": int(total * 100),
            "recipient": PLATFORM_RECIPIENT_CODE,
            "reason": f"Platform revenue sweep — {len(unwithdrawn)} fee(s)",
            "reference": reference,
        },
    )

    for row in unwithdrawn:
        row.withdrawn = True
        row.withdrawal_reference = reference
    await db.commit()

    return {"status": "initiated", "total": str(total), "reference": reference, "count": len(unwithdrawn)}

