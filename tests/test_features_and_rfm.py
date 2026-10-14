"""Unit tests for customer features and RFM segmentation."""

import pandas as pd

from retail_intelligence.customer_features import compute_customer_features
from retail_intelligence.segmentation import assign_rfm_segments, compute_segment_summary


def test_customer_features_point_in_time():
    sales_df = pd.DataFrame({
        "date": pd.to_datetime(["2023-01-01", "2023-02-01", "2023-04-01"]),
        "invoice_id": ["I1", "I2", "I3"],
        "customer_id": ["C1", "C1", "C1"],
        "is_guest": [False, False, False],
        "product_id": ["P1", "P2", "P3"],
        "quantity": [2, 1, 4],
        "unit_price": [10.0, 20.0, 15.0],
        "total_amount": [20.0, 20.0, 60.0],
    })

    # Cutoff date 2023-03-01: should only observe I1 and I2, NOT I3!
    cutoff = pd.Timestamp("2023-03-01")
    feats = compute_customer_features(sales_df, cutoff_date=cutoff)

    assert len(feats) == 1
    row = feats.iloc[0]
    assert row["customer_id"] == "C1"
    assert row["frequency"] == 2  # Only 2 orders before cutoff
    assert row["total_spend"] == 40.0  # 20 + 20
    assert row["recency_days"] == 28.0  # March 1 - Feb 1 = 28 days


def test_rfm_segments_assignment():
    cust_df = pd.DataFrame({
        "customer_id": [f"C{i}" for i in range(1, 21)],
        "recency_days": [5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 120, 140, 160, 180, 200, 220, 250],
        "frequency": [10, 9, 8, 7, 6, 5, 5, 4, 4, 3, 3, 2, 2, 2, 1, 1, 1, 1, 1, 1],
        "total_spend": [1000, 900, 800, 700, 600, 500, 450, 400, 350, 300, 250, 200, 180, 150, 100, 80, 60, 50, 30, 20],
    })

    segmented = assign_rfm_segments(cust_df)
    assert "segment" in segmented.columns
    assert "r_score" in segmented.columns
    assert "f_score" in segmented.columns
    assert "m_score" in segmented.columns
    assert segmented.iloc[0]["segment"] == "Champions"

    summary = compute_segment_summary(segmented)
    assert not summary.empty
    assert "customer_count" in summary.columns
    assert "total_revenue" in summary.columns
