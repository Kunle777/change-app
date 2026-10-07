# test_transfer.py — throwaway
import asyncio
import os
from decimal import Decimal
from app.database import AsyncSessionLocal
from app.savings.service import resolve_account_number, create_transfer_recipient, initiate_transfer

async def main():
    required = (
        "TEST_PAYOUT_ACCOUNT_NUMBER",
        "TEST_PAYOUT_BANK_CODE",
        "TEST_PAYOUT_USER_ID",
        "TEST_PAYOUT_VAULT_ID",
    )
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Set these environment variables before running the live transfer test: "
            + ", ".join(missing)
        )

    account_number = os.environ["TEST_PAYOUT_ACCOUNT_NUMBER"]
    bank_code = os.environ["TEST_PAYOUT_BANK_CODE"]
    user_id = os.environ["TEST_PAYOUT_USER_ID"]
    vault_id = os.environ["TEST_PAYOUT_VAULT_ID"]
    amount = Decimal(os.getenv("TEST_PAYOUT_AMOUNT", "100"))

    resolved = await resolve_account_number(account_number, bank_code)
    print("Resolved:", resolved)

    recipient_code = await create_transfer_recipient(
        resolved["account_number"], bank_code, resolved["account_name"]
    )
    print("Recipient:", recipient_code)

    async with AsyncSessionLocal() as db:
        txn = await initiate_transfer(
            db,
            user_id=user_id,
            vault_id=vault_id,
            amount=amount,
            recipient_code=recipient_code,
            reason="Test payout",
        )
        print("Transaction:", txn.status, txn.paystack_reference)

asyncio.run(main())