"""
RetailIQ — Business & Customer Intelligence Platform
Enterprise Plotly Dash + Dash Mantine Components Application.
"""

import base64
import io
import json
import os
import sys
from pathlib import Path

# Ensure src is on sys.path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import dash_mantine_components as dmc
import pandas as pd
from dash import Dash, Input, Output, State, ctx, dcc, html
from dash_iconify import DashIconify

from retail_intelligence.dash_state import state
from retail_intelligence.dash_ui.header import build_header
from retail_intelligence.dash_ui.view_customer import build_customer_view
from retail_intelligence.dash_ui.view_executive import build_executive_view, build_sales_trend_figure
from retail_intelligence.dash_ui.view_ingestion import build_ingestion_view
from retail_intelligence.dash_ui.view_landing import build_landing_dataset_status, build_landing_view
from retail_intelligence.dash_ui.view_prediction import build_prediction_view
from retail_intelligence.dash_ui.view_prioritisation import build_prioritisation_view
from retail_intelligence.dash_ui.view_product import build_product_view, build_top_products_figure
from retail_intelligence.dash_ui.view_report import build_report_view
from retail_intelligence.reporting import build_audit_report, export_report_markdown
from retail_intelligence.schema_mapping import (
    CANONICAL_REQUIRED_FIELDS,
    FIELD_LABELS,
    detect_column_mappings,
)

PROCEED_BTN_VISIBLE = {
    "display": "block",
    "height": "52px",
    "fontSize": "16px",
    "fontWeight": 600,
    "marginTop": "20px",
}
PROCEED_BTN_HIDDEN = {"display": "none"}

