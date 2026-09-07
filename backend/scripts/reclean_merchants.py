"""One-time cleanup for transactions imported before the AI merchant-cleanup pipeline existed.

Finds transactions whose merchant name looks like a reference-code fragment (e.g. "Aplap
d838b9a8d7e874c81"), asks the configured AI provider for the real merchant name and a better
category, and updates in place. Category is only overwritten when it's still the generic
"default" fallback (Other / Other Income) -- never touches a rule-matched or user-set category.

Usage: python -m scripts.reclean_merchants [--user-email demo@finmate.app] [--dry-run]
"""
import argparse
import sys

from app.ai.factory import get_ai_provider
from app.database.session import SessionLocal
from app.models.category import Category, Merchant
from app.models.transaction import Transaction
from app.models.user import User
from app.services.merchant_normalization import looks_like_garbage_merchant


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-email", default=None, help="Limit to one user (default: all users)")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing")
    args = parser.parse_args()

    provider = get_ai_provider()
    if not provider.is_available:
        print("No AI provider configured (AI_PROVIDER=none or missing API key) -- nothing to do.")
        return 1

    db = SessionLocal()
    try:
        categories_by_name = {c.name: c for c in db.query(Category).all()}
        category_names = list(categories_by_name.keys())

        merchants = db.query(Merchant).all()
        garbage = [m for m in merchants if looks_like_garbage_merchant(m.display_name)]
        print(f"Found {len(garbage)} merchant(s) with reference-code-like names out of {len(merchants)} total.")

        merchants_updated = 0
        categories_updated = 0

        for merchant in garbage:
            txns = db.query(Transaction).filter(Transaction.merchant_id == merchant.id).all()
            if not txns:
                continue
            if args.user_email:
                txns = [t for t in txns if (db.get(User, t.user_id) or User()).email == args.user_email]
                if not txns:
                    continue

            sample_txn = max(txns, key=lambda t: t.transaction_date)
            result = provider.categorize_transaction(sample_txn.original_description, sample_txn.amount, category_names)

            new_name = result.merchant.strip() if result.merchant else ""
            merchant_ok = bool(new_name) and not looks_like_garbage_merchant(new_name)
            category = categories_by_name.get(result.category)

            if not merchant_ok and not category:
                print(f"  [skip] Could not clean: {merchant.display_name!r} <- {sample_txn.original_description[:70]!r}")
                continue

            action = "DRY RUN" if args.dry_run else "update"
            if merchant_ok:
                print(f"  [{action}] merchant {merchant.display_name!r} -> {new_name!r}")
                if not args.dry_run:
                    merchant.display_name = new_name
                    merchants_updated += 1

            if category:
                default_txns = [t for t in txns if t.categorization_source == "default"]
                if default_txns:
                    print(f"    [{action}] category for {len(default_txns)} txn(s) -> {result.category!r}")
                    if not args.dry_run:
                        for t in default_txns:
                            t.category_id = category.id
                            t.categorization_source = "ai"
                            categories_updated += 1

        if not args.dry_run:
            db.commit()
        print(f"Updated {merchants_updated} merchant name(s), {categories_updated} transaction categor(y/ies).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
