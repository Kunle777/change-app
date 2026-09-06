# app/savings/service.py
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from app.savings.models import SavingsVault
# app/savings/service.py — additions

from app.savings.paystack_client import paystack_request, PaystackError
from app.users.models import User
from sqlalchemy.ext.asyncio import AsyncSession




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