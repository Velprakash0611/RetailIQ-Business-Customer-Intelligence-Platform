"""Unit tests for schema mapping."""

from retail_intelligence.schema_mapping import detect_column_mappings, validate_mapping


def test_detect_column_mappings_uci_style():
    uci_cols = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"]
    mapped, conf = detect_column_mappings(uci_cols)

    assert mapped["invoice_id"] == "InvoiceNo"
    assert mapped["product_id"] == "StockCode"
    assert mapped["quantity"] == "Quantity"
    assert mapped["date"] == "InvoiceDate"
    assert mapped["unit_price"] == "UnitPrice"
    assert mapped["customer_id"] == "CustomerID"
    assert mapped["country"] == "Country"

    is_valid, errors = validate_mapping(mapped)
    assert is_valid is True
    assert len(errors) == 0


def test_validate_mapping_missing_required():
    incomplete_mapping = {
        "date": "Date",
        "invoice_id": "Invoice",
        "customer_id": None,  # Missing
        "product_id": "SKU",
        "quantity": "Qty",
        "unit_price": "Price",
    }
    is_valid, errors = validate_mapping(incomplete_mapping)
    assert is_valid is False
    assert any("Customer ID" in err for err in errors)


def test_validate_mapping_duplicate_columns():
    duplicate_mapping = {
        "date": "TransactionDate",
        "invoice_id": "ID",
        "customer_id": "ID",  # Duplicate mapping to same raw column
        "product_id": "SKU",
        "quantity": "Qty",
        "unit_price": "Price",
    }
    is_valid, errors = validate_mapping(duplicate_mapping)
    assert is_valid is False
    assert any("mapped to both" in err for err in errors)
