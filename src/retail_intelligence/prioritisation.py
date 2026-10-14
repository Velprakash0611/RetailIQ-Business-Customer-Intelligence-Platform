"""
Prioritisation module for RetailIQ.
Combines predictive inactivity risk with historical customer value to build
actionable 4-quadrant segments and configurable priority rankings.
"""

import numpy as np
import pandas as pd

PRIORITY_GROUPS = {
    "High Risk, High Value": {
        "label": "High Risk, High Value (VIP At-Risk)",
        "action": "Review first for targeted retention campaign.",
        "badge_color": "#dc3545",  # danger/red
        "urgency": 1,
    },
    "High Risk, Lower Value": {
        "label": "High Risk, Lower Value (Churning Base)",
        "action": "Consider lower-cost automated re-engagement.",
        "badge_color": "#fd7e14",  # orange
        "urgency": 2,
    },
    "Low Risk, High Value": {
        "label": "Low Risk, High Value (VIP Loyals)",
        "action": "Focus on loyalty, VIP rewards, and repeat purchases.",
        "badge_color": "#198754",  # success/green
        "urgency": 3,
    },
    "Low Risk, Lower Value": {
        "label": "Low Risk, Lower Value (Routine Shoppers)",
        "action": "Continue routine monitoring.",
        "badge_color": "#6c757d",  # secondary/gray
        "urgency": 4,
    },
}


def build_customer_priority_list(
    predictions_df: pd.DataFrame,
    risk_threshold: float = 0.50,
    value_percentile_cutoff: float = 70.0,  # Top 30% are high value
    risk_weight: float = 0.60,              # 0.0 to 1.0
) -> pd.DataFrame:
    """
    Combines inactivity probability with monetary value into 4 priority quadrants
    and a normalized composite priority score (0 to 100).
    """
    if predictions_df.empty:
        return pd.DataFrame()

    df = predictions_df.copy()

    # Determine monetary value threshold based on percentile
    val_cutoff_amount = float(np.percentile(df["total_spend"], value_percentile_cutoff))
    df["is_high_value"] = df["total_spend"] >= val_cutoff_amount
    df["is_high_risk"] = df["inactivity_prob_90d"] >= risk_threshold

    # Assign 4 quadrants
    def assign_priority_group(row) -> str:
        if row["is_high_risk"] and row["is_high_value"]:
            return "High Risk, High Value"
        elif row["is_high_risk"] and not row["is_high_value"]:
            return "High Risk, Lower Value"
        elif not row["is_high_risk"] and row["is_high_value"]:
            return "Low Risk, High Value"
        else:
            return "Low Risk, Lower Value"

    df["priority_group"] = df.apply(assign_priority_group, axis=1)
    df["suggested_action"] = df["priority_group"].map(lambda g: PRIORITY_GROUPS[g]["action"])
    df["urgency_rank"] = df["priority_group"].map(lambda g: PRIORITY_GROUPS[g]["urgency"])

    # Composite Priority Score (0 - 100)
    # Normalized risk: 0 to 1
    norm_risk = df["inactivity_prob_90d"].clip(0, 1)

    # Normalized value: percentile rank of total spend (0 to 1)
    norm_val = df["total_spend"].rank(pct=True)

    val_weight = 1.0 - risk_weight
    df["priority_score"] = np.round((risk_weight * norm_risk + val_weight * norm_val) * 100.0, 1)

    # Sort descending by priority score
    return df.sort_values(by=["urgency_rank", "priority_score"], ascending=[True, False]).reset_index(drop=True)


def compute_prioritisation_summary(
    prioritised_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Generates summary metrics across the 4 priority quadrants.
    """
    if prioritised_df.empty or "priority_group" not in prioritised_df.columns:
        return pd.DataFrame()

    total_customers = len(prioritised_df)
    total_revenue = prioritised_df["total_spend"].sum()

    grp = prioritised_df.groupby("priority_group").agg(
        customer_count=("customer_id", "count"),
        total_spend=("total_spend", "sum"),
        avg_spend=("total_spend", "mean"),
        avg_risk_prob=("inactivity_prob_90d", "mean"),
        avg_recency_days=("recency_days", "mean"),
    ).reset_index()

    grp["pct_of_customers"] = ((grp["customer_count"] / total_customers) * 100.0).round(1)
    grp["pct_of_revenue"] = ((grp["total_spend"] / total_revenue) * 100.0).round(1) if total_revenue > 0 else 0.0

    grp["total_spend"] = grp["total_spend"].round(2)
    grp["avg_spend"] = grp["avg_spend"].round(2)
    grp["avg_risk_prob"] = (grp["avg_risk_prob"] * 100.0).round(1)
    grp["avg_recency_days"] = grp["avg_recency_days"].round(1)
    grp["suggested_action"] = grp["priority_group"].map(lambda g: PRIORITY_GROUPS[g]["action"])

    # Urgency order
    grp["urgency"] = grp["priority_group"].map(lambda g: PRIORITY_GROUPS[g]["urgency"])
    return grp.sort_values(by="urgency").drop(columns=["urgency"]).reset_index(drop=True)
