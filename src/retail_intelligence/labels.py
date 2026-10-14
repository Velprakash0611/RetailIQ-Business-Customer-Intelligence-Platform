"""
Labels module for RetailIQ.
Constructs time-aware observation cutoffs, outcome evaluation windows,
and binary future-inactivity target labels (1 = inactive in next 90 days, 0 = active).
"""

from typing import Any

import pandas as pd

from retail_intelligence.customer_features import compute_customer_features


def create_labelled_dataset_at_cutoff(
    sales_df: pd.DataFrame,
    cutoff_date: pd.Timestamp,
    outcome_days: int = 90,
    returns_df: pd.DataFrame | None = None,
    min_orders_before_cutoff: int = 1,
) -> pd.DataFrame:
    """
    Builds a point-in-time dataset for a specific historical cutoff date.
    Features: calculated strictly using transactions on or before cutoff_date.
    Target (is_inactive):
        1 if customer made 0 purchases in (cutoff_date, cutoff_date + outcome_days],
        0 if customer made >= 1 purchase in (cutoff_date, cutoff_date + outcome_days].
    """
    outcome_end = cutoff_date + pd.Timedelta(days=outcome_days)

    # 1. Compute point-in-time features strictly as of cutoff_date
    features_df = compute_customer_features(
        sales_df=sales_df,
        cutoff_date=cutoff_date,
        returns_df=returns_df,
        min_orders=min_orders_before_cutoff,
    )

    if features_df.empty:
        return pd.DataFrame()

    # 2. Check future transactions in outcome window (cutoff_date, outcome_end]
    future_sales = sales_df[
        (sales_df["date"] > cutoff_date)
        & (sales_df["date"] <= outcome_end)
        & (~sales_df["is_guest"])
    ]

    active_in_future = set(future_sales["customer_id"].unique())

    # 3. Assign target: 1 = inactive (did not return), 0 = active (returned)
    features_df["is_inactive"] = features_df["customer_id"].apply(
        lambda cid: 0 if cid in active_in_future else 1
    )
    features_df["cutoff_date"] = cutoff_date
    features_df["outcome_window_days"] = outcome_days

    return features_df


def check_prediction_eligibility(
    sales_df: pd.DataFrame,
    outcome_days: int = 90,
    min_feature_days: int = 90,
    min_registered_customers: int = 30,
) -> dict[str, Any]:
    """
    Validates whether the uploaded dataset contains sufficient time depth,
    customer volume, and repeat purchase behavior for training a business-specific
    predictive model.
    """
    reg_sales = sales_df[~sales_df["is_guest"]]
    if reg_sales.empty:
        return {
            "is_eligible": False,
            "reason": "No registered customer transactions available.",
            "total_span_days": 0,
            "registered_customers": 0,
            "repeat_customers": 0,
            "possible_cutoffs": 0,
        }

    min_date = reg_sales["date"].min()
    max_date = reg_sales["date"].max()
    span_days = (max_date - min_date).days
    n_custs = int(reg_sales["customer_id"].nunique())

    # Count repeat customers
    cust_orders = reg_sales.groupby("customer_id")["invoice_id"].nunique()
    repeat_custs = int((cust_orders > 1).sum())

    required_span = min_feature_days + outcome_days

    if span_days < required_span:
        return {
            "is_eligible": False,
            "reason": (
                f"Insufficient historical time span: {span_days} days detected. "
                f"Predicting 90-day inactivity requires at least {required_span} days "
                f"({min_feature_days} days feature observation + {outcome_days} days outcome window)."
            ),
            "total_span_days": span_days,
            "required_span_days": required_span,
            "registered_customers": n_custs,
            "repeat_customers": repeat_custs,
            "possible_cutoffs": 0,
        }

    if n_custs < min_registered_customers:
        return {
            "is_eligible": False,
            "reason": (
                f"Too few unique registered customers: {n_custs} found (minimum {min_registered_customers} required) "
                "to train and evaluate a statistically reliable predictive model."
            ),
            "total_span_days": span_days,
            "required_span_days": required_span,
            "registered_customers": n_custs,
            "repeat_customers": repeat_custs,
            "possible_cutoffs": 0,
        }

    # Calculate how many historical cutoffs can be extracted
    latest_valid_cutoff = max_date - pd.Timedelta(days=outcome_days)
    earliest_valid_cutoff = min_date + pd.Timedelta(days=min_feature_days)

    return {
        "is_eligible": True,
        "reason": "Dataset meets eligibility criteria for business-specific inactivity prediction.",
        "total_span_days": span_days,
        "required_span_days": required_span,
        "registered_customers": n_custs,
        "repeat_customers": repeat_custs,
        "earliest_valid_cutoff": earliest_valid_cutoff.strftime("%Y-%m-%d"),
        "latest_valid_cutoff": latest_valid_cutoff.strftime("%Y-%m-%d"),
        "min_date": min_date.strftime("%Y-%m-%d"),
        "max_date": max_date.strftime("%Y-%m-%d"),
    }


def generate_training_and_validation_datasets(
    sales_df: pd.DataFrame,
    returns_df: pd.DataFrame | None = None,
    outcome_days: int = 90,
    min_feature_days: int = 90,
) -> tuple[pd.DataFrame | None, pd.DataFrame | None, dict[str, Any]]:
    """
    Constructs temporally partitioned training and validation datasets.
    Validation cutoff is placed exactly `outcome_days` before the latest transaction date.
    Training cutoff is placed earlier, preventing target leakage and temporal correlation.
    """
    eligibility = check_prediction_eligibility(
        sales_df, outcome_days=outcome_days, min_feature_days=min_feature_days
    )
    if not eligibility["is_eligible"]:
        return None, None, eligibility

    reg_sales = sales_df[~sales_df["is_guest"]]
    max_date = reg_sales["date"].max()
    min_date = reg_sales["date"].min()

    # Evaluation cutoff: latest date minus outcome_days
    val_cutoff = max_date - pd.Timedelta(days=outcome_days)

    # Train cutoff: placed 60 to 90 days before val_cutoff, provided it has >= min_feature_days from start
    train_cutoff = val_cutoff - pd.Timedelta(days=60)
    if train_cutoff < (min_date + pd.Timedelta(days=min_feature_days)):
        # Fall back to midpoint between earliest valid cutoff and val_cutoff
        earliest_cutoff = min_date + pd.Timedelta(days=min_feature_days)
        train_cutoff = earliest_cutoff

    train_data = create_labelled_dataset_at_cutoff(
        sales_df=sales_df,
        cutoff_date=train_cutoff,
        outcome_days=outcome_days,
        returns_df=returns_df,
    )

    val_data = create_labelled_dataset_at_cutoff(
        sales_df=sales_df,
        cutoff_date=val_cutoff,
        outcome_days=outcome_days,
        returns_df=returns_df,
    )

    info = {
        **eligibility,
        "train_cutoff": train_cutoff.strftime("%Y-%m-%d"),
        "val_cutoff": val_cutoff.strftime("%Y-%m-%d"),
        "train_samples": len(train_data) if train_data is not None else 0,
        "val_samples": len(val_data) if val_data is not None else 0,
        "train_inactivity_rate": round(float(train_data["is_inactive"].mean()) * 100.0, 1) if not train_data.empty else 0.0,
        "val_inactivity_rate": round(float(val_data["is_inactive"].mean()) * 100.0, 1) if not val_data.empty else 0.0,
    }

    return train_data, val_data, info
