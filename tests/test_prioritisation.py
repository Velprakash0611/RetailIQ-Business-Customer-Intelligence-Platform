"""Unit tests for customer prioritisation and 4-quadrant assignment."""

import pandas as pd

from retail_intelligence.prioritisation import build_customer_priority_list, compute_prioritisation_summary


def test_build_customer_priority_list():
    df = pd.DataFrame({
        "customer_id": ["C1", "C2", "C3", "C4"],
        "inactivity_prob_90d": [0.85, 0.80, 0.15, 0.10],
        "total_spend": [1500.0, 100.0, 2000.0, 50.0],
        "recency_days": [60.0, 75.0, 5.0, 15.0],
    })

    priority_df = build_customer_priority_list(
        df,
        risk_threshold=0.50,
        value_percentile_cutoff=50.0,  # Top 50% spenders are high value (C1 and C3)
        risk_weight=0.60,
    )

    c1 = priority_df[priority_df["customer_id"] == "C1"].iloc[0]
    c2 = priority_df[priority_df["customer_id"] == "C2"].iloc[0]
    c3 = priority_df[priority_df["customer_id"] == "C3"].iloc[0]
    c4 = priority_df[priority_df["customer_id"] == "C4"].iloc[0]

    assert c1["priority_group"] == "High Risk, High Value"
    assert c2["priority_group"] == "High Risk, Lower Value"
    assert c3["priority_group"] == "Low Risk, High Value"
    assert c4["priority_group"] == "Low Risk, Lower Value"

    # C1 should have highest urgency rank (1)
    assert c1["urgency_rank"] == 1
    assert "priority_score" in priority_df.columns

    summary = compute_prioritisation_summary(priority_df)
    assert len(summary) == 4
    assert "suggested_action" in summary.columns
