"""
Metrics module for RetailIQ.
Computes executive business KPIs, sales trends, top/declining products,
country distributions, and monthly cohort retention matrices.
"""

from typing import Any

import pandas as pd


def compute_executive_kpis(
    sales_df: pd.DataFrame,
    returns_df: pd.DataFrame,
) -> dict[str, Any]:
    """
    Computes top-level store KPIs: Gross Sales, Net Sales, Total Orders,
    Unique Customers, AOV, Items Per Order, Return Rate.
    """
    if sales_df.empty:
        return {
            "gross_revenue": 0.0,
            "net_revenue": 0.0,
            "returns_revenue": 0.0,
            "total_orders": 0,
            "unique_customers": 0,
            "registered_customers": 0,
            "guest_orders": 0,
            "average_order_value": 0.0,
            "average_units_per_order": 0.0,
            "return_rate_revenue_pct": 0.0,
            "return_rate_count_pct": 0.0,
        }

    gross_revenue = float(sales_df["total_amount"].sum())
    has_returns = returns_df is not None and not returns_df.empty
    returns_revenue = float(returns_df["total_amount"].sum()) if has_returns else 0.0
    net_revenue = gross_revenue - returns_revenue

    total_orders = int(sales_df["invoice_id"].nunique())
    # Count only registered unique customers for customer KPI
    if "is_guest" in sales_df.columns:
        reg_sales = sales_df[~sales_df["is_guest"]]
        registered_customers = int(reg_sales["customer_id"].nunique())
        guest_orders = int(sales_df[sales_df["is_guest"]]["invoice_id"].nunique())
        total_customers = registered_customers + (1 if guest_orders > 0 else 0)
    else:
        registered_customers = int(sales_df["customer_id"].nunique()) if "customer_id" in sales_df.columns else 0
        guest_orders = 0
        total_customers = registered_customers

    # Order-level grouping for AOV and units per order
    order_summary = sales_df.groupby("invoice_id").agg(
        order_spend=("total_amount", "sum"),
        order_units=("quantity", "sum")
    )
    aov = float(order_summary["order_spend"].mean()) if not order_summary.empty else 0.0
    units_per_order = float(order_summary["order_units"].mean()) if not order_summary.empty else 0.0

    # Return rate
    returns_count = len(returns_df) if returns_df is not None else 0
    total_tx_count = len(sales_df) + returns_count
    return_rate_count = (returns_count / total_tx_count * 100.0) if total_tx_count > 0 else 0.0
    return_rate_rev = (returns_revenue / gross_revenue * 100.0) if gross_revenue > 0 else 0.0

    return {
        "gross_revenue": round(gross_revenue, 2),
        "returns_revenue": round(returns_revenue, 2),
        "net_revenue": round(net_revenue, 2),
        "total_orders": total_orders,
        "unique_customers": total_customers,
        "registered_customers": registered_customers,
        "guest_orders": guest_orders,
        "average_order_value": round(aov, 2),
        "average_units_per_order": round(units_per_order, 1),
        "return_rate_revenue_pct": round(return_rate_rev, 2),
        "return_rate_count_pct": round(return_rate_count, 2),
    }


def compute_sales_trends(
    sales_df: pd.DataFrame,
    freq: str = "D",  # "D" for daily, "W" for weekly, "M" / "MS" for monthly
) -> pd.DataFrame:
    """
    Computes time-series sales, orders, and active customer counts over time.
    """
    if sales_df.empty:
        return pd.DataFrame(columns=["date", "revenue", "orders", "customers", "aov"])

    df = sales_df.copy()
    # Normalize offset aliases to valid Period frequencies (e.g. MS/ME -> M, YS/YE -> Y, QS/QE -> Q)
    period_freq = freq
    if freq in ("MS", "ME", "M"):
        period_freq = "M"
    elif freq in ("YS", "YE", "Y"):
        period_freq = "Y"
    elif freq in ("QS", "QE", "Q"):
        period_freq = "Q"

    df["period"] = df["date"].dt.to_period(period_freq).dt.to_timestamp()

    trend = df.groupby("period").agg(
        revenue=("total_amount", "sum"),
        orders=("invoice_id", "nunique"),
        customers=("customer_id", "nunique"),
    ).reset_index()

    trend["aov"] = (trend["revenue"] / trend["orders"]).round(2)
    trend.rename(columns={"period": "date"}, inplace=True)
    trend["revenue"] = trend["revenue"].round(2)
    return trend.sort_values(by="date")


def compute_top_products(
    sales_df: pd.DataFrame,
    top_n: int = 10,
    by: str = "revenue",  # "revenue" or "quantity"
) -> pd.DataFrame:
    """
    Returns top N products sorted by revenue or quantity sold.
    """
    if sales_df.empty:
        return pd.DataFrame(columns=["product_id", "description", "revenue", "quantity", "orders"])

    prod_grp = sales_df.groupby(["product_id", "description"]).agg(
        revenue=("total_amount", "sum"),
        quantity=("quantity", "sum"),
        orders=("invoice_id", "nunique"),
    ).reset_index()

    prod_grp["revenue"] = prod_grp["revenue"].round(2)

    sort_col = "revenue" if by == "revenue" else "quantity"
    top_prods = prod_grp.sort_values(by=sort_col, ascending=False).head(top_n).reset_index(drop=True)
    return top_prods


