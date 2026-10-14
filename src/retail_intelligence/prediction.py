"""
Prediction module for RetailIQ.
Generates point-in-time inference for current active customers as of the latest transaction date.
Includes fallback heuristic risk scoring if predictive ML model is unavailable.
"""


import numpy as np
import pandas as pd

from retail_intelligence.customer_features import compute_customer_features
from retail_intelligence.training import TrainedModelArtifact


def predict_current_customer_inactivity(
    sales_df: pd.DataFrame,
    returns_df: pd.DataFrame | None = None,
    model_artifact: TrainedModelArtifact | None = None,
    risk_threshold_high: float = 0.70,
    risk_threshold_med: float = 0.40,
) -> pd.DataFrame:
    """
    Scores current customers as of the dataset's latest transaction date.
    Returns customer DataFrame with inactivity probability and risk tier.
    """
    reg_sales = sales_df[~sales_df["is_guest"]]
    if reg_sales.empty:
        return pd.DataFrame()

    latest_date = reg_sales["date"].max()

    # Compute features as of the latest date
    features_df = compute_customer_features(
        sales_df=sales_df,
        cutoff_date=latest_date,
        returns_df=returns_df,
    )

    if features_df.empty:
        return pd.DataFrame()

    # If ML model is provided, run model inference
    if model_artifact is not None and model_artifact.model is not None:
        avail_cols = [c for c in model_artifact.feature_names if c in features_df.columns]
        X = features_df[avail_cols].values
        probs = model_artifact.model.predict_proba(X)[:, 1]
        features_df["inactivity_prob_90d"] = np.round(probs, 3)
        features_df["score_source"] = f"ML Model ({model_artifact.model_type})"
        features_df["is_calibrated"] = model_artifact.is_calibrated
    else:
        # Transparent rule-based fallback heuristic when ML model is not yet trained or data is too short
        # Heuristic estimates risk from recency days relative to a 90-day cycle
        # If recency > 90d, risk is high; if recency < 30d, risk is low
        rec = features_df["recency_days"]
        heuristic_prob = np.clip((rec / 120.0), 0.05, 0.98)
        features_df["inactivity_prob_90d"] = np.round(heuristic_prob, 3)
        features_df["score_source"] = "Heuristic (Recency-based Fallback)"
        features_df["is_calibrated"] = False

    # Assign Risk Tier
    def assign_tier(p: float) -> str:
        if p >= risk_threshold_high:
            return "High Risk"
        elif p >= risk_threshold_med:
            return "Medium Risk"
        else:
            return "Low Risk"

    features_df["risk_tier"] = features_df["inactivity_prob_90d"].apply(assign_tier)
    features_df["as_of_date"] = latest_date.strftime("%Y-%m-%d")

    return features_df
