"""One-time cleanup for transactions imported before normalization.py stripped embedded
rich-text markup (e.g. some broker/trading-account PDF exports embed literal
<style fontName='Mulish' fontSize='8'>...</style> tags in a table cell instead of plain text,
which pdfplumber then extracts verbatim). Re-cleans original/normalized descriptions and
re-points affected transactions at a properly named merchant.

Usage: python -m scripts.reclean_markup_descriptions [--user-email demo@finmate.app] [--dry-run]
"""
import argparse
import sys

from app.database.session import SessionLocal
from app.models.transaction import Transaction
from app.models.user import User
from app.services.lookup import get_or_create_merchant
from app.services.merchant_normalization import normalize_description, normalize_merchant
from app.services.normalization import _strip_markup


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-email", default=None, help="Limit to one user (default: all users)")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        q = db.query(Transaction).filter(Transaction.original_description.like("%<%"))
        if args.user_email:
            user = db.query(User).filter(User.email == args.user_email).first()
            if not user:
                print(f"No user with email {args.user_email!r}")
                return 1
            q = q.filter(Transaction.user_id == user.id)
        txns = q.all()
        print(f"Found {len(txns)} transaction(s) with embedded markup.")

        updated = 0
        for t in txns:
            clean_raw = _strip_markup(t.original_description)
            clean_normalized = normalize_description(clean_raw)
            clean_merchant_name = normalize_merchant(clean_raw)

            action = "DRY RUN" if args.dry_run else "update"
            print(f"  [{action}] {t.original_description[:70]!r} -> {clean_raw[:70]!r}")

            if not args.dry_run:
                t.original_description = clean_raw
                t.normalized_description = clean_normalized
                merchant = get_or_create_merchant(db, clean_merchant_name, clean_merchant_name)
                t.merchant_id = merchant.id
                updated += 1

        if not args.dry_run:
            db.commit()
        print(f"Updated {updated} transaction(s).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