def compute_declining_products(
    sales_df: pd.DataFrame,
    min_orders: int = 5,
    top_n: int = 10,
) -> pd.DataFrame:
    """
    Identifies products experiencing the largest decline in revenue between
    the recent half of the dataset and the earlier half.
    """
    if sales_df.empty:
        return pd.DataFrame(columns=["product_id", "description", "earlier_revenue", "recent_revenue", "pct_change"])

    min_date = sales_df["date"].min()
    max_date = sales_df["date"].max()
    midpoint = min_date + (max_date - min_date) / 2

    earlier = sales_df[sales_df["date"] < midpoint]
    recent = sales_df[sales_df["date"] >= midpoint]

    early_grp = earlier.groupby(["product_id", "description"]).agg(
        earlier_revenue=("total_amount", "sum"),
        earlier_orders=("invoice_id", "nunique"),
    ).reset_index()

    recent_grp = recent.groupby(["product_id", "description"]).agg(
        recent_revenue=("total_amount", "sum"),
        recent_orders=("invoice_id", "nunique"),
    ).reset_index()

    merged = pd.merge(early_grp, recent_grp, on=["product_id", "description"], how="left")
    merged["recent_revenue"] = merged["recent_revenue"].fillna(0.0)
    merged["recent_orders"] = merged["recent_orders"].fillna(0)

    # Filter to products with sufficient initial traction
    merged = merged[merged["earlier_orders"] >= min_orders]

    merged["diff"] = merged["recent_revenue"] - merged["earlier_revenue"]
    merged["pct_change"] = ((merged["diff"] / merged["earlier_revenue"]) * 100.0).round(1)

    declining = merged[merged["diff"] < 0].sort_values(by="diff", ascending=True).head(top_n)
    declining["earlier_revenue"] = declining["earlier_revenue"].round(2)
    declining["recent_revenue"] = declining["recent_revenue"].round(2)

    return declining[["product_id", "description", "earlier_revenue", "recent_revenue", "pct_change"]].reset_index(drop=True)


def compute_country_breakdown(
    sales_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Aggregates revenue, orders, and customer counts by geographic region.
    """
    if sales_df.empty or "country" not in sales_df.columns:
        return pd.DataFrame(columns=["country", "revenue", "orders", "customers", "pct_of_total_revenue"])

    geo_grp = sales_df.groupby("country").agg(
        revenue=("total_amount", "sum"),
        orders=("invoice_id", "nunique"),
        customers=("customer_id", "nunique"),
    ).reset_index()

    total_rev = geo_grp["revenue"].sum()
    geo_grp["pct_of_total_revenue"] = ((geo_grp["revenue"] / total_rev) * 100.0).round(2) if total_rev > 0 else 0.0
    geo_grp["revenue"] = geo_grp["revenue"].round(2)

    return geo_grp.sort_values(by="revenue", ascending=False).reset_index(drop=True)


def compute_cohort_retention(
    sales_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calculates monthly customer acquisition cohort size and retention percentages.
    Only considers registered customers (excludes guest checkouts).
    Returns:
        cohort_counts: DataFrame of customer count active in month index 0, 1, 2...
        cohort_retention: DataFrame of retention percentages (0-100%)
    """
    reg_df = sales_df[~sales_df["is_guest"]].copy()
    if reg_df.empty or reg_df["customer_id"].nunique() < 5:
        return pd.DataFrame(), pd.DataFrame()

    # Get order month
    reg_df["order_month"] = reg_df["date"].dt.to_period("M")

    # Cohort month is the customer's first purchase month
    reg_df["cohort_month"] = reg_df.groupby("customer_id")["order_month"].transform("min")

    cohort_data = reg_df.groupby(["cohort_month", "order_month"]).agg(
        n_customers=("customer_id", "nunique")
    ).reset_index()

    # Cohort period index: difference in months
    cohort_data["cohort_index"] = (
        (cohort_data["order_month"].dt.year - cohort_data["cohort_month"].dt.year) * 12
        + (cohort_data["order_month"].dt.month - cohort_data["cohort_month"].dt.month)
    )

    cohort_counts = cohort_data.pivot(
        index="cohort_month", columns="cohort_index", values="n_customers"
    )

    cohort_sizes = cohort_counts.iloc[:, 0]
    cohort_retention = cohort_counts.divide(cohort_sizes, axis=0) * 100.0

    cohort_counts.index = cohort_counts.index.astype(str)
    cohort_retention.index = cohort_retention.index.astype(str)

    return cohort_counts, cohort_retention.round(1)
