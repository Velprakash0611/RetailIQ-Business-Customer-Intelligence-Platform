"""
Cleaning module for RetailIQ.
Standardizes schema, handles cancellations and returns, manages guest transactions,
removes duplicate records, and generates an audit log of rejected records.
"""

from typing import Any

import pandas as pd


def clean_and_standardize_data(
    df: pd.DataFrame,
    mapping: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """
    Cleans raw transactions according to retail business logic.
    Returns:
        clean_sales_df: Standardized positive sales transactions (registered and guest)
        returns_df: Standardized returns/cancellations (for return analysis)
        rejected_df: Audit table of excluded rows with reason
        summary: Dictionary of cleaning counts and financial totals
    """
    total_raw_rows = len(df)
    
    # 1. Rename to canonical columns
    rename_dict = {
        mapping["date"]: "date",
        mapping["invoice_id"]: "invoice_id",
        mapping["customer_id"]: "customer_id",
        mapping["product_id"]: "product_id",
        mapping["quantity"]: "quantity",
        mapping["unit_price"]: "unit_price",
    }
    
    if mapping.get("country") and mapping["country"] in df.columns:
        rename_dict[mapping["country"]] = "country"
    if mapping.get("currency") and mapping["currency"] in df.columns:
        rename_dict[mapping["currency"]] = "currency"
    if mapping.get("description") and mapping["description"] in df.columns:
        rename_dict[mapping["description"]] = "description"

    working_df = df.copy()

    # Create working copy with canonical columns
    std_df = pd.DataFrame()
    for raw_col, canon_col in rename_dict.items():
        std_df[canon_col] = working_df[raw_col]

    # Fill optional columns if missing
    if "country" not in std_df.columns:
        std_df["country"] = "Global / Unspecified"
    else:
        std_df["country"] = std_df["country"].fillna("Global / Unspecified").astype(str).str.strip()

    if "currency" not in std_df.columns:
        std_df["currency"] = "USD"
    else:
        std_df["currency"] = std_df["currency"].fillna("USD").astype(str).str.strip()

    if "description" not in std_df.columns:
        std_df["description"] = std_df["product_id"].astype(str)
    else:
        std_df["description"] = std_df["description"].fillna(std_df["product_id"].astype(str)).astype(str).str.strip()

    # Track rejection reasons
    rejection_reasons = pd.Series(index=std_df.index, dtype="object")

    # 2. De-duplicate exact duplicates
    dup_mask = std_df.duplicated(keep="first")
    rejection_reasons[dup_mask] = "Exact duplicate record"

    # 3. Parse date
    std_df["parsed_date"] = pd.to_datetime(std_df["date"], errors="coerce")
    bad_date_mask = std_df["parsed_date"].isna() & rejection_reasons.isna()
    rejection_reasons[bad_date_mask] = "Invalid / unparseable transaction date"

    # 4. Parse quantity and unit price
    std_df["num_qty"] = pd.to_numeric(std_df["quantity"], errors="coerce")
    std_df["num_price"] = pd.to_numeric(std_df["unit_price"], errors="coerce")

    bad_numeric_mask = (std_df["num_qty"].isna() | std_df["num_price"].isna()) & rejection_reasons.isna()
    rejection_reasons[bad_numeric_mask] = "Non-numeric quantity or unit price"

    # 5. Clean strings
    std_df["clean_invoice_id"] = std_df["invoice_id"].astype(str).str.strip()
    std_df["clean_product_id"] = std_df["product_id"].astype(str).str.strip()

    # 6. Flag returns / cancellations:
    # A transaction is a return if quantity < 0 or invoice starts with 'C' or 'c'
    is_cancelled_inv = std_df["clean_invoice_id"].str.upper().str.startswith("C")
    is_neg_qty = std_df["num_qty"] < 0
    is_return_mask = (is_cancelled_inv | is_neg_qty) & rejection_reasons.isna()

    # 7. Check zero / negative unit prices on positive transactions
    zero_price_mask = (std_df["num_price"] <= 0) & (~is_return_mask) & rejection_reasons.isna()
    rejection_reasons[zero_price_mask] = "Zero or negative unit price on non-return item"

    # 8. Separate rejected rows
    rejected_rows_mask = rejection_reasons.notna()
    rejected_df = std_df[rejected_rows_mask].copy()
    rejected_df["rejection_reason"] = rejection_reasons[rejected_rows_mask]

    # 9. Clean returns
    raw_returns_df = std_df[is_return_mask].copy()
    returns_df = pd.DataFrame({
        "date": raw_returns_df["parsed_date"],
        "invoice_id": raw_returns_df["clean_invoice_id"],
        "customer_id": raw_returns_df["customer_id"].fillna("GUEST").astype(str).str.strip().str.replace(r"\.0$", "", regex=True),
        "product_id": raw_returns_df["clean_product_id"],
        "description": raw_returns_df["description"],
        "quantity": raw_returns_df["num_qty"].abs(),  # Absolute count returned
        "unit_price": raw_returns_df["num_price"].abs(),
        "total_amount": raw_returns_df["num_qty"].abs() * raw_returns_df["num_price"].abs(),
        "country": raw_returns_df["country"],
        "currency": raw_returns_df["currency"],
    })

    # 10. Clean positive sales
    clean_sales_mask = (~rejected_rows_mask) & (~is_return_mask)
    raw_sales_df = std_df[clean_sales_mask].copy()

    # Handle customer IDs: Clean float strings like "12345.0" to "12345"
    cust_str = raw_sales_df["customer_id"].astype(str).str.strip()
    is_guest_mask = raw_sales_df["customer_id"].isna() | cust_str.isin(["", "nan", "NaN", "None", "null", "NULL", "0", "0.0"])

    clean_cust_ids = cust_str.str.replace(r"\.0$", "", regex=True)
    clean_cust_ids = clean_cust_ids.mask(is_guest_mask, "GUEST_CHECKOUT")

    clean_sales_df = pd.DataFrame({
        "date": raw_sales_df["parsed_date"],
        "invoice_id": raw_sales_df["clean_invoice_id"],
        "customer_id": clean_cust_ids,
        "is_guest": is_guest_mask.values,
        "product_id": raw_sales_df["clean_product_id"],
        "description": raw_sales_df["description"],
        "quantity": raw_sales_df["num_qty"],
        "unit_price": raw_sales_df["num_price"],
        "total_amount": raw_sales_df["num_qty"] * raw_sales_df["num_price"],
        "country": raw_sales_df["country"],
        "currency": raw_sales_df["currency"],
    })

    # Sort sales chronologically
    clean_sales_df = clean_sales_df.sort_values(by="date").reset_index(drop=True)
    returns_df = returns_df.sort_values(by="date").reset_index(drop=True)

    # 11. Compute Summary Stats
    total_sales_rev = float(clean_sales_df["total_amount"].sum())
    total_returns_rev = float(returns_df["total_amount"].sum())
    net_rev = total_sales_rev - total_returns_rev
    guest_rev = float(clean_sales_df[clean_sales_df["is_guest"]]["total_amount"].sum())
    registered_rev = float(clean_sales_df[~clean_sales_df["is_guest"]]["total_amount"].sum())

    summary = {
        "total_raw_rows": total_raw_rows,
        "clean_sales_rows": len(clean_sales_df),
        "returns_rows": len(returns_df),
        "rejected_rows": len(rejected_df),
        "duplicates_removed": int(dup_mask.sum()),
        "guest_rows": int(is_guest_mask.sum()),
        "registered_rows": int((~is_guest_mask).sum()),
        "total_gross_revenue": round(total_sales_rev, 2),
        "total_returns_revenue": round(total_returns_rev, 2),
        "net_revenue": round(net_rev, 2),
        "guest_revenue": round(guest_rev, 2),
        "registered_revenue": round(registered_rev, 2),
        "currency": clean_sales_df["currency"].iloc[0] if not clean_sales_df.empty else "USD",
        "date_min": clean_sales_df["date"].min().strftime("%Y-%m-%d") if not clean_sales_df.empty else None,
        "date_max": clean_sales_df["date"].max().strftime("%Y-%m-%d") if not clean_sales_df.empty else None,
    }

    return clean_sales_df, returns_df, rejected_df, summary
