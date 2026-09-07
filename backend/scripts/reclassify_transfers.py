"""One-time reclassification for transactions imported before transfer_detection.py treated
P2A/P2P credits the same as debits. A UPI/IMPS "P2A" (person-to-account) credit -- e.g. money
moving from your own ICICI account into your Axis account -- was being counted as income; it's
now classified the same way a matching debit already was: as a transfer, excluded from cash
flow and income totals.

Usage: python -m scripts.reclassify_transfers [--user-email demo@finmate.app] [--dry-run]
"""
import argparse
import sys

from app.database.session import SessionLocal
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.services.transfer_detection import classify_transaction_type


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-email", default=None, help="Limit to one user (default: all users)")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        q = db.query(Transaction)
        if args.user_email:
            user = db.query(User).filter(User.email == args.user_email).first()
            if not user:
                print(f"No user with email {args.user_email!r}")
                return 1
            q = q.filter(Transaction.user_id == user.id)

        accounts_by_id = {a.id: a for a in db.query(Account).all()}
        users_by_id = {u.id: u for u in db.query(User).all()}
        changed = 0

        for t in q.all():
            account = accounts_by_id.get(t.account_id)
            identifiers = [account.masked_account_number] if account else []
            holder = users_by_id.get(t.user_id)
            new_type = classify_transaction_type(t, identifiers, holder.full_name if holder else None)
            if new_type != t.transaction_type:
                action = "DRY RUN" if args.dry_run else "update"
                print(f"  [{action}] {t.transaction_type} -> {new_type}: {t.original_description[:80]!r}")
                if not args.dry_run:
                    t.transaction_type = new_type
                changed += 1

        if not args.dry_run:
            db.commit()
        print(f"Reclassified {changed} transaction(s).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
