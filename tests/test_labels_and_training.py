"""Unit tests for labels creation, eligibility checking, model training, and evaluation."""

import numpy as np
import pandas as pd

from retail_intelligence.evaluation import evaluate_model
from retail_intelligence.labels import create_labelled_dataset_at_cutoff
from retail_intelligence.training import train_inactivity_model


def test_labels_inactivity_definition():
    sales_df = pd.DataFrame({
        "date": pd.to_datetime([
            "2023-01-01",  # C1 initial purchase
            "2023-01-10",  # C2 initial purchase
            "2023-04-15",  # C1 purchases in outcome window (Apr 1 - Jul 1)
        ]),
        "invoice_id": ["I1", "I2", "I3"],
        "customer_id": ["C1", "C2", "C1"],
        "is_guest": [False, False, False],
        "product_id": ["P1", "P1", "P2"],
        "quantity": [1, 2, 1],
        "unit_price": [10.0, 10.0, 20.0],
        "total_amount": [10.0, 20.0, 20.0],
    })

    cutoff = pd.Timestamp("2023-04-01")
    labelled = create_labelled_dataset_at_cutoff(sales_df, cutoff_date=cutoff, outcome_days=90)

    assert len(labelled) == 2
    c1_row = labelled[labelled["customer_id"] == "C1"].iloc[0]
    c2_row = labelled[labelled["customer_id"] == "C2"].iloc[0]

    # C1 purchased on April 15 (inside outcome window) -> active (0)
    assert c1_row["is_inactive"] == 0
    # C2 did not purchase in outcome window -> inactive (1)
    assert c2_row["is_inactive"] == 1


def test_model_training_and_evaluation():
    # Build a synthetic sample of 60 customers with features and targets
    np.random.seed(42)
    n = 60
    train_df = pd.DataFrame({
        "recency_days": np.random.uniform(5, 120, n),
        "frequency": np.random.randint(1, 15, n),
        "total_spend": np.random.uniform(50, 2000, n),
        "avg_order_value": np.random.uniform(20, 200, n),
        "total_units": np.random.randint(2, 50, n),
        "avg_units_per_order": np.random.uniform(1, 10, n),
        "distinct_products": np.random.randint(1, 20, n),
        "tenure_days": np.random.uniform(30, 300, n),
        "avg_days_between_orders": np.random.uniform(5, 60, n),
        "orders_last_30d": np.random.randint(0, 4, n),
        "spend_last_30d": np.random.uniform(0, 300, n),
        "orders_last_90d": np.random.randint(0, 8, n),
        "spend_last_90d": np.random.uniform(0, 800, n),
        "spend_velocity_30_90": np.random.uniform(0, 3, n),
        "return_count": np.random.randint(0, 3, n),
        "return_spend": np.random.uniform(0, 50, n),
        "is_inactive": np.random.choice([0, 1], size=n, p=[0.4, 0.6]),
    })

    val_df = train_df.copy()

    artifact = train_inactivity_model(train_df, val_df, model_type="logistic_regression", calibrate=True)
    assert artifact.is_calibrated is True
    assert artifact.model is not None

    eval_report = evaluate_model(artifact, val_df)
    assert "pr_auc" in eval_report.metrics
    assert "brier_score" in eval_report.metrics
    assert eval_report.reliability_verdict is not None
