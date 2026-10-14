"""
Schema mapping module for RetailIQ.
Handles column name heuristics, auto-detection, and mapping validation.
"""

import re

# Canonical required and optional fields
CANONICAL_REQUIRED_FIELDS = [
    "date",
    "invoice_id",
    "customer_id",
    "product_id",
    "quantity",
    "unit_price",
]

CANONICAL_OPTIONAL_FIELDS = [
    "country",
    "currency",
    "description",
]

FIELD_LABELS = {
    "date": "Transaction Date",
    "invoice_id": "Invoice / Order ID",
    "customer_id": "Customer ID",
    "product_id": "Product SKU / ID",
    "quantity": "Quantity",
    "unit_price": "Unit Price",
    "country": "Country (Optional)",
    "currency": "Currency (Optional)",
    "description": "Product Description (Optional)",
}

# Heuristic regex patterns for common column naming variations
HEURISTIC_PATTERNS: dict[str, list[str]] = {
    "date": [
        r"^invoicedate$",
        r"^invoice_date$",
        r"^order_date$",
        r"^orderdate$",
        r"^transaction_date$",
        r"^tx_date$",
        r"^date$",
        r"^timestamp$",
        r"^created_at$",
        r"^purchase_date$",
    ],
    "invoice_id": [
        r"^invoiceno$",
        r"^invoice_no$",
        r"^invoice_id$",
        r"^invoice$",
        r"^order_id$",
        r"^orderid$",
        r"^orderno$",
        r"^order_number$",
        r"^transaction_id$",
        r"^trans_id$",
        r"^bill_no$",
    ],
    "customer_id": [
        r"^customerid$",
        r"^customer_id$",
        r"^cust_id$",
        r"^client_id$",
        r"^user_id$",
        r"^account_id$",
        r"^buyer_id$",
        r"^shopper_id$",
    ],
    "product_id": [
        r"^stockcode$",
        r"^stock_code$",
        r"^product_id$",
        r"^productid$",
        r"^item_id$",
        r"^item_code$",
        r"^sku$",
        r"^product_sku$",
        r"^item$",
    ],
    "quantity": [
        r"^quantity$",
        r"^qty$",
        r"^volume$",
        r"^units$",
        r"^item_count$",
        r"^units_sold$",
    ],
    "unit_price": [
        r"^unitprice$",
        r"^unit_price$",
        r"^price$",
        r"^item_price$",
        r"^rate$",
        r"^cost$",
        r"^unit_cost$",
        r"^sales_price$",
    ],
    "country": [
        r"^country$",
        r"^country_name$",
        r"^nation$",
        r"^region$",
        r"^market$",
    ],
    "currency": [
        r"^currency$",
        r"^curr$",
        r"^currency_code$",
    ],
    "description": [
        r"^description$",
        r"^desc$",
        r"^item_description$",
        r"^product_name$",
        r"^product_title$",
        r"^title$",
    ],
}


def normalize_col_name(col: str) -> str:
    """Normalize column names by lowercasing and stripping non-alphanumeric chars except underscores."""
    col_str = str(col).strip().lower()
    return re.sub(r"[\s\-]+", "_", col_str)


def detect_column_mappings(columns: list[str]) -> tuple[dict[str, str | None], dict[str, float]]:
    """
    Automatically suggest canonical mappings for a list of columns.
    Returns:
        mapped_dict: {canonical_field: detected_original_column or None}
        confidence_scores: {canonical_field: float_score}
    """
    mapped: dict[str, str | None] = {field: None for field in CANONICAL_REQUIRED_FIELDS + CANONICAL_OPTIONAL_FIELDS}
    confidence: dict[str, float] = {field: 0.0 for field in mapped}

    used_columns = set()

    # Pass 1: Exact / regex matches
    for canonical_field, patterns in HEURISTIC_PATTERNS.items():
        for col in columns:
            if col in used_columns:
                continue
            norm_col = normalize_col_name(col)
            for pat in patterns:
                if re.match(pat, norm_col):
                    mapped[canonical_field] = col
                    confidence[canonical_field] = 0.95
                    used_columns.add(col)
                    break
            if mapped[canonical_field] is not None:
                break

    # Pass 2: Substring matching for unmapped required fields
    for canonical_field, patterns in HEURISTIC_PATTERNS.items():
        if mapped[canonical_field] is not None:
            continue
        for col in columns:
            if col in used_columns:
                continue
            norm_col = normalize_col_name(col)
            if canonical_field in norm_col:
                mapped[canonical_field] = col
                confidence[canonical_field] = 0.70
                used_columns.add(col)
                break

    return mapped, confidence


def validate_mapping(mapping: dict[str, str | None]) -> tuple[bool, list[str]]:
    """
    Validate that all required canonical fields have been mapped to non-empty column names.
    Returns:
        (is_valid, list_of_missing_or_duplicate_errors)
    """
    errors: list[str] = []
    
    # Check for missing required fields
    for req in CANONICAL_REQUIRED_FIELDS:
        val = mapping.get(req)
        if not val or str(val).strip() == "" or str(val).strip().lower() == "none":
            errors.append(f"Missing required field mapping: '{FIELD_LABELS.get(req, req)}'")

    # Check for duplicates (multiple canonical fields mapped to the exact same column)
    seen_cols: dict[str, str] = {}
    for canon, col in mapping.items():
        if col and str(col).strip() != "" and str(col).strip().lower() != "none":
            if col in seen_cols:
                errors.append(
                    f"Column '{col}' is mapped to both '{FIELD_LABELS.get(seen_cols[col], seen_cols[col])}' "
                    f"and '{FIELD_LABELS.get(canon, canon)}'. Each column must be unique."
                )
            else:
                seen_cols[col] = canon

    return len(errors) == 0, errors
