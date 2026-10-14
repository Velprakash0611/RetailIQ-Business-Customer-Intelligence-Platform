"""
Prediction & Model Evaluation view for Dash Mantine UI.
Configures business-specific inactivity model training, displays holdout
evaluation metrics (PR-AUC, ROC-AUC, Brier score), calibration curves,
and feature importances.
"""

import dash_mantine_components as dmc
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html
from dash_iconify import DashIconify

from retail_intelligence.dash_state import state
from retail_intelligence.labels import check_prediction_eligibility
from retail_intelligence.training import FEATURE_DISPLAY_NAMES


def build_calibration_curve_figure(calib_data: dict[str, list[float]]) -> go.Figure:
    """Builds calibration curve (reliability diagram) with ideal diagonal reference."""
    fig = go.Figure()

    # Ideal 45-degree calibration line
    fig.add_trace(
        go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode="lines",
            name="Perfect Calibration",
            line=dict(color="#94A3B8", dash="dash", width=1.5),
            hoverinfo="none",
        )
    )

    if calib_data and calib_data.get("prob_pred"):
        fig.add_trace(
            go.Scatter(
                x=calib_data["prob_pred"],
                y=calib_data["prob_true"],
                mode="lines+markers",
                name="Calibrated Model",
                line=dict(color="#2563EB", width=2.5),
                marker=dict(size=7, color="#2563EB"),
                hovertemplate="Mean Predicted: %{x:.2f}<br>Fraction of Positives: %{y:.2f}<extra></extra>",
            )
        )

    fig.update_layout(
        template="plotly_white",
        height=280,
        margin=dict(l=45, r=20, t=15, b=35),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Mean Predicted Inactivity Probability", range=[0, 1], showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(title="Observed Positive Fraction", range=[0, 1], showgrid=True, gridcolor="#E2E8F0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def build_pr_curve_figure(pr_data: dict[str, list[float]], baseline: float = 0.5) -> go.Figure:
    """Builds Precision-Recall curve with naive baseline threshold."""
    fig = go.Figure()

    # Naive baseline horizontal line
    fig.add_trace(
        go.Scatter(
            x=[0, 1],
            y=[baseline, baseline],
            mode="lines",
            name=f"Naive Baseline ({baseline:.2f})",
            line=dict(color="#EF4444", dash="dash", width=1.5),
            hoverinfo="none",
        )
    )

    if pr_data and pr_data.get("precision"):
        fig.add_trace(
            go.Scatter(
                x=pr_data["recall"],
                y=pr_data["precision"],
                mode="lines",
                name="Precision-Recall",
                line=dict(color="#0D9488", width=2.5),
                hovertemplate="Recall: %{x:.2f}<br>Precision: %{y:.2f}<extra></extra>",
            )
        )

    fig.update_layout(
        template="plotly_white",
        height=280,
        margin=dict(l=45, r=20, t=15, b=35),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Recall", range=[0, 1], showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(title="Precision", range=[0, 1.05], showgrid=True, gridcolor="#E2E8F0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def build_feature_importance_figure(importances: dict[str, float]) -> go.Figure:
    """Builds horizontal bar chart for top predictive feature weights."""
    if not importances:
        fig = go.Figure()
        fig.update_layout(template="plotly_white", height=280, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig

    # Sort descending and take top 8
    sorted_items = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:8]
    # Reverse for top-down display in Plotly horizontal bar
    sorted_items = sorted_items[::-1]

    names = [FEATURE_DISPLAY_NAMES.get(k, k) for k, _ in sorted_items]
    vals = [v for _, v in sorted_items]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=names,
            x=vals,
            orientation="h",
            marker=dict(color="#6366F1", opacity=0.88),
            hovertemplate="<b>%{y}</b><br>Weight: %{x:.3f}<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_white",
        height=280,
        margin=dict(l=180, r=20, t=10, b=35),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Relative Importance Weight", showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(title="", tickfont=dict(size=11)),
    )
    return fig


def build_prediction_view() -> html.Div:
    """Renders the prediction modeling and evaluation tab."""
    sales_df = state.clean_sales_df if state.clean_sales_df is not None else pd.DataFrame()
    eligibility = check_prediction_eligibility(sales_df, outcome_days=90)

    model_art = state.model_artifact
    eval_rep = state.eval_report

    # Eligibility Alert
    if eligibility["is_eligible"]:
        elig_alert = dmc.Alert(
            title="Dataset Eligible for Business-Specific Model Training",
            color="teal",
            variant="light",
            radius="md",
            mb="lg",
            icon=DashIconify(icon="tabler:circle-check", width=22),
            children=(
                f"Historical depth: {eligibility.get('total_span_days', 0)} days with {eligibility.get('registered_customers', 0)} registered customers. "
                f"Valid historical cutoff range: {eligibility.get('earliest_valid_cutoff', 'N/A')} to {eligibility.get('latest_valid_cutoff', 'N/A')}."
            ),
        )
    else:
        elig_alert = dmc.Alert(
            title="Insufficient Historical Depth for Dedicated Model Training",
            color="orange",
            variant="light",
            radius="md",
            mb="lg",
            icon=DashIconify(icon="tabler:alert-triangle", width=22),
            children=(
                f"Reason: {eligibility['reason']}. Minimum required is 180 days span and >= 30 registered buyers. "
                "The application will use historical recency percentiles for customer ranking."
            ),
        )

    # Metrics values
    metrics = eval_rep.metrics if eval_rep else {}
    calib_fig = build_calibration_curve_figure(eval_rep.calibration_curve_data if eval_rep else {})
    pr_fig = build_pr_curve_figure(
        eval_rep.pr_curve_data if eval_rep else {},
        baseline=metrics.get("baseline_inactivity_rate", 0.5),
    )
    imp_fig = build_feature_importance_figure(model_art.feature_importances if model_art else {})

    # Verdict styling
    verdict = eval_rep.reliability_verdict if eval_rep else "Model Not Trained"
    verdict_explanation = (
        eval_rep.verdict_explanation
        if eval_rep
        else "Click 'Train Business-Specific Model' below to train and validate on your historical cutoffs."
    )
    verdict_color = "teal" if "High" in verdict else ("orange" if "Moderate" in verdict else "gray")

    return html.Div(
        children=[
            elig_alert,
            # Training Configuration & Controls
            dmc.Paper(
                p="lg",
                radius="md",
                withBorder=True,
                shadow="xs",
                mb="lg",
                children=[
                    dmc.Group(
                        justify="space-between",
                        align="center",
                        mb="md",
                        children=[
                            html.Div([
                                dmc.Title("Model Training Configuration", order=4),
                                dmc.Text("Trains on historical cutoffs and tests against holdout validation observation windows", size="xs", c="dimmed"),
                            ]),
                            dmc.Button(
                                "Train Business-Specific Model",
                                id="btn-train-model",
                                variant="filled",
                                color="blue",
                                leftSection=DashIconify(icon="tabler:brain", width=18),
                            ),
                        ],
                    ),
                    dmc.SimpleGrid(
                        cols={"base": 1, "sm": 2, "md": 3},
                        spacing="md",
                        children=[
                            dmc.Select(
                                id="pred-model-type-select",
                                label="Algorithm Architecture",
                                description="Underlying classifier pipeline",
                                data=[
                                    {"label": "HistGradientBoosting (Recommended)", "value": "gradient_boosting"},
                                    {"label": "Random Forest (100 Trees)", "value": "random_forest"},
                                    {"label": "Logistic Regression (L2 Regularized)", "value": "logistic_regression"},
                                ],
                                value="gradient_boosting",
                                radius="sm",
                            ),
                            dmc.Select(
                                id="pred-calibrate-select",
                                label="Probability Calibration",
                                description="Aligns predicted outputs with real frequencies",
                                data=[
                                    {"label": "CalibratedClassifierCV (Sigmoid / 3-Fold)", "value": "true"},
                                    {"label": "Uncalibrated Raw Outputs", "value": "false"},
                                ],
                                value="true",
                                radius="sm",
                            ),
                            dmc.Paper(
                                p="sm",
                                withBorder=True,
                                radius="sm",
                                children=[
                                    dmc.Text("Current Model Status", size="xs", c="dimmed"),
                                    dmc.Badge(
                                        "Trained & Calibrated" if model_art and model_art.is_calibrated else ("Heuristic Mode" if not model_art else "Trained (Uncalibrated)"),
                                        color="teal" if model_art else "gray",
                                        variant="light",
                                        size="lg",
                                        radius="sm",
                                        mt=4,
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Div(id="train-feedback-container", style={"marginTop": "10px"}),
                ],
            ),
            # Evaluation Verdict & Key Metrics Cards
            dmc.Paper(
                p="lg",
                radius="md",
                withBorder=True,
                shadow="xs",
                mb="lg",
                children=[
                    dmc.Group(
                        justify="space-between",
                        align="center",
                        mb="sm",
                        children=[
                            dmc.Title("Holdout Evaluation & Production Reliability", order=4),
                            dmc.Badge(verdict, color=verdict_color, variant="filled", size="lg", radius="sm"),
                        ],
                    ),
                    dmc.Text(verdict_explanation, size="sm", c="dimmed", mb="md"),
                    dmc.SimpleGrid(
                        cols={"base": 1, "sm": 2, "md": 4},
                        spacing="md",
                        children=[
                            dmc.Paper(
                                p="md",
                                withBorder=True,
                                radius="sm",
                                children=[
                                    dmc.Text("PR-AUC vs Baseline", size="xs", c="dimmed"),
                                    dmc.Title(f"{metrics.get('pr_auc', 0.0):.3f}", order=3, c="blue"),
                                    dmc.Text(f"Baseline: {metrics.get('baseline_inactivity_rate', 0.0):.3f}", size="xs", c="dimmed", mt=2),
                                ],
                            ),
                            dmc.Paper(
                                p="md",
                                withBorder=True,
                                radius="sm",
                                children=[
                                    dmc.Text("ROC-AUC Score", size="xs", c="dimmed"),
                                    dmc.Title(f"{metrics.get('roc_auc', 0.0):.3f}", order=3, c="teal"),
                                    dmc.Text("Discrimination power", size="xs", c="dimmed", mt=2),
                                ],
                            ),
                            dmc.Paper(
                                p="md",
                                withBorder=True,
                                radius="sm",
                                children=[
                                    dmc.Text("Brier Score Loss", size="xs", c="dimmed"),
                                    dmc.Title(f"{metrics.get('brier_score', 0.0):.3f}", order=3, c="indigo"),
                                    dmc.Text("Calibration error (lower is better)", size="xs", c="dimmed", mt=2),
                                ],
                            ),
                            dmc.Paper(
                                p="md",
                                withBorder=True,
                                radius="sm",
                                children=[
                                    dmc.Text("F1 Score / Precision", size="xs", c="dimmed"),
                                    dmc.Title(f"{metrics.get('f1_score', 0.0):.3f}", order=3),
                                    dmc.Text(f"Prec: {metrics.get('precision', 0.0):.2f} | Rec: {metrics.get('recall', 0.0):.2f}", size="xs", c="dimmed", mt=2),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            # Diagnostic Visualizations: Calibration & PR Curves
            dmc.SimpleGrid(
                cols={"base": 1, "md": 2},
                spacing="lg",
                mb="lg",
                children=[
                    dmc.Paper(
                        p="lg",
                        radius="md",
                        withBorder=True,
                        shadow="xs",
                        children=[
                            dmc.Title("Calibration Reliability Diagram", order=4, mb="xs"),
                            dmc.Text("Predicted inactivity probability vs observed empirical event rate", size="xs", c="dimmed", mb="md"),
                            dcc.Graph(
                                id="pred-calib-chart",
                                figure=calib_fig,
                                config={"displayModeBar": False, "responsive": True},
                            ),
                        ],
                    ),
                    dmc.Paper(
                        p="lg",
                        radius="md",
                        withBorder=True,
                        shadow="xs",
                        children=[
                            dmc.Title("Precision-Recall Tradeoff Curve", order=4, mb="xs"),
                            dmc.Text("Classifier precision across recall spectrum relative to naive rate", size="xs", c="dimmed", mb="md"),
                            dcc.Graph(
                                id="pred-pr-chart",
                                figure=pr_fig,
                                config={"displayModeBar": False, "responsive": True},
                            ),
                        ],
                    ),
                ],
            ),
            # Top Predictive Features
            dmc.Paper(
                p="lg",
                radius="md",
                withBorder=True,
                shadow="xs",
                children=[
                    dmc.Title("Key Predictive Feature Weights", order=4, mb="xs"),
                    dmc.Text("Relative impact of historical behavioral signals on predicting 90-day inactivity", size="xs", c="dimmed", mb="md"),
                    dcc.Graph(
                        id="pred-feature-chart",
                        figure=imp_fig,
                        config={"displayModeBar": False, "responsive": True},
                    ),
                ],
            ),
        ]
    )
