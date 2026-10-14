"""
Training module for RetailIQ.
Trains, tunes, and calibrates customer inactivity models using scikit-learn.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS = [
    "recency_days",
    "frequency",
    "total_spend",
    "avg_order_value",
    "total_units",
    "avg_units_per_order",
    "distinct_products",
    "tenure_days",
    "avg_days_between_orders",
    "orders_last_30d",
    "spend_last_30d",
    "orders_last_90d",
    "spend_last_90d",
    "spend_velocity_30_90",
    "return_count",
    "return_spend",
]

FEATURE_DISPLAY_NAMES = {
    "recency_days": "Days Since Last Purchase",
    "frequency": "Total Lifetime Orders",
    "total_spend": "Total Lifetime Spend",
    "avg_order_value": "Average Order Value",
    "total_units": "Total Items Purchased",
    "avg_units_per_order": "Avg Items Per Order",
    "distinct_products": "Distinct Products Bought",
    "tenure_days": "Customer Age (Tenure Days)",
    "avg_days_between_orders": "Avg Inter-Purchase Days",
    "orders_last_30d": "Orders in Trailing 30 Days",
    "spend_last_30d": "Spend in Trailing 30 Days",
    "orders_last_90d": "Orders in Trailing 90 Days",
    "spend_last_90d": "Spend in Trailing 90 Days",
    "spend_velocity_30_90": "Spend Momentum (30d vs 90d)",
    "return_count": "Lifetime Returned Items",
    "return_spend": "Lifetime Return Value",
}


@dataclass
class TrainedModelArtifact:
    model: Any
    model_type: str
    feature_names: list[str]
    is_calibrated: bool
    feature_importances: dict[str, float]
    training_summary: dict[str, Any]


def train_inactivity_model(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame | None = None,
    model_type: str = "gradient_boosting",  # "gradient_boosting", "logistic_regression", "random_forest"
    calibrate: bool = True,
) -> TrainedModelArtifact:
    """
    Trains an inactivity prediction model with feature preprocessing and probability calibration.
    """
    # Verify required feature columns
    available_features = [f for f in FEATURE_COLUMNS if f in train_df.columns]
    if len(available_features) < 3:
        raise ValueError(f"Insufficient feature columns in training data: {available_features}")

    X_train = train_df[available_features].values
    y_train = train_df["is_inactive"].values.astype(int)

    # Base estimator selection
    if model_type == "logistic_regression":
        base_estimator = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)),
        ])
    elif model_type == "random_forest":
        base_estimator = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("classifier", RandomForestClassifier(
                n_estimators=100, max_depth=6, min_samples_leaf=3, class_weight="balanced", random_state=42
            )),
        ])
    else:  # default "gradient_boosting"
        base_estimator = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("classifier", HistGradientBoostingClassifier(
                max_iter=100, max_depth=5, min_samples_leaf=5, class_weight="balanced", random_state=42
            )),
        ])

    # Probability calibration using modern scikit-learn cross-validation
    if calibrate:
        # Calibrate using internal 3-fold cross validation on training data
        calibrated_model = CalibratedClassifierCV(estimator=base_estimator, method="sigmoid", cv=3)
        calibrated_model.fit(X_train, y_train)
        fitted_model = calibrated_model
        is_calibrated = True
    else:
        base_estimator.fit(X_train, y_train)
        fitted_model = base_estimator
        is_calibrated = False

    # Extract feature importances
    feature_importances: dict[str, float] = {}
    try:
        # Check underlying model inside pipeline or calibration wrapper
        underlying = base_estimator.named_steps.get("classifier")
        if hasattr(underlying, "feature_importances_"):
            raw_imp = underlying.feature_importances_
            feature_importances = {feat: float(raw_imp[i]) for i, feat in enumerate(available_features)}
        elif hasattr(underlying, "coef_"):
            raw_coef = np.abs(underlying.coef_[0])
            sum_c = float(np.sum(raw_coef)) or 1.0
            feature_importances = {feat: float(raw_coef[i] / sum_c) for i, feat in enumerate(available_features)}
        else:
            feature_importances = {feat: 1.0 / len(available_features) for feat in available_features}
    except Exception:
        feature_importances = {feat: 1.0 / len(available_features) for feat in available_features}

    # Normalize importances
    total_imp = sum(feature_importances.values())
    if total_imp > 0:
        feature_importances = {k: round(v / total_imp, 4) for k, v in feature_importances.items()}

    summary = {
        "model_type": model_type,
        "n_train_samples": len(train_df),
        "n_features": len(available_features),
        "inactivity_baseline_rate": round(float(np.mean(y_train)) * 100.0, 1),
        "is_calibrated": is_calibrated,
    }

    return TrainedModelArtifact(
        model=fitted_model,
        model_type=model_type,
        feature_names=available_features,
        is_calibrated=is_calibrated,
        feature_importances=feature_importances,
        training_summary=summary,
    )
