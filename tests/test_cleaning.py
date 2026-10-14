"""Unit tests for cleaning module."""

import numpy as np
import pandas as pd

from retail_intelligence.cleaning import clean_and_standardize_data


def test_cleaning_pipeline_behavior():
    raw_df = pd.DataFrame({
        "InvoiceNo": ["1001", "1001", "C1002", "1003", "1004"],
        "StockCode": ["P1", "P1", "P1", "P2", "P3"],
        "Quantity": [2, 2, -1, 4, 1],
        "InvoiceDate": ["2023-01-01 10:00:00", "2023-01-01 10:00:00", "2023-01-02 11:00:00", "2023-01-03 12:00:00", "2023-01-04 15:00:00"],
        "UnitPrice": [5.0, 5.0, 5.0, 0.0, 10.0],  # One duplicate row, one return, one zero-price
        "CustomerID": ["101.0", "101.0", "101.0", "102.0", np.nan],  # Last is guest
    })
    mapping = {
        "invoice_id": "InvoiceNo",
        "product_id": "StockCode",
        "quantity": "Quantity",
        "date": "InvoiceDate",
        "unit_price": "UnitPrice",
        "customer_id": "CustomerID",
    }

    clean_sales, returns, rejected, summary = clean_and_standardize_data(raw_df, mapping)

    # 1 duplicate removed, 1 zero-price rejected
    assert summary["duplicates_removed"] == 1
    assert summary["rejected_rows"] == 2  # 1 duplicate + 1 zero price
    # 1 return
    assert len(returns) == 1
    assert returns.iloc[0]["invoice_id"] == "C1002"
    # Clean sales should have 2 records: invoice 1001 (first copy) and invoice 1004 (guest)
    assert len(clean_sales) == 2
    # Verify customer ID cleaning (101.0 -> 101)
    assert clean_sales.iloc[0]["customer_id"] == "101"
    assert bool(clean_sales.iloc[0]["is_guest"]) is False
    # Guest record
    assert bool(clean_sales.iloc[1]["is_guest"]) is True
    assert clean_sales.iloc[1]["customer_id"] == "GUEST_CHECKOUT"
