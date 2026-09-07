"""One-time backfill for accounts created before the balance-refresh fix existed -- their
opening/closing balance stayed at the 0.0 default even though real transactions were imported.

Usage: python -m scripts.backfill_account_balances
"""
import sys

from app.database.session import SessionLocal
from app.models.account import Account
from app.services.statement_import import StatementImportService


def main() -> int:
    db = SessionLocal()
    try:
        service = StatementImportService(db)
        accounts = db.query(Account).all()
        updated = 0
        for account in accounts:
            before = (account.opening_balance, account.closing_balance)
            service._refresh_account_balance(account.id)
            after = (account.opening_balance, account.closing_balance)
            if before != after:
                print(f"  {account.bank_name} {account.masked_account_number}: {before} -> {after}")
                updated += 1
        db.commit()
        print(f"Updated {updated} of {len(accounts)} account(s).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
