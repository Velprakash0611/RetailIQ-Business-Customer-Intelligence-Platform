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


def test_compute_sales_trends_frequencies():
    from retail_intelligence.metrics import compute_sales_trends
    sales_df = pd.DataFrame({
        "date": pd.to_datetime(["2023-01-01", "2023-01-15", "2023-02-05"]),
        "invoice_id": ["I1", "I2", "I3"],
        "customer_id": ["C1", "C2", "C1"],
        "quantity": [2, 1, 3],
        "unit_price": [10.0, 20.0, 10.0],
        "total_amount": [20.0, 20.0, 30.0],
    })

    # Test daily
    trend_d = compute_sales_trends(sales_df, freq="D")
    assert len(trend_d) == 3

    # Test weekly
    trend_w = compute_sales_trends(sales_df, freq="W")
    assert not trend_w.empty

    # Test monthly with "M"
    trend_m = compute_sales_trends(sales_df, freq="M")
    assert len(trend_m) == 2

    # Test monthly with "MS" (ensures offset aliases are properly handled)
    trend_ms = compute_sales_trends(sales_df, freq="MS")
    assert len(trend_ms) == 2
    assert trend_ms["revenue"].sum() == 70.0

