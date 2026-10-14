"""
Dash state controller for RetailIQ.
Manages in-memory cache of transactions, pre-calculated features, trained models,
and prioritisation queues for high-performance reactive callbacks.
"""

import os
import pickle
from typing import Any, Dict, Optional

import pandas as pd

from retail_intelligence.cleaning import clean_and_standardize_data
from retail_intelligence.evaluation import evaluate_model
from retail_intelligence.labels import generate_training_and_validation_datasets
from retail_intelligence.prediction import predict_current_customer_inactivity
from retail_intelligence.prioritisation import build_customer_priority_list
from retail_intelligence.schema_mapping import detect_column_mappings
from retail_intelligence.training import TrainedModelArtifact, train_inactivity_model

BENCHMARK_CSV = "data/raw/online_retail_sample.csv"
SAVED_MODEL_PATH = "models/inactivity_model_latest.pkl"


class DashStateController:
    """Singleton-style controller for Dash runtime data."""

    def __init__(self, auto_load_benchmark: bool = False):
        self.filename: Optional[str] = None
        self.raw_df: Optional[pd.DataFrame] = None
        self.mapping: Dict[str, str] = {}
        self.clean_sales_df: Optional[pd.DataFrame] = None
        self.returns_df: Optional[pd.DataFrame] = None
        self.rejected_df: Optional[pd.DataFrame] = None
        self.cleaning_summary: Optional[Dict[str, Any]] = None
        self.model_artifact: Optional[TrainedModelArtifact] = None
        self.eval_report: Optional[Any] = None
        self.predictions_df: Optional[pd.DataFrame] = None
        self.prioritised_df: Optional[pd.DataFrame] = None
        self.risk_threshold: float = 0.50
        self.value_cutoff_pct: float = 70.0
        self.risk_weight: float = 0.60

        if auto_load_benchmark:
            self.load_benchmark()

    def load_benchmark(self):
        """Loads benchmark dataset and pre-computes pipeline."""
        if not os.path.exists(BENCHMARK_CSV):
            from scripts.build_benchmark import generate_benchmark_dataset
            generate_benchmark_dataset()

        df = pd.read_csv(BENCHMARK_CSV)
        self.raw_df = df
        self.filename = "online_retail_sample.csv (Benchmark)"
        self.mapping, _ = detect_column_mappings(list(df.columns))

        clean_sales, returns, rejected, summary = clean_and_standardize_data(df, self.mapping)
        self.clean_sales_df = clean_sales
        self.returns_df = returns
        self.rejected_df = rejected
        self.cleaning_summary = summary

        # Load saved model if available
        if os.path.exists(SAVED_MODEL_PATH):
            try:
                with open(SAVED_MODEL_PATH, "rb") as f:
                    self.model_artifact = pickle.load(f)
            except Exception:
                self.model_artifact = None

        if self.model_artifact is not None:
            _, val_df, _ = generate_training_and_validation_datasets(clean_sales, returns, outcome_days=90)
            if val_df is not None and not val_df.empty:
                self.eval_report = evaluate_model(self.model_artifact, val_df)

        self.refresh_predictions_and_priorities()

    def set_uploaded_dataset(self, filename: str, df: pd.DataFrame, mapping: Dict[str, str]):
        """Sets newly uploaded dataset, cleans, and recalculates."""
        self.filename = filename
        self.raw_df = df
        self.mapping = mapping

        clean_sales, returns, rejected, summary = clean_and_standardize_data(df, mapping)
        self.clean_sales_df = clean_sales
        self.returns_df = returns
        self.rejected_df = rejected
        self.cleaning_summary = summary
        self.model_artifact = None
        self.eval_report = None

        self.refresh_predictions_and_priorities()

    def train_model(self, model_type: str = "gradient_boosting", calibrate: bool = True):
        """Trains business-specific model on current dataset."""
        if self.clean_sales_df is None or self.clean_sales_df.empty:
            return None, "No data available"

        train_df, val_df, info = generate_training_and_validation_datasets(
            self.clean_sales_df, self.returns_df, outcome_days=90
        )
        if train_df is None or train_df.empty:
            return None, info.get("reason", "Ineligible for model training")

        artifact = train_inactivity_model(train_df, val_df, model_type=model_type, calibrate=calibrate)
        eval_rep = evaluate_model(artifact, val_df)
        self.model_artifact = artifact
        self.eval_report = eval_rep

        # Persist model
        os.makedirs(os.path.dirname(SAVED_MODEL_PATH), exist_ok=True)
        with open(SAVED_MODEL_PATH, "wb") as f:
            pickle.dump(artifact, f)

        self.refresh_predictions_and_priorities()
        return eval_rep, "Model trained successfully"

    def refresh_predictions_and_priorities(self):
        """Recalculates predictions and priority queue."""
        if self.clean_sales_df is None or self.clean_sales_df.empty:
            return

        preds = predict_current_customer_inactivity(
            sales_df=self.clean_sales_df,
            returns_df=self.returns_df,
            model_artifact=self.model_artifact,
            risk_threshold_high=0.70,
            risk_threshold_med=0.40,
        )
        self.predictions_df = preds

        prioritised = build_customer_priority_list(
            predictions_df=preds,
            risk_threshold=self.risk_threshold,
            value_percentile_cutoff=self.value_cutoff_pct,
            risk_weight=self.risk_weight,
        )
        self.prioritised_df = prioritised


# Global state instance
state = DashStateController()
