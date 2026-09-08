# test_transfer.py — throwaway
import asyncio
from decimal import Decimal
from app.savings.service import resolve_account_number, create_transfer_recipient, initiate_transfer

async def main():
    # Use a real test-mode bank code + account number from Paystack's test docs
    resolved = await resolve_account_number("0000000000", "057")  # example values — use Paystack's real test account
    print("Resolved:", resolved)

    recipient_code = await create_transfer_recipient(
        resolved["account_number"], "057", resolved["account_name"]
    )
    print("Recipient:", recipient_code)

    result = await initiate_transfer(recipient_code, Decimal("100"), "Test payout")
    print("Transfer:", result)

asyncio.run(main())