# Initialize Dash application with Mantine styles
app = Dash(
    __name__,
    title="RetailIQ — Business & Customer Intelligence Platform",
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server


def build_dataset_required_modal() -> dmc.Modal:
    """Modal dialog prompting the user to load a dataset before accessing dashboard."""
    return dmc.Modal(
        id="no-dataset-modal",
        opened=False,
        centered=True,
        size="md",
        radius="md",
        withCloseButton=True,
        title=dmc.Group(
            gap="xs",
            children=[
                dmc.ThemeIcon(
                    DashIconify(icon="tabler:alert-triangle", width=18),
                    color="orange",
                    variant="light",
                    size="md",
                    radius="sm",
                ),
                dmc.Text("Dataset Required", fw=700, size="sm"),
            ],
        ),
        children=dmc.Stack(
            gap="md",
            children=[
                dmc.Text(
                    "No retail transaction dataset is currently loaded. "
                    "To view executive KPIs, customer personas, and inactivity predictions, "
                    "please choose one of the options below to get started:",
                    size="sm",
                    c="dimmed",
                ),
                dmc.Paper(
                    p="md",
                    withBorder=True,
                    radius="md",
                    children=dmc.Stack(
                        gap="sm",
                        children=[
                            dmc.Group(
                                justify="space-between",
                                align="center",
                                children=[
                                    html.Div([
                                        dmc.Text("Option 1: Explore Benchmark Data", size="xs", fw=700),
                                        dmc.Text("8,910 rows • 18-month history • Pre-trained ML", size="xs", c="dimmed"),
                                    ]),
                                    dmc.Button(
                                        "Load Demo Dataset",
                                        id="btn-modal-load-benchmark",
                                        color="teal",
                                        size="xs",
                                        variant="filled",
                                        leftSection=DashIconify(icon="tabler:sparkles", width=14),
                                    ),
                                ],
                            ),
                            dmc.Divider(variant="dashed"),
                            dmc.Group(
                                justify="space-between",
                                align="center",
                                children=[
                                    html.Div([
                                        dmc.Text("Option 2: Upload Custom Dataset", size="xs", fw=700),
                                        dmc.Text("Drop CSV or Excel on the Home page", size="xs", c="dimmed"),
                                    ]),
                                    dmc.Button(
                                        "Go to Upload",
                                        id="btn-modal-upload-custom",
                                        color="blue",
                                        size="xs",
                                        variant="light",
                                        leftSection=DashIconify(icon="tabler:upload", width=14),
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )


# Root application layout
app.layout = dmc.MantineProvider(
    id="mantine-provider",
    forceColorScheme="light",
    theme={
        "primaryColor": "blue",
        "fontFamily": "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif",
    },
    children=[
        # Client-side state stores
        dcc.Store(id="state-trigger", data=0),
        dcc.Store(id="page-view-store", data="landing"),
        dcc.Store(id="color-scheme-store", data="light"),
        # Guard Modal: Prompt when accessing dashboard with no data
        build_dataset_required_modal(),
        # Global Navigation Header
        build_header(),
        # Main App Page Container
        html.Div(
            id="page-content-wrapper",
            children=dmc.Container(
                id="main-app-container",
                size="xl",
                px="md",
                py="lg",
                children=[
                    # 1. Landing View Container (Default: Visible)
                    html.Div(
                        id="landing-view-container",
                        style={"display": "block"},
                        children=build_landing_view(),
                    ),
                    # 2. Dashboard View Container (Default: Hidden until Proceed or Data Loaded)
                    html.Div(
                        id="dashboard-view-container",
                        style={"display": "none"},
                        children=[
                            dmc.Stack(
                                gap="md",
                                children=[
                                    dmc.Tabs(
                                        id="main-tabs",
                                        value="tab-executive",
                                        color="blue",
                                        variant="outline",
                                        radius="md",
                                        children=[
                                            dmc.TabsList(
                                                children=[
                                                    dmc.TabsTab(
                                                        "Executive Overview",
                                                        value="tab-executive",
                                                        leftSection=DashIconify(icon="tabler:dashboard", width=18),
                                                    ),
                                                    dmc.TabsTab(
                                                        "Data Ingestion & Quality",
                                                        value="tab-ingestion",
                                                        leftSection=DashIconify(icon="tabler:database-import", width=18),
                                                    ),
                                                    dmc.TabsTab(
                                                        "Product & Geography",
                                                        value="tab-product",
                                                        leftSection=DashIconify(icon="tabler:packages", width=18),
                                                    ),
                                                    dmc.TabsTab(
                                                        "Customer Intelligence",
                                                        value="tab-customer",
                                                        leftSection=DashIconify(icon="tabler:users", width=18),
                                                    ),
                                                    dmc.TabsTab(
                                                        "Inactivity Prediction",
                                                        value="tab-prediction",
                                                        leftSection=DashIconify(icon="tabler:brain", width=18),
                                                    ),
                                                    dmc.TabsTab(
                                                        "Prioritisation Queue",
                                                        value="tab-prioritisation",
                                                        leftSection=DashIconify(icon="tabler:list-check", width=18),
                                                    ),
                                                    dmc.TabsTab(
                                                        "Audit & Governance",
                                                        value="tab-report",
                                                        leftSection=DashIconify(icon="tabler:file-certificate", width=18),
                                                    ),
                                                ],
                                            ),
                                        ],
                                    ),
                                    # Dynamic tab view container
                                    html.Div(
                                        id="tab-content",
                                        style={"marginTop": "10px"},
                                        children=build_executive_view(),
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ),
    ],
)


# ---------------------------------------------------------------------------
# Routing & Page Visibility Controller (with Guard Modal)
# ---------------------------------------------------------------------------

@app.callback(
    Output("landing-view-container", "style"),
    Output("dashboard-view-container", "style"),
    Output("page-view-store", "data"),
    Output("no-dataset-modal", "opened"),
    Input("btn-proceed-to-dashboard", "n_clicks"),
    Input("btn-nav-dashboard", "n_clicks"),
    Input("btn-nav-landing", "n_clicks"),
    Input("header-brand-button", "n_clicks"),
    Input("btn-modal-upload-custom", "n_clicks"),
    Input("btn-modal-load-benchmark", "n_clicks"),
    State("page-view-store", "data"),
    prevent_initial_call=True,
)
def handle_page_navigation(
    btn_proceed: int,
    btn_nav_dash: int,
    btn_nav_land: int,
    btn_brand: int,
    btn_modal_upload: int,
    btn_modal_demo: int,
    current_page: str,
):
    """Toggles visibility between Landing View and Dashboard View, with guard modal if no data."""
    try:
        triggered_id = ctx.triggered_id
    except Exception:
        triggered_id = None

    has_data = state.clean_sales_df is not None and not state.clean_sales_df.empty

    # Guard: User clicks Dashboard from nav without any dataset loaded
    if triggered_id == "btn-nav-dashboard" and not has_data:
        return {"display": "block"}, {"display": "none"}, "landing", True

    # User clicks modal's Go to Upload
    if triggered_id == "btn-modal-upload-custom":
        return {"display": "block"}, {"display": "none"}, "landing", False

    # User clicks modal's Load Demo Dataset
    if triggered_id == "btn-modal-load-benchmark":
        return {"display": "none"}, {"display": "block"}, "dashboard", False

    # User clicks Proceed to Dashboard or Nav Dashboard (with active data)
    if triggered_id in ["btn-proceed-to-dashboard", "btn-nav-dashboard"]:
        return {"display": "none"}, {"display": "block"}, "dashboard", False

    # User clicks Home or Brand logo
    if triggered_id in ["btn-nav-landing", "header-brand-button"]:
        return {"display": "block"}, {"display": "none"}, "landing", False

    # Default fallback
    if current_page == "dashboard" and has_data:
        return {"display": "none"}, {"display": "block"}, "dashboard", False
    return {"display": "block"}, {"display": "none"}, "landing", False


@app.callback(
    Output("tab-content", "children"),
    Input("main-tabs", "value"),
    Input("state-trigger", "data"),
    prevent_initial_call=True,
)
def render_tab_content(active_tab: str, _trigger: int):
    """Renders specific analytical view based on currently selected tab."""
    if active_tab == "tab-executive":
        return build_executive_view()
    elif active_tab == "tab-ingestion":
        return build_ingestion_view()
    elif active_tab == "tab-product":
        return build_product_view()
    elif active_tab == "tab-customer":
        return build_customer_view()
    elif active_tab == "tab-prediction":
        return build_prediction_view()
    elif active_tab == "tab-prioritisation":
        return build_prioritisation_view()
    elif active_tab == "tab-report":
        return build_report_view()
    return html.Div("View not found")


# ---------------------------------------------------------------------------
# Dark Mode Toggle Callback
# ---------------------------------------------------------------------------

@app.callback(
    Output("mantine-provider", "forceColorScheme"),
    Output("color-scheme-icon", "icon"),
    Output("color-scheme-store", "data"),
    Input("color-scheme-toggle", "n_clicks"),
    State("color-scheme-store", "data"),
    prevent_initial_call=True,
)
def toggle_dark_mode(n_clicks: int, current_scheme: str):
    """Toggles between light and dark mode."""
    if not n_clicks:
        return current_scheme or "light", "tabler:moon", current_scheme or "light"

    new_scheme = "dark" if current_scheme == "light" else "light"
    icon = "tabler:sun" if new_scheme == "dark" else "tabler:moon"
    return new_scheme, icon, new_scheme


# ---------------------------------------------------------------------------
# Demo Benchmark Dataset Loading (Header, Landing Hero, Landing Ingestion & Modal)
# ---------------------------------------------------------------------------

@app.callback(
    Output("header-dataset-badge-container", "children"),
    Output("landing-dataset-status-container", "children"),
    Output("btn-proceed-to-dashboard", "style"),
    Output("landing-demo-status", "children"),
    Output("state-trigger", "data"),
    Input("btn-load-benchmark", "n_clicks"),
    Input("btn-landing-load-benchmark", "n_clicks"),
    Input("btn-hero-load-demo", "n_clicks"),
    Input("btn-modal-load-benchmark", "n_clicks"),
    State("state-trigger", "data"),
    prevent_initial_call=True,
)
def handle_load_benchmark_unified(
    btn_header: int,
    btn_landing: int,
    btn_hero: int,
    btn_modal: int,
    current_trigger: int,
):
    """Loads the benchmark dataset and updates status across landing, modal, and header."""
    if not any([btn_header, btn_landing, btn_hero, btn_modal]):
        badge = dmc.Badge("No dataset loaded", color="gray", variant="light", size="lg")
        empty_status = build_landing_dataset_status(is_loaded=False)
        return badge, empty_status, PROCEED_BTN_HIDDEN, html.Div(), current_trigger

    state.load_benchmark()
    rows_count = len(state.clean_sales_df) if state.clean_sales_df is not None else 0
    cust_count = int(state.clean_sales_df["customer_id"].nunique()) if state.clean_sales_df is not None else 0
    net_rev = float(state.cleaning_summary.get("net_revenue", 0.0)) if state.cleaning_summary else 0.0
    date_min = state.cleaning_summary.get("date_min", "N/A") if state.cleaning_summary else "N/A"
    date_max = state.cleaning_summary.get("date_max", "N/A") if state.cleaning_summary else "N/A"
    date_span = f"{date_min} to {date_max}"

    badge = dmc.Badge(
        f"Active: {state.filename} ({rows_count:,} records)",
        color="teal",
        variant="light",
        size="lg",
        radius="sm",
    )

    status_card = build_landing_dataset_status(
        is_loaded=True,
        filename=state.filename,
        row_count=rows_count,
        customer_count=cust_count,
        net_revenue=net_rev,
        date_span=date_span,
    )

    demo_alert = dmc.Alert(
        f"Demo benchmark loaded: {rows_count:,} records spanning 18 months ready for analysis.",
        color="teal",
        variant="light",
        radius="sm",
    )

    return badge, status_card, PROCEED_BTN_VISIBLE, demo_alert, (current_trigger or 0) + 1


# ---------------------------------------------------------------------------
# File Upload Ingestion (Dedicated Landing Dropzone Callback)
# ---------------------------------------------------------------------------

@app.callback(
    Output("landing-upload-status", "children"),
    Output("header-dataset-badge-container", "children", allow_duplicate=True),
    Output("landing-dataset-status-container", "children", allow_duplicate=True),
    Output("btn-proceed-to-dashboard", "style", allow_duplicate=True),
    Output("state-trigger", "data", allow_duplicate=True),
    Input("upload-data-file-landing", "contents"),
    State("upload-data-file-landing", "filename"),
    State("state-trigger", "data"),
    prevent_initial_call=True,
)
def handle_landing_upload(contents: str, filename: str, current_trigger: int):
    """Parses uploaded CSV/Excel file from the Landing Page dropzone."""
    if not contents or not filename:
        empty_status = build_landing_dataset_status(is_loaded=False)
        return html.Div(), dmc.Badge("No file", color="gray"), empty_status, PROCEED_BTN_HIDDEN, current_trigger

    try:
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)

        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.StringIO(decoded.decode("utf-8", errors="replace")))
        elif filename.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            msg = dmc.Alert(
                "Unsupported file format. Please upload a standard CSV or Excel file.",
                color="red",
                variant="light",
                radius="sm",
            )
            empty_status = build_landing_dataset_status(is_loaded=False)
            return msg, dmc.Badge("Upload Error", color="red"), empty_status, PROCEED_BTN_HIDDEN, current_trigger

        # Schema detection
        mapping, _ = detect_column_mappings(list(df.columns))
        missing_required = [
            FIELD_LABELS.get(f, f)
            for f in CANONICAL_REQUIRED_FIELDS
            if not mapping.get(f)
        ]
        if missing_required:
            msg = dmc.Alert(
                f"Missing essential fields: {', '.join(missing_required)}. Ensure columns for date, invoice ID, customer ID, product SKU, quantity, and unit price exist.",
                color="red",
                variant="light",
                radius="sm",
            )
            empty_status = build_landing_dataset_status(is_loaded=False)
            return msg, dmc.Badge("Schema Mismatch", color="red"), empty_status, PROCEED_BTN_HIDDEN, current_trigger

        # Update application state
        state.set_uploaded_dataset(filename, df, mapping)
        clean_count = len(state.clean_sales_df) if state.clean_sales_df is not None else 0
        cust_count = int(state.clean_sales_df["customer_id"].nunique()) if state.clean_sales_df is not None else 0
        net_rev = float(state.cleaning_summary.get("net_revenue", 0.0)) if state.cleaning_summary else 0.0
        date_min = state.cleaning_summary.get("date_min", "N/A") if state.cleaning_summary else "N/A"
        date_max = state.cleaning_summary.get("date_max", "N/A") if state.cleaning_summary else "N/A"
        date_span = f"{date_min} to {date_max}"

        success_msg = dmc.Alert(
            f"Successfully processed '{filename}': Ingested {len(df):,} raw records, retained {clean_count:,} clean transactions.",
            color="teal",
            variant="light",
            radius="sm",
        )
        badge = dmc.Badge(
            f"Active: {filename} ({clean_count:,} records)",
            color="blue",
            variant="light",
            size="lg",
            radius="sm",
        )
        status_card = build_landing_dataset_status(
            is_loaded=True,
            filename=filename,
            row_count=clean_count,
            customer_count=cust_count,
            net_revenue=net_rev,
            date_span=date_span,
        )

        return success_msg, badge, status_card, PROCEED_BTN_VISIBLE, (current_trigger or 0) + 1

    except Exception as exc:
        err_msg = dmc.Alert(
            f"Error processing upload: {str(exc)}",
            color="red",
            variant="light",
            radius="sm",
        )
        empty_status = build_landing_dataset_status(is_loaded=False)
        return err_msg, dmc.Badge("Error", color="red"), empty_status, PROCEED_BTN_HIDDEN, current_trigger


# ---------------------------------------------------------------------------
# File Upload Ingestion (Dedicated Audit Tab Dropzone Callback)
# ---------------------------------------------------------------------------

@app.callback(
    Output("upload-status-message", "children"),
    Output("header-dataset-badge-container", "children", allow_duplicate=True),
    Output("landing-dataset-status-container", "children", allow_duplicate=True),
    Output("btn-proceed-to-dashboard", "style", allow_duplicate=True),
    Output("state-trigger", "data", allow_duplicate=True),
    Input("upload-data-file", "contents"),
    State("upload-data-file", "filename"),
    State("state-trigger", "data"),
    prevent_initial_call=True,
)
def handle_audit_upload(contents: str, filename: str, current_trigger: int):
    """Parses uploaded CSV/Excel file from the Audit Tab dropzone."""
    if not contents or not filename:
        empty_status = build_landing_dataset_status(is_loaded=False)
        return html.Div(), dmc.Badge("No file", color="gray"), empty_status, PROCEED_BTN_HIDDEN, current_trigger

    try:
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)

        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.StringIO(decoded.decode("utf-8", errors="replace")))
        elif filename.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            msg = dmc.Alert(
                "Unsupported file format. Please upload a standard CSV or Excel file.",
                color="red",
                variant="light",
                radius="sm",
            )
            empty_status = build_landing_dataset_status(is_loaded=False)
            return msg, dmc.Badge("Upload Error", color="red"), empty_status, PROCEED_BTN_HIDDEN, current_trigger

        # Schema detection
        mapping, _ = detect_column_mappings(list(df.columns))
        missing_required = [
            FIELD_LABELS.get(f, f)
            for f in CANONICAL_REQUIRED_FIELDS
            if not mapping.get(f)
        ]
        if missing_required:
            msg = dmc.Alert(
                f"Missing essential fields: {', '.join(missing_required)}. Ensure columns for date, invoice ID, customer ID, product SKU, quantity, and unit price exist.",
                color="red",
                variant="light",
                radius="sm",
            )
            empty_status = build_landing_dataset_status(is_loaded=False)
            return msg, dmc.Badge("Schema Mismatch", color="red"), empty_status, PROCEED_BTN_HIDDEN, current_trigger

        # Update application state
        state.set_uploaded_dataset(filename, df, mapping)
        clean_count = len(state.clean_sales_df) if state.clean_sales_df is not None else 0
        cust_count = int(state.clean_sales_df["customer_id"].nunique()) if state.clean_sales_df is not None else 0
        net_rev = float(state.cleaning_summary.get("net_revenue", 0.0)) if state.cleaning_summary else 0.0
        date_min = state.cleaning_summary.get("date_min", "N/A") if state.cleaning_summary else "N/A"
        date_max = state.cleaning_summary.get("date_max", "N/A") if state.cleaning_summary else "N/A"
        date_span = f"{date_min} to {date_max}"

        success_msg = dmc.Alert(
            f"Successfully processed '{filename}': Ingested {len(df):,} raw records, retained {clean_count:,} clean transactions.",
            color="teal",
            variant="light",
            radius="sm",
        )
        badge = dmc.Badge(
            f"Active: {filename} ({clean_count:,} records)",
            color="blue",
            variant="light",
            size="lg",
            radius="sm",
        )
        status_card = build_landing_dataset_status(
            is_loaded=True,
            filename=filename,
            row_count=clean_count,
            customer_count=cust_count,
            net_revenue=net_rev,
            date_span=date_span,
        )

        return success_msg, badge, status_card, PROCEED_BTN_VISIBLE, (current_trigger or 0) + 1

    except Exception as exc:
        err_msg = dmc.Alert(
            f"Error processing upload: {str(exc)}",
            color="red",
            variant="light",
            radius="sm",
        )
        empty_status = build_landing_dataset_status(is_loaded=False)
        return err_msg, dmc.Badge("Error", color="red"), empty_status, PROCEED_BTN_HIDDEN, current_trigger


# ---------------------------------------------------------------------------
# Downstream Analytics & Control Callbacks
# ---------------------------------------------------------------------------

@app.callback(
    Output("exec-trend-chart", "figure"),
    Input("exec-trend-interval", "value"),
    prevent_initial_call=True,
)
def handle_trend_interval(freq: str):
    """Updates executive sales trend chart on frequency interval switch."""
    return build_sales_trend_figure(state.clean_sales_df, freq=freq or "W")


@app.callback(
    Output("product-top-chart", "figure"),
    Input("product-sort-metric", "value"),
    prevent_initial_call=True,
)
def handle_product_sort(sort_metric: str):
    """Updates product ranking chart on metric switch."""
    return build_top_products_figure(state.clean_sales_df, top_n=10, by=sort_metric or "revenue")


@app.callback(
    Output("train-feedback-container", "children"),
    Output("state-trigger", "data", allow_duplicate=True),
    Input("btn-train-model", "n_clicks"),
    State("pred-model-type-select", "value"),
    State("pred-calibrate-select", "value"),
    State("state-trigger", "data"),
    prevent_initial_call=True,
)
def handle_model_training(n_clicks: int, model_type: str, calibrate_str: str, current_trigger: int):
    """Trains business-specific model and recalculates holdout evaluation."""
    if not n_clicks:
        return html.Div(), current_trigger

    calibrate_bool = calibrate_str == "true"
    report, msg = state.train_model(model_type=model_type or "gradient_boosting", calibrate=calibrate_bool)

    if report is not None:
        alert = dmc.Alert(
            f"Model successfully trained! PR-AUC: {report.metrics.get('pr_auc'):.3f} vs Baseline: {report.metrics.get('baseline_inactivity_rate'):.3f} ({report.reliability_verdict})",
            color="teal",
            variant="light",
            radius="sm",
        )
    else:
        alert = dmc.Alert(
            f"Training not completed: {msg}",
            color="orange",
            variant="light",
            radius="sm",
        )
    return alert, (current_trigger or 0) + 1


@app.callback(
    Output("state-trigger", "data", allow_duplicate=True),
    Input("btn-recalculate-priorities", "n_clicks"),
    State("slider-risk-threshold", "value"),
    State("slider-val-cutoff", "value"),
    State("slider-risk-weight", "value"),
    State("state-trigger", "data"),
    prevent_initial_call=True,
)
def handle_prioritisation_tuning(n_clicks: int, risk_thresh: float, val_cutoff: float, risk_weight: float, current_trigger: int):
    """Adjusts prioritisation formula thresholds and weights."""
    if not n_clicks:
        return current_trigger

    state.risk_threshold = float(risk_thresh)
    state.value_cutoff_pct = float(val_cutoff)
    state.risk_weight = float(risk_weight)
    state.refresh_predictions_and_priorities()
    return (current_trigger or 0) + 1


@app.callback(
    Output("download-queue-csv", "data"),
    Input("btn-download-queue-csv", "n_clicks"),
    prevent_initial_call=True,
)
def handle_download_queue(n_clicks: int):
    """Exports prioritised action queue to CSV."""
    if not n_clicks or state.prioritised_df is None:
        return None
    return dcc.send_data_frame(state.prioritised_df.to_csv, "retailiq_action_queue.csv", index=False)


@app.callback(
    Output("download-report-md", "data"),
    Input("btn-export-report-md", "n_clicks"),
    prevent_initial_call=True,
)
def handle_download_md_report(n_clicks: int):
    """Exports governance and quality report as Markdown."""
    if not n_clicks:
        return None

    audit_dict = build_audit_report(
        session_id="session_export",
        filename=state.filename or "No dataset",
        validation_stats={},
        cleaning_summary=state.cleaning_summary or {},
        model_eval_report=state.eval_report.to_dict() if state.eval_report else None,
    )
    md_content = export_report_markdown(audit_dict)
    return dict(content=md_content, filename="retailiq_governance_report.md")


@app.callback(
    Output("download-report-json", "data"),
    Input("btn-export-report-json", "n_clicks"),
    prevent_initial_call=True,
)
def handle_download_json_report(n_clicks: int):
    """Exports governance and quality audit log as JSON."""
    if not n_clicks:
        return None

    audit_dict = build_audit_report(
        session_id="session_export",
        filename=state.filename or "No dataset",
        validation_stats={},
        cleaning_summary=state.cleaning_summary or {},
        model_eval_report=state.eval_report.to_dict() if state.eval_report else None,
    )
    json_content = json.dumps(audit_dict, indent=2)
    return dict(content=json_content, filename="retailiq_audit_log.json")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    print(f"RetailIQ Dash Mantine application running at http://127.0.0.1:{port}")
    app.run(debug=True, host="127.0.0.1", port=port)
