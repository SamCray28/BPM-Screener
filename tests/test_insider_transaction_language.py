import unittest
from datetime import datetime, timezone

from app.models.snapshot import InsiderTransaction, describe_insider_transaction
from app.safeguards import assert_no_directional_language


class TestInsiderTransactionLanguage(unittest.TestCase):
    """SEC Form 4 filings genuinely use 'Buy'/'Sell' as category labels.
    That raw label must never leak into screener output verbatim — this
    proves the neutral-language helper actually strips it."""

    def test_buy_transaction_type_produces_no_directional_language(self):
        txn = InsiderTransaction(
            timestamp=datetime.now(timezone.utc), insider_role="CEO", transaction_type="Buy",
        )
        text = describe_insider_transaction(txn)
        assert_no_directional_language(text)  # should not raise
        self.assertIn("acquisition", text)

    def test_sell_transaction_type_produces_no_directional_language(self):
        txn = InsiderTransaction(
            timestamp=datetime.now(timezone.utc), insider_role="CFO", transaction_type="Sell",
        )
        text = describe_insider_transaction(txn)
        assert_no_directional_language(text)  # should not raise
        self.assertIn("disposition", text)


if __name__ == "__main__":
    unittest.main()
