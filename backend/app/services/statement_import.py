"""Statement import orchestrator: Parse -> Normalize -> Validate -> Overlap/Duplicate Detection
-> Categorize -> Stage for review -> (on confirm) Commit inside one DB transaction.

Uploaded statements are never auto-imported when a critical conflict (exact duplicate or full
containment) exists -- see ingest() and StatementReviewRequired handling in the API layer.
"""
import json
from dataclasses import asdict, dataclass
from datetime import date
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.ai.base import CategorizationResult
from app.ai.factory import get_ai_provider
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.models.account import Account
from app.models.statement import Statement, StatementProcessingError
from app.models.transaction import Transaction
from app.parsers.bank_detection import mask_account_number
from app.parsers.registry import registry
from app.services.balance_validation import validate_balances
from app.services.categorization import rule_based_category
from app.services.duplicate_detection import DuplicateConfidence, ExistingTxnRef, check_duplicate
from app.services.lookup import (
    ensure_default_categories, get_or_create_account, get_or_create_merchant, load_learned_rules,
)
from app.services.normalization import NormalizedTransaction, normalize_rows
from app.services.overlap_detection import ExistingPeriod, OverlapType, detect_overlap
from app.services.transfer_detection import classify_transaction_type
from app.utils.files import delete_temp_file

logger = get_logger(__name__)

CRITICAL_OVERLAPS = (OverlapType.EXACT_DUPLICATE, OverlapType.FULL_CONTAINMENT)


@dataclass
class ImportSummary:
    statement_id: str
    bank_name: str
    account_id: str
    masked_account_number: str
    period_start: Optional[str]
    period_end: Optional[str]
    transaction_count: int
    total_income: float
    total_expenses: float
    potential_duplicates: int
    overlap_type: str
    overlap_message: str
    warnings: List[str]
    balance_mismatches: int
    status: str


