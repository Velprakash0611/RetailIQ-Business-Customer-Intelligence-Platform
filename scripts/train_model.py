"""
CLI Model training script for RetailIQ.
Processes raw transaction dataset, validates, cleans, creates point-in-time training sets,
fits calibrated scikit-learn models, evaluates on holdout cutoff, and saves model artifact.
"""

import argparse
import os
import pickle
import sys

# Ensure src directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from retail_intelligence.cleaning import clean_and_standardize_data
from retail_intelligence.evaluation import evaluate_model
from retail_intelligence.ingestion import load_full_dataframe
from retail_intelligence.labels import generate_training_and_validation_datasets
from retail_intelligence.schema_mapping import detect_column_mappings, validate_mapping
from retail_intelligence.training import train_inactivity_model


def main():
    parser = argparse.ArgumentParser(description="Train customer inactivity prediction model")
    parser.add_argument("--data", default="data/raw/online_retail_sample.csv", help="Path to transaction file")
    parser.add_argument("--model-type", default="gradient_boosting", choices=["gradient_boosting", "logistic_regression", "random_forest"])
    parser.add_argument("--output-model", default="models/inactivity_model_latest.pkl", help="Output model path")
    args = parser.parse_args()

    print(f"Loading data from {args.data}...")
    df_raw = load_full_dataframe(args.data, os.path.basename(args.data))
    print(f"Loaded {len(df_raw)} records.")

    # Detect schema
    mapping, _ = detect_column_mappings(list(df_raw.columns))
    is_valid, errs = validate_mapping(mapping)
    if not is_valid:
        print(f"Schema mapping error: {errs}")
        sys.exit(1)

    # Clean data
    clean_sales, returns, rejected, summary = clean_and_standardize_data(df_raw, mapping)
    print(f"Cleaned {len(clean_sales)} positive sales, {len(returns)} returns, {len(rejected)} rejected.")

    # Create datasets
    train_data, val_data, info = generate_training_and_validation_datasets(clean_sales, returns)
    if not info.get("is_eligible", False):
        print(f"Prediction ineligible: {info.get('reason')}")
        sys.exit(1)

    print(f"Training samples: {len(train_data)}, Validation samples: {len(val_data)}")

    # Train
    artifact = train_inactivity_model(train_data, val_data, model_type=args.model_type, calibrate=True)
    print(f"Model trained. Calibrated: {artifact.is_calibrated}")

    # Evaluate
    eval_rep = evaluate_model(artifact, val_data)
    print("\n--- Evaluation Results ---")
    for k, v in eval_rep.metrics.items():
        print(f"  {k}: {v}")
    print(f"Reliability: {eval_rep.reliability_verdict}")
    print(f"{eval_rep.verdict_explanation}\n")

    # Save
    os.makedirs(os.path.dirname(args.output_model), exist_ok=True)
    with open(args.output_model, "wb") as f:
        pickle.dump(artifact, f)
    print(f"Saved model artifact to {args.output_model}")


if __name__ == "__main__":
    main()

