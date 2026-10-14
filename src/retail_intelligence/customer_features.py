"""
Customer features module for RetailIQ.
Computes point-in-time customer behavioral and transactional features strictly as of
a specified cutoff date, preventing future data leakage.
"""


import numpy as np
import pandas as pd


def compute_customer_features(
    sales_df: pd.DataFrame,
    cutoff_date: pd.Timestamp | None = None,
    returns_df: pd.DataFrame | None = None,
    min_orders: int = 1,
) -> pd.DataFrame:
    """
    Computes customer features using only transactions on or before cutoff_date.
    Only registered customers (non-guest) are included.
    """
    if sales_df.empty:
        return pd.DataFrame()

    if cutoff_date is None:
        cutoff_date = sales_df["date"].max()

    # Filter to registered transactions on or before cutoff_date
    obs_sales = sales_df[(sales_df["date"] <= cutoff_date) & (~sales_df["is_guest"])].copy()

    if obs_sales.empty:
        return pd.DataFrame()

    # Pre-calculate trailing window start dates
    d_30 = cutoff_date - pd.Timedelta(days=30)
    d_90 = cutoff_date - pd.Timedelta(days=90)
    d_180 = cutoff_date - pd.Timedelta(days=180)

    # Base aggregation per customer
    # Group by customer_id and invoice_id first to get order-level statistics
    order_grp = obs_sales.groupby(["customer_id", "invoice_id"]).agg(
        order_date=("date", "max"),
        order_spend=("total_amount", "sum"),
        order_units=("quantity", "sum"),
        order_items=("product_id", "nunique"),
    ).reset_index()

    # Aggregate to customer level
    cust_agg = order_grp.groupby("customer_id").agg(
        frequency=("invoice_id", "count"),
        first_purchase_date=("order_date", "min"),
        last_purchase_date=("order_date", "max"),
        total_spend=("order_spend", "sum"),
        avg_order_value=("order_spend", "mean"),
        max_order_spend=("order_spend", "max"),
        min_order_spend=("order_spend", "min"),
        total_units=("order_units", "sum"),
        avg_units_per_order=("order_units", "mean"),
    ).reset_index()

    # Filter by minimum orders if needed
    if min_orders > 1:
        cust_agg = cust_agg[cust_agg["frequency"] >= min_orders].copy()
        if cust_agg.empty:
            return pd.DataFrame()

    # Distinct products purchased across all items
    distinct_prods = obs_sales.groupby("customer_id")["product_id"].nunique().rename("distinct_products")
    cust_agg = cust_agg.merge(distinct_prods, on="customer_id", how="left")

    # Time-based features
    cust_agg["recency_days"] = (cutoff_date - cust_agg["last_purchase_date"]).dt.total_seconds() / 86400.0
    cust_agg["tenure_days"] = (cutoff_date - cust_agg["first_purchase_date"]).dt.total_seconds() / 86400.0

    # Average days between orders (for repeat customers)
    days_active = (cust_agg["last_purchase_date"] - cust_agg["first_purchase_date"]).dt.total_seconds() / 86400.0
    cust_agg["avg_days_between_orders"] = np.where(
        cust_agg["frequency"] > 1,
        days_active / (cust_agg["frequency"] - 1),
        0.0,
    )

    # Trailing window aggregations (last 30d, 90d, 180d)
    w30_orders = order_grp[order_grp["order_date"] >= d_30].groupby("customer_id")["invoice_id"].count().rename("orders_last_30d")
    w30_spend = order_grp[order_grp["order_date"] >= d_30].groupby("customer_id")["order_spend"].sum().rename("spend_last_30d")

    w90_orders = order_grp[order_grp["order_date"] >= d_90].groupby("customer_id")["invoice_id"].count().rename("orders_last_90d")
    w90_spend = order_grp[order_grp["order_date"] >= d_90].groupby("customer_id")["order_spend"].sum().rename("spend_last_90d")

    w180_orders = order_grp[order_grp["order_date"] >= d_180].groupby("customer_id")["invoice_id"].count().rename("orders_last_180d")
    w180_spend = order_grp[order_grp["order_date"] >= d_180].groupby("customer_id")["order_spend"].sum().rename("spend_last_180d")

    cust_agg = cust_agg.merge(w30_orders, on="customer_id", how="left")
    cust_agg = cust_agg.merge(w30_spend, on="customer_id", how="left")
    cust_agg = cust_agg.merge(w90_orders, on="customer_id", how="left")
    cust_agg = cust_agg.merge(w90_spend, on="customer_id", how="left")
    cust_agg = cust_agg.merge(w180_orders, on="customer_id", how="left")
    cust_agg = cust_agg.merge(w180_spend, on="customer_id", how="left")

    cust_agg["orders_last_30d"] = cust_agg["orders_last_30d"].fillna(0).astype(int)
    cust_agg["spend_last_30d"] = cust_agg["spend_last_30d"].fillna(0.0).round(2)
    cust_agg["orders_last_90d"] = cust_agg["orders_last_90d"].fillna(0).astype(int)
    cust_agg["spend_last_90d"] = cust_agg["spend_last_90d"].fillna(0.0).round(2)
    cust_agg["orders_last_180d"] = cust_agg["orders_last_180d"].fillna(0).astype(int)
    cust_agg["spend_last_180d"] = cust_agg["spend_last_180d"].fillna(0.0).round(2)

    # Momentum/Velocity: Ratio of 30d spend to 90d spend (scaled by 3)
    cust_agg["spend_velocity_30_90"] = np.where(
        cust_agg["spend_last_90d"] > 0,
        (cust_agg["spend_last_30d"] * 3.0) / cust_agg["spend_last_90d"],
        0.0,
    ).round(2)

    # Returns metrics up to cutoff
    if returns_df is not None and not returns_df.empty:
        obs_returns = returns_df[returns_df["date"] <= cutoff_date]
        ret_grp = obs_returns.groupby("customer_id").agg(
            return_count=("quantity", "sum"),
            return_spend=("total_amount", "sum"),
        ).reset_index()
        cust_agg = cust_agg.merge(ret_grp, on="customer_id", how="left")
        cust_agg["return_count"] = cust_agg["return_count"].fillna(0).astype(int)
        cust_agg["return_spend"] = cust_agg["return_spend"].fillna(0.0).round(2)
    else:
        cust_agg["return_count"] = 0
        cust_agg["return_spend"] = 0.0

    # Clean rounding
    cust_agg["recency_days"] = cust_agg["recency_days"].round(1)
    cust_agg["tenure_days"] = cust_agg["tenure_days"].round(1)
    cust_agg["avg_days_between_orders"] = cust_agg["avg_days_between_orders"].round(1)
    cust_agg["total_spend"] = cust_agg["total_spend"].round(2)
    cust_agg["avg_order_value"] = cust_agg["avg_order_value"].round(2)
    cust_agg["max_order_spend"] = cust_agg["max_order_spend"].round(2)
    cust_agg["min_order_spend"] = cust_agg["min_order_spend"].round(2)
    cust_agg["avg_units_per_order"] = cust_agg["avg_units_per_order"].round(1)

    return cust_agg
