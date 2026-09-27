# app/savings/notifications.py
from decimal import Decimal
from fcm import send_push_notification  # adjust path if yours differs
from app.savings.models import SavingsVault
from app.Users.models import User


async def notify_deposit_confirmed(user: User, vault: SavingsVault, amount: Decimal):
    if not user.fcm_token:
        return
    await send_push_notification(
        fcm_token=user.fcm_token,
        title="Deposit confirmed",
        body=f"₦{amount:,.2f} added to '{vault.name}'. New balance: ₦{vault.current_amount:,.2f}",
    )


async def notify_milestone_reached(user: User, vault: SavingsVault, milestone_pct: int):
    if not user.fcm_token:
        return
    await send_push_notification(
        fcm_token=user.fcm_token,
        title=f"{milestone_pct}% milestone reached! 🎉",
        body=f"You're {milestone_pct}% of the way to '{vault.name}'. Keep it up.",
    )


async def notify_payout_confirmed(user: User, vault: SavingsVault, amount: Decimal):
    if not user.fcm_token:
        return
    await send_push_notification(
        fcm_token=user.fcm_token,
        title="Payout complete",
        body=f"₦{amount:,.2f} from '{vault.name}' has landed in your bank account.",
    )


async def notify_payout_failed(user: User, vault: SavingsVault, amount: Decimal):
    if not user.fcm_token:
        return
    await send_push_notification(
        fcm_token=user.fcm_token,
        title="Payout failed",
        body=f"Your ₦{amount:,.2f} payout from '{vault.name}' didn't go through. Funds remain safely in your vault — we'll retry.",
    )


async def notify_add_bank_details(user: User, vault: SavingsVault):
    if not user.fcm_token:
        return
    await send_push_notification(
        fcm_token=user.fcm_token,
        title="'%s' is ready to pay out" % vault.name,
        body="Add a verified payout account to receive your matured savings.",
    )


async def notify_kyc_verified(user: User):
    if not user.fcm_token:
        return
    await send_push_notification(
        fcm_token=user.fcm_token,
        title="Identity verified",
        body="Your identity has been confirmed. You can now create savings vaults.",
    )


async def notify_kyc_failed(user: User, reason: str | None = None):
    if not user.fcm_token:
        return
    await send_push_notification(
        fcm_token=user.fcm_token,
        title="Identity verification failed",
        body=reason or "We couldn't verify your details. Please check and try again.",
    )


async def notify_bank_change_requested(user: User, unlock_at):
    if not user.fcm_token:
        return
    await send_push_notification(
        fcm_token=user.fcm_token,
        title="Bank account change requested",
        body=f"If this wasn't you, contact support immediately. Change takes effect {unlock_at.strftime('%b %d, %I:%M %p')}.",
    )