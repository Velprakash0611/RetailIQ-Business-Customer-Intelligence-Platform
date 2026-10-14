"""Unit tests for business metrics and analytics."""

import pandas as pd

from retail_intelligence.metrics import (
    compute_executive_kpis,
    compute_top_products,
)


def test_compute_executive_kpis():
    sales_df = pd.DataFrame({
        "date": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
        "invoice_id": ["INV1", "INV2", "INV3"],
        "customer_id": ["C1", "C2", "C1"],
        "is_guest": [False, False, False],
        "quantity": [2, 1, 3],
        "unit_price": [10.0, 20.0, 10.0],
        "total_amount": [20.0, 20.0, 30.0],
    })
    returns_df = pd.DataFrame({
        "date": pd.to_datetime(["2023-01-04"]),
        "invoice_id": ["C_INV1"],
        "customer_id": ["C1"],
        "quantity": [1],
        "unit_price": [10.0],
        "total_amount": [10.0],
    })

    kpis = compute_executive_kpis(sales_df, returns_df)
    assert kpis["gross_revenue"] == 70.0
    assert kpis["returns_revenue"] == 10.0
    assert kpis["net_revenue"] == 60.0
    assert kpis["total_orders"] == 3
    assert kpis["registered_customers"] == 2
    assert round(kpis["average_order_value"], 2) == 23.33


def test_compute_top_products():
    sales_df = pd.DataFrame({
        "product_id": ["P1", "P2", "P1"],
        "description": ["Product 1", "Product 2", "Product 1"],
        "quantity": [5, 20, 5],
        "total_amount": [50.0, 40.0, 50.0],
        "invoice_id": ["I1", "I2", "I3"],
    })
    top_rev = compute_top_products(sales_df, top_n=2, by="revenue")
    assert top_rev.iloc[0]["product_id"] == "P1"
    assert top_rev.iloc[0]["revenue"] == 100.0

    top_qty = compute_top_products(sales_df, top_n=2, by="quantity")
    assert top_qty.iloc[0]["product_id"] == "P2"
    assert top_qty.iloc[0]["quantity"] == 20
