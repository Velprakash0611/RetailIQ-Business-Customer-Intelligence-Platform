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
from dash import Dash, Input, Output, State, dcc, html
from dash_iconify import DashIconify

from retail_intelligence.dash_state import state
from retail_intelligence.dash_ui.header import build_header
from retail_intelligence.dash_ui.view_customer import build_customer_view
from retail_intelligence.dash_ui.view_executive import build_executive_view, build_sales_trend_figure
from retail_intelligence.dash_ui.view_ingestion import build_ingestion_view
from retail_intelligence.dash_ui.view_prediction import build_prediction_view
from retail_intelligence.dash_ui.view_prioritisation import build_prioritisation_view
from retail_intelligence.dash_ui.view_product import build_product_view, build_top_products_figure
from retail_intelligence.dash_ui.view_report import build_report_view
from retail_intelligence.reporting import build_audit_report, export_report_markdown
from retail_intelligence.schema_mapping import detect_column_mappings

# Initialize Dash application with Mantine styles
app = Dash(
    __name__,
    title="RetailIQ — Business & Customer Intelligence Platform",
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server

# Root application layout
app.layout = dmc.MantineProvider(
    theme={
        "colorScheme": "light",
        "primaryColor": "blue",
        "fontFamily": "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif",
    },
    children=[
        dcc.Store(id="state-trigger", data=0),
        # Global Navigation Header
        build_header(),
        # Main Content Container
        dmc.Container(
            size="xl",
            px="md",
            py="lg",
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
                # Dynamic tab view injection
                html.Div(id="tab-content", style={"marginTop": "20px"}),
            ],
        ),
    ],
)


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@app.callback(
    Output("tab-content", "children"),
    Input("main-tabs", "value"),
    Input("state-trigger", "data"),
)
def render_tab_content(active_tab: str, _trigger: int):
    """Renders view content based on currently active tab."""
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


@app.callback(
    Output("header-dataset-badge-container", "children"),
    Output("state-trigger", "data"),
    Input("btn-load-benchmark", "n_clicks"),
    State("state-trigger", "data"),
    prevent_initial_call=True,
)
def handle_load_benchmark(n_clicks: int, current_trigger: int):
    """Reloads the benchmark dataset and refreshes telemetry."""
    if not n_clicks:
        return dmc.Badge("No dataset loaded", color="gray"), current_trigger

    state.load_benchmark()
    rows_count = len(state.clean_sales_df) if state.clean_sales_df is not None else 0

    badge = dmc.Badge(
        f"Active: {state.filename} ({rows_count:,} records)",
        color="teal",
        variant="light",
        size="lg",
        radius="sm",
    )
    return badge, (current_trigger or 0) + 1


@app.callback(
    Output("upload-status-message", "children"),
    Output("header-dataset-badge-container", "children", allow_duplicate=True),
    Output("state-trigger", "data", allow_duplicate=True),
    Input("upload-data-file", "contents"),
    State("upload-data-file", "filename"),
    State("state-trigger", "data"),
    prevent_initial_call=True,
)
def handle_file_upload(contents: str, filename: str, current_trigger: int):
    """Parses uploaded CSV/Excel file, runs auto-mapping, cleans data, and updates state."""
    if not contents or not filename:
        return html.Div(), dmc.Badge("No file", color="gray"), current_trigger

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
            return msg, dmc.Badge("Upload Error", color="red"), current_trigger

        # Schema detection
        mapping, missing_req = detect_column_mappings(list(df.columns))
        if missing_req:
            msg = dmc.Alert(
                f"Missing essential fields: {', '.join(missing_req)}. Ensure columns for date, invoice ID, quantity, and unit price exist.",
                color="red",
                variant="light",
                radius="sm",
            )
            return msg, dmc.Badge("Schema Mismatch", color="red"), current_trigger

        # Update application state
        state.set_uploaded_dataset(filename, df, mapping)
        clean_count = len(state.clean_sales_df) if state.clean_sales_df is not None else 0

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
        return success_msg, badge, (current_trigger or 0) + 1

    except Exception as exc:
        err_msg = dmc.Alert(
            f"Error processing upload: {str(exc)}",
            color="red",
            variant="light",
            radius="sm",
        )
        return err_msg, dmc.Badge("Error", color="red"), current_trigger


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
        filename=state.filename,
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
        filename=state.filename,
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
