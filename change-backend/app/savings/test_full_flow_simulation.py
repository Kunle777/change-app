# test_full_flow_simulation.py — throwaway, run directly
import asyncio
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import httpx
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.Users.models import User
from app.savings.models import SavingsVault, PendingDeposit, PendingDepositStatus

PAYSTACK_SECRET_KEY = os.environ["PAYSTACK_SECRET_KEY"]


async def setup():
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).order_by(User.id).limit(1))).scalar_one()

        vault = SavingsVault(
            user_id=user.id,
            name="Test Vault",
            target_amount=Decimal("10000"),
            current_amount=Decimal("5000"),  # pre-seeded, so this deposit crosses a milestone
            lock_until=datetime.now(timezone.utc) + timedelta(days=7),
            milestone_tier="short",
        )
        db.add(vault)
        await db.flush()

        # Bypassing the deposit-intent endpoint directly since it needs DVA —
        # this is standing in for what that endpoint would have created
        pending = PendingDeposit(
            vault_id=vault.id,
            user_id=user.id,
            expected_amount=Decimal("1000"),  # deposit that pushes 5000 -> 6000 = 60%
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        db.add(pending)
        await db.commit()

        print(f"user.paystack_customer_code = {user.paystack_customer_code}")
        return user.paystack_customer_code, str(vault.id)


async def fire_webhook(customer_code: str):
    payload = {
        "event": "charge.success",
        "data": {
            "reference": "sim_test_ref_001",
            "amount": 100000,  # kobo -> ₦1000, matches expected_amount above
            "customer": {"customer_code": customer_code},
        },
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    signature = hmac.new(PAYSTACK_SECRET_KEY.encode(), body_bytes, hashlib.sha512).hexdigest()

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        response = await client.post(
            "/api/savings/webhooks/paystack",
            content=body_bytes,
            headers={"x-paystack-signature": signature, "Content-Type": "application/json"},
        )
    print(response.status_code, response.json())


async def main():
    customer_code, vault_id = await setup()
    await fire_webhook(customer_code)

    # Confirm the result
    async with AsyncSessionLocal() as db:
        vault = await db.get(SavingsVault, vault_id)
        print(f"current_amount = {vault.current_amount}")  # expect 6000
        print(f"milestones_reached = {vault.milestones_reached}")  # expect [60]

asyncio.run(main())