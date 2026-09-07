# app/savings/notifications.py
from fcm import send_push_notification  
from app.savings.models import SavingsVault
from app.users.models import User
from decimal import Decimal


async def notify_deposit_confirmed(user: User, vault: SavingsVault, amount: Decimal):
    if not user.fcm_token:
        return  # no device registered yet — fail silently, never block the webhook on this
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