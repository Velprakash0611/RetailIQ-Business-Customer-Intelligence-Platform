"""Unit tests for validation module."""

import numpy as np
import pandas as pd

from retail_intelligence.validation import validate_mapped_dataframe


def test_validate_clean_dataframe():
    df = pd.DataFrame({
        "InvoiceNo": ["1001", "1002", "1003"],
        "StockCode": ["A1", "B2", "C3"],
        "Quantity": [2, 5, 1],
        "InvoiceDate": ["2023-01-01", "2023-01-05", "2023-05-01"],
        "UnitPrice": [10.0, 5.5, 20.0],
        "CustomerID": ["123", "456", "789"],
    })
    mapping = {
        "invoice_id": "InvoiceNo",
        "product_id": "StockCode",
        "quantity": "Quantity",
        "date": "InvoiceDate",
        "unit_price": "UnitPrice",
        "customer_id": "CustomerID",
    }
    report = validate_mapped_dataframe(df, mapping)
    assert report.is_valid_for_processing is True
    assert report.total_raw_rows == 3


def test_validate_detects_returns_and_missing_customers():
    df = pd.DataFrame({
        "InvoiceNo": ["1001", "C1002", "1003"],
        "StockCode": ["A1", "A1", "C3"],
        "Quantity": [2, -2, 1],
        "InvoiceDate": ["2023-01-01", "2023-01-02", "2023-01-03"],
        "UnitPrice": [10.0, 10.0, 20.0],
        "CustomerID": ["123", "123", np.nan],  # Missing customer ID
    })
    mapping = {
        "invoice_id": "InvoiceNo",
        "product_id": "StockCode",
        "quantity": "Quantity",
        "date": "InvoiceDate",
        "unit_price": "UnitPrice",
        "customer_id": "CustomerID",
    }
    report = validate_mapped_dataframe(df, mapping)
    assert report.is_valid_for_processing is True
    assert report.stats["missing_customer_ids"] == 1
    assert report.stats["negative_quantity_rows"] == 1
    categories = [i.category for i in report.issues]
    assert "Missing Customer IDs" in categories
    assert "Returns and Cancellations" in categories


def test_validate_catches_non_numeric_price():
    df = pd.DataFrame({
        "InvoiceNo": ["1001"],
        "StockCode": ["A1"],
        "Quantity": [1],
        "InvoiceDate": ["2023-01-01"],
        "UnitPrice": ["FREE"],  # Non-numeric
        "CustomerID": ["123"],
    })
    mapping = {
        "invoice_id": "InvoiceNo",
        "product_id": "StockCode",
        "quantity": "Quantity",
        "date": "InvoiceDate",
        "unit_price": "UnitPrice",
        "customer_id": "CustomerID",
    }
    report = validate_mapped_dataframe(df, mapping)
    assert report.is_valid_for_processing is False
    assert any(i.severity == "ERROR" and "Unit Price" in i.category for i in report.issues)
