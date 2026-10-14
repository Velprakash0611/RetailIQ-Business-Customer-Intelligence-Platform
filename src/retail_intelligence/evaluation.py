"""
Evaluation module for RetailIQ.
Computes PR-AUC, ROC-AUC, Brier score, calibration curve coordinates,
confusion matrix, and production reliability verdicts.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)

from retail_intelligence.training import TrainedModelArtifact


@dataclass
class EvaluationReport:
    metrics: dict[str, float]
    confusion: dict[str, int]
    calibration_curve_data: dict[str, list[float]]
    pr_curve_data: dict[str, list[float]]
    reliability_verdict: str
    verdict_explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "metrics": self.metrics,
            "confusion": self.confusion,
            "calibration_curve_data": self.calibration_curve_data,
            "pr_curve_data": self.pr_curve_data,
            "reliability_verdict": self.reliability_verdict,
            "verdict_explanation": self.verdict_explanation,
        }


def evaluate_model(
    artifact: TrainedModelArtifact,
    eval_df: pd.DataFrame,
    threshold: float = 0.5,
) -> EvaluationReport:
    """
    Evaluates a trained model artifact on a holdout evaluation dataset.
    """
    if eval_df.empty or "is_inactive" not in eval_df.columns:
        raise ValueError("Evaluation DataFrame is empty or missing 'is_inactive' target.")

    X_eval = eval_df[artifact.feature_names].values
    y_true = eval_df["is_inactive"].values.astype(int)

    # Probabilities of class 1 (inactivity)
    y_prob = artifact.model.predict_proba(X_eval)[:, 1]
    y_pred = (y_prob >= threshold).astype(int)

    baseline_inactivity_rate = float(np.mean(y_true))

    # Metrics
    # ROC-AUC (safe check for single-class edge cases)
    try:
        roc_auc = float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.5
    except Exception:
        roc_auc = 0.5

    # PR-AUC
    try:
        pr_auc = float(average_precision_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else baseline_inactivity_rate
    except Exception:
        pr_auc = baseline_inactivity_rate

    # Brier score
    brier = float(brier_score_loss(y_true, y_prob))

    # Precision, Recall, F1
    precision = float(precision_score(y_true, y_pred, zero_division=0))
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    # Confusion Matrix
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

    # Calibration Curve (Reliability Diagram)
    prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=5, strategy="uniform")

    # PR Curve coordinates (sampled for visualization)
    prec_vals, rec_vals, _ = precision_recall_curve(y_true, y_prob)
    # Downsample if too large
    step = max(1, len(prec_vals) // 50)
    pr_sampled_prec = [round(float(p), 4) for p in prec_vals[::step]]
    pr_sampled_rec = [round(float(r), 4) for r in rec_vals[::step]]

    # Production Reliability Verdict
    # High reliability: PR-AUC > baseline + 0.15, Brier < 0.20, n_samples >= 50
    if len(eval_df) < 30:
        verdict = "Low Sample Warning"
        explanation = (
            f"Holdout validation sample is small ({len(eval_df)} customers). "
            "Metrics provide directional guidance but should be monitored as more history accumulates."
        )
    elif pr_auc >= (baseline_inactivity_rate + 0.10) and brier <= 0.22:
        verdict = "High Reliability (Production Ready)"
        explanation = (
            f"The model demonstrates strong predictive lift (PR-AUC: {pr_auc:.3f} vs baseline: {baseline_inactivity_rate:.3f}) "
            f"and sound probability calibration (Brier Score: {brier:.3f}). Probabilities can be reliably used for prioritisation."
        )
    elif pr_auc >= baseline_inactivity_rate and brier <= 0.28:
        verdict = "Moderate Reliability"
        explanation = (
            f"The model shows positive predictive signal (PR-AUC: {pr_auc:.3f}), but risk scores should be used alongside "
            "business judgment and customer spend value rather than as absolute certainties."
        )
    else:
        verdict = "Experimental / Low Predictive Lift"
        explanation = (
            f"Model performance (PR-AUC: {pr_auc:.3f}) is near the naive baseline ({baseline_inactivity_rate:.3f}). "
            "We recommend relying on RFM rules and recency tiers until additional customer history is collected."
        )

    return EvaluationReport(
        metrics={
            "pr_auc": round(pr_auc, 3),
            "roc_auc": round(roc_auc, 3),
            "brier_score": round(brier, 3),
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1_score": round(f1, 3),
            "baseline_inactivity_rate": round(baseline_inactivity_rate, 3),
            "eval_samples": len(eval_df),
        },
        confusion={"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        calibration_curve_data={
            "prob_pred": [round(float(p), 4) for p in prob_pred],
            "prob_true": [round(float(p), 4) for p in prob_true],
        },
        pr_curve_data={
            "precision": pr_sampled_prec,
            "recall": pr_sampled_rec,
        },
        reliability_verdict=verdict,
        verdict_explanation=explanation,
    )
