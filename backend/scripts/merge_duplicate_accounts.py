"""One-time cleanup for accounts that were duplicated by the get_or_create_account race
condition (concurrent statement uploads for the same bank+account number each creating their
own Account row before the unique constraint existed -- see migration <TBD> and
services/lookup.py::get_or_create_account).

For every (user_id, bank_name, masked_account_number) group with more than one Account, keeps
the earliest-created row as canonical, reassigns every Statement/Transaction from the other rows
onto it, deletes the now-empty duplicates, and recomputes the canonical account's balances from
its full (merged) transaction history.

Usage: python -m scripts.merge_duplicate_accounts [--apply]
(dry-run by default; pass --apply to actually commit the changes)
"""
import sys
from collections import defaultdict

from app.database.session import SessionLocal
from app.models.account import Account
from app.models.recurring import RecurringTransaction
from app.models.statement import Statement
from app.models.transaction import Transaction


def main() -> int:
    apply = "--apply" in sys.argv
    db = SessionLocal()
    try:
        groups = defaultdict(list)
        for account in db.query(Account).order_by(Account.created_at.asc()).all():
            groups[(account.user_id, account.bank_name, account.masked_account_number)].append(account)

        total_merged = 0
        for key, accounts in groups.items():
            if len(accounts) < 2:
                continue
            canonical, dupes = accounts[0], accounts[1:]
            user_id, bank_name, masked = key
            print(f"{bank_name} {masked!r} (user {user_id}): merging {len(dupes)} duplicate(s) into {canonical.id}")

            for dupe in dupes:
                stmt_count = db.query(Statement).filter(Statement.account_id == dupe.id).count()
                txn_count = db.query(Transaction).filter(Transaction.account_id == dupe.id).count()
                print(f"  - {dupe.id}: {stmt_count} statement(s), {txn_count} transaction(s)")
                if apply:
                    db.query(Statement).filter(Statement.account_id == dupe.id).update({Statement.account_id: canonical.id})
                    db.query(Transaction).filter(Transaction.account_id == dupe.id).update({Transaction.account_id: canonical.id})
                    db.query(RecurringTransaction).filter(RecurringTransaction.account_id == dupe.id).update(
                        {RecurringTransaction.account_id: canonical.id}
                    )
                    db.delete(dupe)

            if apply:
                db.flush()
                latest = (
                    db.query(Transaction)
                    .filter(Transaction.account_id == canonical.id, Transaction.balance.isnot(None))
                    .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
                    .first()
                )
                earliest = (
                    db.query(Transaction)
                    .filter(Transaction.account_id == canonical.id, Transaction.balance.isnot(None))
                    .order_by(Transaction.transaction_date.asc(), Transaction.created_at.asc())
                    .first()
                )
                if latest is not None:
                    canonical.closing_balance = latest.balance
                if earliest is not None:
                    canonical.opening_balance = round(earliest.balance - earliest.amount, 2)
                print(f"  -> canonical balances: opening={canonical.opening_balance} closing={canonical.closing_balance}")

            total_merged += len(dupes)

        if apply:
            db.commit()
            print(f"\nMerged {total_merged} duplicate account(s). Committed.")
        else:
            db.rollback()
            print(f"\nDry run: would merge {total_merged} duplicate account(s). Re-run with --apply to commit.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