class StatementImportService:
    def __init__(self, db: Session):
        self.db = db
        self.categories = ensure_default_categories(db)
        self.provider = get_ai_provider()

    def ingest(self, user_id: str, file_path: str, original_filename: str, file_format: str) -> ImportSummary:
        with open(file_path, "rb") as f:
            sample = f.read(4096)

        parser = registry.detect_parser(original_filename, sample)
        try:
            parsed = parser.parse(file_path)
        except AppError:
            raise
        except Exception as exc:
            logger.exception("Unexpected parser failure")
            raise AppError(ErrorCode.PARSER_FAILED, f"Unexpected error while parsing file: {exc}")

        account = get_or_create_account(
            self.db, user_id, parsed.bank_name, parsed.account_type,
            parsed.account_identifier or mask_account_number(original_filename), parsed.currency,
        )

        normalized = normalize_rows(parsed.rows, account.id, parsed.currency)
        if not normalized:
            raise AppError(ErrorCode.NO_TRANSACTIONS_FOUND, "No valid transactions could be extracted.")

        period_start = parsed.period_start or min(t.transaction_date for t in normalized)
        period_end = parsed.period_end or max(t.transaction_date for t in normalized)
        period_confidence = parsed.period_confidence if parsed.period_start else 0.5

        warnings: List[str] = list(parsed.warnings)
        for t in normalized:
            warnings.extend(t.warnings)

        existing_periods = [
            ExistingPeriod(s.id, s.period_start, s.period_end)
            for s in self.db.query(Statement).filter(
                Statement.account_id == account.id, Statement.status != "FAILED",
                Statement.period_start.isnot(None),
            ).all()
        ]
        overlap = detect_overlap(period_start, period_end, existing_periods)

        mismatches = validate_balances(normalized)
        if mismatches:
            warnings.append(f"Balance mismatch detected on {len(mismatches)} row(s).")

        existing_refs = [
            ExistingTxnRef(t.id, t.fingerprint, t.transaction_date, t.amount, t.normalized_description)
            for t in self.db.query(Transaction).filter(Transaction.account_id == account.id).all()
        ]

        learned_rules = load_learned_rules(self.db, user_id)
        staged = []
        duplicate_count = 0
        total_income = total_expenses = 0.0

        for t in normalized:
            dup = check_duplicate(t, existing_refs)
            is_duplicate = dup.confidence != DuplicateConfidence.NONE
            if is_duplicate:
                duplicate_count += 1

            is_credit = t.credit > 0
            category_name, confidence, source = rule_based_category(
                t.normalized_description, t.merchant_name, is_credit, learned_rules
            )
            if category_name is None and self.provider.is_available:
                result: CategorizationResult = self.provider.categorize_transaction(
                    t.original_description, t.amount, list({c.name for c in self.categories.values()})
                )
                category_name, confidence, source = result.category, result.confidence, "ai"
            elif category_name is None:
                category_name, confidence, source = "Other", 0.2, "default"

            txn_type = classify_transaction_type(t, [account.masked_account_number])
            if txn_type == "expense":
                total_expenses += t.debit
            elif txn_type == "income":
                total_income += t.credit

            staged.append({
                "row_index": t.row_index,
                "transaction_date": t.transaction_date.isoformat(),
                "value_date": t.value_date.isoformat() if t.value_date else None,
                "original_description": t.original_description,
                "normalized_description": t.normalized_description,
                "merchant_name": t.merchant_name,
                "reference_number": t.reference_number,
                "debit": t.debit,
                "credit": t.credit,
                "amount": t.amount,
                "balance": t.balance,
                "payment_method": t.payment_method,
                "fingerprint": t.fingerprint,
                "transaction_type": txn_type,
                "category_name": category_name,
                "categorization_confidence": confidence,
                "categorization_source": source,
                "is_duplicate": is_duplicate,
                "duplicate_confidence": dup.confidence.value,
            })

        # PROCESSED is reserved for statements whose transactions have actually been committed
        # (see confirm()) -- until then, every non-critical outcome is NEEDS_REVIEW so the
        # mandatory Import Review screen is never skipped.
        status = "NEEDS_REVIEW"
        if overlap.overlap_type in CRITICAL_OVERLAPS:
            status = "OVERLAP_DETECTED" if overlap.overlap_type != OverlapType.EXACT_DUPLICATE else "DUPLICATE"

        statement = Statement(
            user_id=user_id, account_id=account.id, original_filename=original_filename,
            file_format=file_format, detected_bank=parsed.bank_name, parser_used=parsed.parser_used,
            period_start=period_start, period_end=period_end, period_confidence=period_confidence,
            status=status, transaction_count=len(staged),
            total_income=round(total_income, 2), total_expenses=round(total_expenses, 2),
            overlap_type=overlap.overlap_type.value, duplicate_count=duplicate_count,
            warnings_json=json.dumps(warnings),
            balance_mismatch_json=json.dumps([asdict(m) for m in mismatches], default=str) if mismatches else None,
            staging_transactions_json=json.dumps(staged),
        )
        self.db.add(statement)
        self.db.commit()
        self.db.refresh(statement)

        return ImportSummary(
            statement_id=statement.id, bank_name=parsed.bank_name, account_id=account.id,
            masked_account_number=account.masked_account_number,
            period_start=period_start.isoformat(), period_end=period_end.isoformat(),
            transaction_count=len(staged), total_income=round(total_income, 2),
            total_expenses=round(total_expenses, 2), potential_duplicates=duplicate_count,
            overlap_type=overlap.overlap_type.value, overlap_message=overlap.message,
            warnings=warnings, balance_mismatches=len(mismatches), status=status,
        )

    def confirm(self, statement_id: str, user_id: str) -> Dict:
        statement = self._get_owned_statement(statement_id, user_id)
        if statement.status == "DUPLICATE":
            raise AppError(ErrorCode.DUPLICATE_STATEMENT, "This statement is an exact duplicate and cannot be imported.")
        if not statement.staging_transactions_json:
            raise AppError(ErrorCode.DATABASE_ERROR, "No staged transactions found for this statement.")

        staged = json.loads(statement.staging_transactions_json)
        imported, skipped_exact_duplicates = 0, 0

        for row in staged:
            if row["duplicate_confidence"] == DuplicateConfidence.EXACT.value:
                skipped_exact_duplicates += 1
                continue

            category = self.categories.get(row["category_name"]) or self.categories.get("Other")
            merchant = get_or_create_merchant(self.db, row["merchant_name"], row["merchant_name"])

            is_likely_dup = row["duplicate_confidence"] in (
                DuplicateConfidence.LIKELY.value, DuplicateConfidence.POSSIBLE.value,
            )

            txn = Transaction(
                user_id=user_id, account_id=statement.account_id, statement_id=statement.id,
                transaction_date=date.fromisoformat(row["transaction_date"]),
                value_date=date.fromisoformat(row["value_date"]) if row["value_date"] else None,
                original_description=row["original_description"],
                normalized_description=row["normalized_description"],
                reference_number=row["reference_number"] or None,
                debit=row["debit"], credit=row["credit"], amount=row["amount"],
                transaction_type=row["transaction_type"], balance=row["balance"],
                merchant_id=merchant.id, category_id=category.id if category else None,
                payment_method=row["payment_method"], source="import", source_row=row["row_index"],
                confidence_score=row["categorization_confidence"],
                categorization_source=row["categorization_source"],
                fingerprint=row["fingerprint"], is_duplicate=is_likely_dup,
                is_excluded=is_likely_dup,
                is_internal_transfer=row["transaction_type"] == "transfer",
            )
            self.db.add(txn)
            imported += 1

        statement.status = "PROCESSED"
        statement.staging_transactions_json = None
        self.db.commit()

        return {"imported": imported, "skipped_exact_duplicates": skipped_exact_duplicates}

    def cancel(self, statement_id: str, user_id: str) -> None:
        statement = self._get_owned_statement(statement_id, user_id)
        self.db.delete(statement)
        self.db.commit()

    def _get_owned_statement(self, statement_id: str, user_id: str) -> Statement:
        statement = self.db.get(Statement, statement_id)
        if not statement or statement.user_id != user_id:
            raise AppError(ErrorCode.NOT_FOUND, "Statement not found.", status_code=404)
        return statement
