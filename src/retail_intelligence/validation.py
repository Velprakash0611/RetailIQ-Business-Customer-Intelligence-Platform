"""
Validation module for RetailIQ.
Analyzes raw mapped transactions for data quality issues: missing keys, invalid types,
returns, cancellations, zero-prices, duplicate rows, and date spans.
"""

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class ValidationIssue:
    severity: str  # "ERROR", "WARNING", "INFO"
    category: str
    message: str
    affected_rows: int
    affected_pct: float
    affected_monetary_impact: float | None = None


@dataclass
class ValidationReport:
    total_raw_rows: int
    total_raw_columns: int
    is_valid_for_processing: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_raw_rows": self.total_raw_rows,
            "total_raw_columns": self.total_raw_columns,
            "is_valid_for_processing": self.is_valid_for_processing,
            "issues": [
                {
                    "severity": issue.severity,
                    "category": issue.category,
                    "message": issue.message,
                    "affected_rows": issue.affected_rows,
                    "affected_pct": issue.affected_pct,
                    "affected_monetary_impact": issue.affected_monetary_impact,
                }
                for issue in self.issues
            ],
            "stats": self.stats,
        }


def validate_mapped_dataframe(
    df: pd.DataFrame,
    mapping: dict[str, str],
) -> ValidationReport:
    """
    Validates a raw DataFrame against the user-confirmed column mapping.
    df: raw dataframe
    mapping: {canonical_name: raw_col_name}
    """
    total_rows = len(df)
    issues: list[ValidationIssue] = []
    stats: dict[str, Any] = {}

    if total_rows == 0:
        return ValidationReport(
            total_raw_rows=0,
            total_raw_columns=len(df.columns),
            is_valid_for_processing=False,
            issues=[
                ValidationIssue(
                    severity="ERROR",
                    category="Empty Dataset",
                    message="The uploaded file contains zero data rows.",
                    affected_rows=0,
                    affected_pct=0.0,
                )
            ],
            stats={},
        )

    # 1. Check required mapped columns exist in df
    missing_cols = [raw_col for canon, raw_col in mapping.items() if canon in [
        "date", "invoice_id", "customer_id", "product_id", "quantity", "unit_price"
    ] and (not raw_col or raw_col not in df.columns)]

    if missing_cols:
        issues.append(
            ValidationIssue(
                severity="ERROR",
                category="Missing Mapped Columns",
                message=f"Mapped columns not found in uploaded file: {', '.join(missing_cols)}",
                affected_rows=total_rows,
                affected_pct=100.0,
            )
        )
        return ValidationReport(
            total_raw_rows=total_rows,
            total_raw_columns=len(df.columns),
            is_valid_for_processing=False,
            issues=issues,
            stats={},
        )

    # Extract series for analysis
    date_col = mapping["date"]
    cust_col = mapping["customer_id"]
    qty_col = mapping["quantity"]
    price_col = mapping["unit_price"]

    # 2. Check Customer ID completeness
    cust_series = df[cust_col]
    null_cust_mask = cust_series.isna() | (cust_series.astype(str).str.strip().isin(["", "nan", "NaN", "None", "null", "NULL"]))
    null_cust_count = int(null_cust_mask.sum())
    null_cust_pct = (null_cust_count / total_rows) * 100.0
    stats["missing_customer_ids"] = null_cust_count
    stats["missing_customer_ids_pct"] = round(null_cust_pct, 2)

    if null_cust_count > 0:
        issues.append(
            ValidationIssue(
                severity="WARNING",
                category="Missing Customer IDs",
                message=(
                    f"{null_cust_count:,} records ({null_cust_pct:.1f}%) have missing customer identifiers (e.g. guest transactions). "
                    "These will be included in overall business sales but excluded from customer RFM and churn modelling."
                ),
                affected_rows=null_cust_count,
                affected_pct=round(null_cust_pct, 2),
            )
        )

    # 3. Check Date validity
    try:
        parsed_dates = pd.to_datetime(df[date_col], errors="coerce")
        invalid_dates_mask = parsed_dates.isna()
        invalid_dates_count = int(invalid_dates_mask.sum())
        invalid_dates_pct = (invalid_dates_count / total_rows) * 100.0
        stats["invalid_dates"] = invalid_dates_count
        stats["invalid_dates_pct"] = round(invalid_dates_pct, 2)

        if invalid_dates_count > 0:
            issues.append(
                ValidationIssue(
                    severity="ERROR" if invalid_dates_pct > 20 else "WARNING",
                    category="Invalid Dates",
                    message=f"{invalid_dates_count:,} records ({invalid_dates_pct:.1f}%) have unparseable or null dates.",
                    affected_rows=invalid_dates_count,
                    affected_pct=round(invalid_dates_pct, 2),
                )
            )

        valid_dates = parsed_dates.dropna()
        if not valid_dates.empty:
            min_date = valid_dates.min()
            max_date = valid_dates.max()
            date_span_days = (max_date - min_date).days
            stats["min_date"] = min_date.strftime("%Y-%m-%d")
            stats["max_date"] = max_date.strftime("%Y-%m-%d")
            stats["date_span_days"] = date_span_days

            if date_span_days < 90:
                issues.append(
                    ValidationIssue(
                        severity="WARNING",
                        category="Short Historical Span",
                        message=(
                            f"The dataset spans only {date_span_days} days. Reliable 90-day future inactivity prediction "
                            "requires at least 180 to 365 days of transaction history."
                        ),
                        affected_rows=total_rows,
                        affected_pct=100.0,
                    )
                )
            else:
                issues.append(
                    ValidationIssue(
                        severity="INFO",
                        category="Historical Span",
                        message=f"Date range spans {stats['min_date']} to {stats['max_date']} ({date_span_days} days).",
                        affected_rows=0,
                        affected_pct=0.0,
                    )
                )
        else:
            stats["min_date"] = None
            stats["max_date"] = None
            stats["date_span_days"] = 0
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    category="No Valid Dates",
                    message="No valid date values could be parsed from the date column.",
                    affected_rows=total_rows,
                    affected_pct=100.0,
                )
            )
    except Exception as e:
        issues.append(
            ValidationIssue(
                severity="ERROR",
                category="Date Parsing Failure",
                message=f"Date parsing failed with error: {e!s}",
                affected_rows=total_rows,
                affected_pct=100.0,
            )
        )

    # 4. Check Quantities and Prices
    # Numeric conversion check
    numeric_qty = pd.to_numeric(df[qty_col], errors="coerce")
    invalid_qty_count = int(numeric_qty.isna().sum())
    stats["invalid_quantity_rows"] = invalid_qty_count

    numeric_price = pd.to_numeric(df[price_col], errors="coerce")
    invalid_price_count = int(numeric_price.isna().sum())
    stats["invalid_price_rows"] = invalid_price_count

    if invalid_qty_count > 0:
        issues.append(
            ValidationIssue(
                severity="ERROR",
                category="Non-Numeric Quantity",
                message=f"{invalid_qty_count:,} rows have non-numeric or empty quantity values.",
                affected_rows=invalid_qty_count,
                affected_pct=round((invalid_qty_count / total_rows) * 100.0, 2),
            )
        )

    if invalid_price_count > 0:
        issues.append(
            ValidationIssue(
                severity="ERROR",
                category="Non-Numeric Unit Price",
                message=f"{invalid_price_count:,} rows have non-numeric or empty unit price values.",
                affected_rows=invalid_price_count,
                affected_pct=round((invalid_price_count / total_rows) * 100.0, 2),
            )
        )

    # Negative quantities (cancellations/returns)
    neg_qty_mask = numeric_qty < 0
    neg_qty_count = int(neg_qty_mask.sum())
    stats["negative_quantity_rows"] = neg_qty_count
    stats["negative_quantity_pct"] = round((neg_qty_count / total_rows) * 100.0, 2)

    if neg_qty_count > 0:
        issues.append(
            ValidationIssue(
                severity="INFO",
                category="Returns and Cancellations",
                message=(
                    f"{neg_qty_count:,} records ({stats['negative_quantity_pct']}%) represent negative quantities "
                    "(returns, refunds, or order cancellations). These will be isolated into a returns audit log."
                ),
                affected_rows=neg_qty_count,
                affected_pct=stats["negative_quantity_pct"],
            )
        )

    # Zero or negative prices
    zero_or_neg_price_mask = numeric_price <= 0
    zero_price_count = int(zero_or_neg_price_mask.sum())
    stats["zero_or_negative_price_rows"] = zero_price_count
    stats["zero_or_negative_price_pct"] = round((zero_price_count / total_rows) * 100.0, 2)

    if zero_price_count > 0:
        issues.append(
            ValidationIssue(
                severity="WARNING",
                category="Zero or Negative Unit Price",
                message=(
                    f"{zero_price_count:,} records ({stats['zero_or_negative_price_pct']}%) have unit prices <= 0 "
                    "(promotional items, damages, or adjustments). These will be excluded from standard sales totals."
                ),
                affected_rows=zero_price_count,
                affected_pct=stats["zero_or_negative_price_pct"],
            )
        )

    # 5. Duplicate records
    duplicate_count = int(df.duplicated().sum())
    duplicate_pct = round((duplicate_count / total_rows) * 100.0, 2)
    stats["duplicate_rows"] = duplicate_count
    stats["duplicate_pct"] = duplicate_pct

    if duplicate_count > 0:
        issues.append(
            ValidationIssue(
                severity="WARNING",
                category="Duplicate Records",
                message=f"{duplicate_count:,} exact duplicate rows ({duplicate_pct}%) detected. They will be deduplicated.",
                affected_rows=duplicate_count,
                affected_pct=duplicate_pct,
            )
        )

    # 6. Overall validity determination
    fatal_errors = [issue for issue in issues if issue.severity == "ERROR"]
    is_valid = len(fatal_errors) == 0

    return ValidationReport(
        total_raw_rows=total_rows,
        total_raw_columns=len(df.columns),
        is_valid_for_processing=is_valid,
        issues=issues,
        stats=stats,
    )
