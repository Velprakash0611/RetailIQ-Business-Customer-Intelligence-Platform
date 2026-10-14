"""
Reporting module for RetailIQ.
Compiles audit trails, data quality summaries, model governance metadata,
and downloadable markdown/JSON reports.
"""

from datetime import datetime
from typing import Any


def build_audit_report(
    session_id: str,
    filename: str,
    validation_stats: dict[str, Any],
    cleaning_summary: dict[str, Any],
    model_eval_report: dict[str, Any] | None = None,
    priority_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Constructs a comprehensive audit log report for the session run.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = {
        "report_generated_at": now_str,
        "session_id": session_id,
        "source_file": filename,
        "data_quality_scorecard": {
            "total_raw_rows": cleaning_summary.get("total_raw_rows", 0),
            "clean_sales_rows": cleaning_summary.get("clean_sales_rows", 0),
            "returns_rows": cleaning_summary.get("returns_rows", 0),
            "rejected_rows": cleaning_summary.get("rejected_rows", 0),
            "duplicates_removed": cleaning_summary.get("duplicates_removed", 0),
            "guest_rows": cleaning_summary.get("guest_rows", 0),
            "registered_rows": cleaning_summary.get("registered_rows", 0),
            "gross_revenue": cleaning_summary.get("total_gross_revenue", 0.0),
            "returns_revenue": cleaning_summary.get("total_returns_revenue", 0.0),
            "net_revenue": cleaning_summary.get("net_revenue", 0.0),
            "historical_date_range": f"{cleaning_summary.get('date_min')} to {cleaning_summary.get('date_max')}",
        },
        "model_governance": {
            "model_trained": model_eval_report is not None,
            "metrics": model_eval_report.get("metrics") if model_eval_report else None,
            "reliability_verdict": model_eval_report.get("reliability_verdict") if model_eval_report else "No model evaluated",
            "verdict_explanation": model_eval_report.get("verdict_explanation") if model_eval_report else "Prediction model not trained.",
            "limitations_caveats": [
                "Inactivity predictions estimate non-purchase probability over a 90-day window based on historical behavioral patterns.",
                "Predictions do not account for unobserved macro events, competitor campaigns, or supply disruptions.",
                "Prioritisation ranking combines risk and value; it does not measure marketing campaign lift or elasticity.",
                "Data quality depends on proper invoice cancellation tagging and customer identity tracking.",
            ],
        },
    }

    return report


def export_report_markdown(audit_report: dict[str, Any]) -> str:
    """
    Formats the audit report into clean, readable GitHub-style Markdown.
    """
    dq = audit_report["data_quality_scorecard"]
    gov = audit_report["model_governance"]

    md = f"""# RetailIQ — Data & Model Governance Report

**Generated:** {audit_report['report_generated_at']}  
**Source Dataset:** `{audit_report['source_file']}`  
**Session ID:** `{audit_report['session_id']}`  

---

## 1. Data Processing & Quality Scorecard

| Metric | Value |
|---|---|
| Total Raw Uploaded Records | {dq.get('total_raw_rows', 0):,} |
| Clean Sales Records | {dq.get('clean_sales_rows', 0):,} |
| Returns & Cancellations | {dq.get('returns_rows', 0):,} |
| Excluded / Rejected Records | {dq.get('rejected_rows', 0):,} |
| Exact Duplicates Removed | {dq.get('duplicates_removed', 0):,} |
| Registered Customer Transactions | {dq.get('registered_rows', 0):,} |
| Guest / Unregistered Transactions | {dq.get('guest_rows', 0):,} |
| Historical Date Range | {dq.get('historical_date_range', 'N/A')} |
| Gross Recorded Sales | ${dq.get('gross_revenue', 0.0):,.2f} |
| Returns & Refunds | ${dq.get('returns_revenue', 0.0):,.2f} |
| Net Revenue | ${dq.get('net_revenue', 0.0):,.2f} |

---

## 2. Predictive Model Governance & Reliability

**Status:** {'Trained & Evaluated' if gov['model_trained'] else 'Not Trained (Heuristic Active)'}  
**Reliability Verdict:** **{gov['reliability_verdict']}**  
**Assessment:** {gov['verdict_explanation']}  

"""
    if gov.get("metrics"):
        m = gov["metrics"]
        md += f"""### Evaluation Metrics (Holdout Validation Period)
- **PR-AUC (Precision-Recall Area):** {m.get('pr_auc', 'N/A')} (Baseline: {m.get('baseline_inactivity_rate', 'N/A')})
- **ROC-AUC:** {m.get('roc_auc', 'N/A')}
- **Brier Score (Calibration Error):** {m.get('brier_score', 'N/A')}
- **Precision:** {m.get('precision', 'N/A')}
- **Recall:** {m.get('recall', 'N/A')}
- **F1 Score:** {m.get('f1_score', 'N/A')}
- **Holdout Validation Customers:** {m.get('eval_samples', 'N/A')}

"""

    md += """## 3. Assumptions & Caveats
1. **Target Definition:** Inactivity is defined as zero qualifying purchases during the subsequent 90 days.
2. **Leakage Prevention:** Features are computed strictly using transactions recorded on or before each historical cutoff date.
3. **Multi-retailer Generalization:** Prediction models are trained business-specifically on this uploaded dataset's historical behavior.
4. **Actionable Ranking:** Priority rankings blend predicted risk with historical customer monetary value to optimize contact queues.
"""
    return md
