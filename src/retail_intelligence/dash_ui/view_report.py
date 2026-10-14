"""
Audit & Governance Reporting view for Dash Mantine UI.
Displays comprehensive data quality scorecard, processing audit logs,
predictive model governance, operational assumptions, and export actions.
"""

import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

from retail_intelligence.dash_state import state
from retail_intelligence.reporting import build_audit_report


def build_report_view() -> html.Div:
    """Renders the comprehensive audit log and export tab."""
    summary = state.cleaning_summary or {}
    eval_rep = state.eval_report

    audit_dict = build_audit_report(
        session_id="session_active",
        filename=state.filename,
        validation_stats={},
        cleaning_summary=summary,
        model_eval_report=eval_rep.to_dict() if eval_rep else None,
    )

    dq = audit_dict["data_quality_scorecard"]
    gov = audit_dict["model_governance"]

    # Scorecard table
    scorecard_data = [
        ["Total Raw Records Ingested", f"{dq.get('total_raw_rows', 0):,}"],
        ["Clean Sales Records (Retained)", f"{dq.get('clean_sales_rows', 0):,}"],
        ["Returns & Cancellations (Isolated)", f"{dq.get('returns_rows', 0):,}"],
        ["Excluded / Rejected Invalid Records", f"{dq.get('rejected_rows', 0):,}"],
        ["Exact Duplicate Rows Removed", f"{dq.get('duplicates_removed', 0):,}"],
        ["Registered Customer Transactions", f"{dq.get('registered_rows', 0):,}"],
        ["Guest / Unregistered Transactions", f"{dq.get('guest_rows', 0):,}"],
        ["Historical Observed Date Range", str(dq.get('historical_date_range', 'N/A'))],
        ["Gross Recorded Sales", f"${dq.get('gross_revenue', 0.0):,.2f}"],
        ["Returns & Refunds Impact", f"-${dq.get('returns_revenue', 0.0):,.2f}"],
        ["Net Recorded Revenue", f"${dq.get('net_revenue', 0.0):,.2f}"],
    ]

    return html.Div(
        children=[
            # Top Banner & Export Actions
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
                        children=[
                            html.Div([
                                dmc.Title("System Audit & Model Governance Report", order=4),
                                dmc.Text(f"Dataset: {state.filename} | Generated: {audit_dict['report_generated_at']}", size="xs", c="dimmed"),
                            ]),
                            dmc.Group(
                                gap="sm",
                                children=[
                                    dmc.Button(
                                        "Export Markdown Report",
                                        id="btn-export-report-md",
                                        variant="filled",
                                        color="blue",
                                        size="sm",
                                        leftSection=DashIconify(icon="tabler:file-text", width=16),
                                    ),
                                    dcc.Download(id="download-report-md"),
                                    dmc.Button(
                                        "Export JSON Audit",
                                        id="btn-export-report-json",
                                        variant="light",
                                        color="blue",
                                        size="sm",
                                        leftSection=DashIconify(icon="tabler:code", width=16),
                                    ),
                                    dcc.Download(id="download-report-json"),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            # 2 Columns: Quality Scorecard & Model Governance
            dmc.SimpleGrid(
                cols={"base": 1, "md": 2},
                spacing="lg",
                mb="lg",
                children=[
                    # Data Quality Scorecard
                    dmc.Paper(
                        p="lg",
                        radius="md",
                        withBorder=True,
                        shadow="xs",
                        children=[
                            dmc.Title("1. Data Processing & Quality Scorecard", order=4, mb="xs"),
                            dmc.Text("Verification of raw file filtering, deduplication, and separation of refunds", size="xs", c="dimmed", mb="md"),
                            dmc.Table(
                                data={
                                    "head": ["Audit Item", "Metric Value"],
                                    "body": scorecard_data,
                                },
                                striped=True,
                                highlightOnHover=True,
                                withTableBorder=True,
                            ),
                        ],
                    ),
                    # Model Governance & Evaluation
                    dmc.Paper(
                        p="lg",
                        radius="md",
                        withBorder=True,
                        shadow="xs",
                        children=[
                            dmc.Title("2. Predictive Model Governance", order=4, mb="xs"),
                            dmc.Text("Validation performance, probability calibration, and production readiness", size="xs", c="dimmed", mb="md"),
                            dmc.Paper(
                                p="md",
                                withBorder=True,
                                radius="sm",
                                mb="md",
                                children=[
                                    dmc.Text("Production Reliability Verdict", size="xs", c="dimmed"),
                                    dmc.Text(gov["reliability_verdict"], size="md", fw=700, c="teal" if "High" in gov["reliability_verdict"] else "orange"),
                                    dmc.Text(gov["verdict_explanation"], size="xs", c="dimmed", mt=4),
                                ],
                            ),
                            dmc.Title("Operational Assumptions & Limitations", order=5, mb="xs"),
                            dmc.List(
                                size="xs",
                                spacing="xs",
                                children=[
                                    dmc.ListItem("Prediction Target: Estimates likelihood of 0 purchases over the next 90 days."),
                                    dmc.ListItem("Leakage Prevention: Features are strictly computed on or before historical cutoff dates."),
                                    dmc.ListItem("Independent Retailer Principle: Never blindly transfers models between distinct retailers."),
                                    dmc.ListItem("Prioritisation vs Causality: Rankings prioritize outreach queues, not causal campaign uplift."),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ]
    )
