"""
Segmentation module for RetailIQ.
Computes classical and quantile-based RFM scoring and maps customers to
actionable business segments.
"""

import pandas as pd


def _score_quantiles(series: pd.Series, ascending: bool = True, bins: int = 5) -> pd.Series:
    """
    Assigns 1..bins score based on quantile ranking.
    If ascending=False, lower values get higher scores (e.g., Recency).
    Safely handles duplicate values by using percent_rank.
    """
    if series.empty or series.nunique() <= 1:
        return pd.Series(3, index=series.index, dtype=int)

    rank = series.rank(method="first", ascending=ascending)
    scores = pd.qcut(rank, q=bins, labels=False, duplicates="drop") + 1
    return scores.astype(int)


def assign_rfm_segments(
    customer_features_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Takes customer features (containing recency_days, frequency, total_spend)
    and computes R, F, M scores and assigned business segment.
    """
    if customer_features_df.empty:
        return pd.DataFrame()

    df = customer_features_df.copy()

    # Recency: lower days is better -> ascending=False
    df["r_score"] = _score_quantiles(df["recency_days"], ascending=False, bins=5)
    # Frequency: higher count is better -> ascending=True
    df["f_score"] = _score_quantiles(df["frequency"], ascending=True, bins=5)
    # Monetary: higher spend is better -> ascending=True
    df["m_score"] = _score_quantiles(df["total_spend"], ascending=True, bins=5)

    df["rfm_score"] = (
        df["r_score"].astype(str) + df["f_score"].astype(str) + df["m_score"].astype(str)
    )

    # Segment mapping rules
    def get_segment(r: int, f: int, m: int) -> str:
        # Champions: bought recently, buy often, spend the most
        if r >= 4 and f >= 4 and m >= 4:
            return "Champions"
        # Loyal Customers: spend good money, responsive to promotions
        elif (r >= 3 and f >= 3) or (f >= 4 and m >= 3):
            return "Loyal Customers"
        # Potential Loyalists: recent customers with average frequency
        elif r >= 4 and f in [2, 3]:
            return "Potential Loyalists"
        # New Customers: bought most recently, but frequency is 1
        elif r >= 4 and f == 1:
            return "New Customers"
        # Promising: recent shoppers with small spend
        elif r == 3 and f == 1:
            return "Promising"
        # Need Attention: above average recency, frequency & monetary values
        elif r == 3 and f in [2, 3]:
            return "Need Attention"
        # About to Sleep: below average recency & frequency
        elif r in [2, 3] and f <= 2:
            return "About to Sleep"
        # Can't Lose Them: made big purchases and often, but haven't returned for a long time
        elif r <= 2 and f >= 4 and m >= 4:
            return "Can't Lose Them"
        # At Risk: spent big money and purchased often a long time ago
        elif r <= 2 and (f >= 3 or m >= 3):
            return "At Risk"
        # Hibernating: low frequency, low spend, last purchase was long ago
        elif r <= 2 and f <= 2 and m <= 2:
            return "Hibernating"
        # Lost: lowest recency, frequency, monetary
        else:
            return "Lost / Inactive"

    df["segment"] = [
        get_segment(r, f, m)
        for r, f, m in zip(df["r_score"], df["f_score"], df["m_score"])
    ]

    return df


def compute_segment_summary(
    segmented_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Aggregates statistics by RFM segment: count, % of customers, total spend,
    mean spend, mean frequency, mean recency.
    """
    if segmented_df.empty or "segment" not in segmented_df.columns:
        return pd.DataFrame()

    total_custs = len(segmented_df)
    total_rev = segmented_df["total_spend"].sum()

    summary = segmented_df.groupby("segment").agg(
        customer_count=("customer_id", "count"),
        total_revenue=("total_spend", "sum"),
        avg_revenue=("total_spend", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_recency_days=("recency_days", "mean"),
    ).reset_index()

    summary["pct_customers"] = ((summary["customer_count"] / total_custs) * 100.0).round(1)
    summary["pct_revenue"] = ((summary["total_revenue"] / total_rev) * 100.0).round(1) if total_rev > 0 else 0.0

    summary["total_revenue"] = summary["total_revenue"].round(2)
    summary["avg_revenue"] = summary["avg_revenue"].round(2)
    summary["avg_frequency"] = summary["avg_frequency"].round(1)
    summary["avg_recency_days"] = summary["avg_recency_days"].round(1)

    # Order segments logically
    segment_order = [
        "Champions",
        "Loyal Customers",
        "Potential Loyalists",
        "New Customers",
        "Promising",
        "Need Attention",
        "About to Sleep",
        "Can't Lose Them",
        "At Risk",
        "Hibernating",
        "Lost / Inactive",
    ]
    summary["sort_order"] = summary["segment"].map(
        lambda s: segment_order.index(s) if s in segment_order else 99
    )
    return summary.sort_values(by="sort_order").drop(columns=["sort_order"]).reset_index(drop=True)
