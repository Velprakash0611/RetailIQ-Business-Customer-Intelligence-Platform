"""
Data Ingestion and Pre-Flight Validation view for Dash Mantine UI.
"""

import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

from retail_intelligence.dash_state import state


def build_ingestion_view() -> html.Div:
    """Renders file upload, schema mapping configuration, and pre-flight audit findings."""
    raw_df = state.raw_df
    summary = state.cleaning_summary or {}
    total_raw = len(raw_df) if raw_df is not None else 0

    return html.Div(
        children=[
            # Top Banner
            dmc.Alert(
                title="Independent Business Prediction Principle",
                color="blue",
                variant="light",
                radius="md",
                mb="lg",
                icon=DashIconify(icon="tabler:info-circle", width=22),
                children=(
                    "RetailIQ does not assume a model trained on one retailer generalizes to another. "
                    "Upload your own CSV or Excel transaction file to train an independent business model, "
                    "or explore using the bundled 18-month benchmark dataset."
                ),
            ),
            # Upload & Inspection Section
            dmc.SimpleGrid(
                cols={"base": 1, "md": 2},
                spacing="lg",
                mb="lg",
                children=[
                    # Upload Box
                    dmc.Paper(
                        p="lg",
                        radius="md",
                        withBorder=True,
                        shadow="xs",
                        children=[
                            dmc.Title("1. Upload Transaction File", order=4, mb="xs"),
                            dmc.Text("Accepts standard CSV or Excel (.xlsx, .xls) files containing historical orders.", size="sm", c="dimmed", mb="md"),
                            dcc.Upload(
                                id="upload-data-file",
                                children=html.Div(
                                    style={
                                        "border": "2px dashed #94A3B8",
                                        "borderRadius": "8px",
                                        "padding": "32px 16px",
                                        "textAlign": "center",
                                        "cursor": "pointer",
                                    },
                                    children=[
                                        DashIconify(icon="tabler:cloud-upload", width=36, color="#3B82F6"),
                                        dmc.Text("Drag and drop your transaction file here, or click to browse", size="sm", fw=500, mt="xs"),
                                        dmc.Text("CSV, XLSX, or XLS (Max 100MB)", size="xs", c="dimmed"),
                                    ],
                                ),
                                multiple=False,
                            ),
                            html.Div(id="upload-status-message", style={"marginTop": "12px"}),
                        ],
                    ),
                    # Pre-flight Metrics
                    dmc.Paper(
                        p="lg",
                        radius="md",
                        withBorder=True,
                        shadow="xs",
                        children=[
                            dmc.Title("2. Current File Telemetry", order=4, mb="xs"),
                            dmc.Text(f"Active Source: {state.filename}", size="sm", c="dimmed", mb="md"),
                            dmc.SimpleGrid(
                                cols=2,
                                spacing="md",
                                children=[
                                    dmc.Paper(
                                        p="md",
                                        withBorder=True,
                                        radius="sm",
                                        children=[
                                            dmc.Text("Total Records Ingested", size="xs", c="dimmed"),
                                            dmc.Title(f"{total_raw:,}", order=3),
                                        ],
                                    ),
                                    dmc.Paper(
                                        p="md",
                                        withBorder=True,
                                        radius="sm",
                                        children=[
                                            dmc.Text("Historical Date Range", size="xs", c="dimmed"),
                                            dmc.Text(f"{summary.get('date_min', 'N/A')} to {summary.get('date_max', 'N/A')}", size="sm", fw=600),
                                        ],
                                    ),
                                    dmc.Paper(
                                        p="md",
                                        withBorder=True,
                                        radius="sm",
                                        children=[
                                            dmc.Text("Clean Sales Lines", size="xs", c="dimmed"),
                                            dmc.Title(f"{summary.get('clean_sales_rows', 0):,}", order=3, c="teal"),
                                        ],
                                    ),
                                    dmc.Paper(
                                        p="md",
                                        withBorder=True,
                                        radius="sm",
                                        children=[
                                            dmc.Text("Returns Isolated", size="xs", c="dimmed"),
                                            dmc.Title(f"{summary.get('returns_rows', 0):,}", order=3, c="orange"),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            # Pipeline Processing Action Card
            dmc.Paper(
                p="lg",
                radius="md",
                withBorder=True,
                shadow="xs",
                children=[
                    dmc.Group(
                        justify="space-between",
                        align="center",
                        children=[
                            html.Div([
                                dmc.Title("3. Processing & Analytical Pipeline Status", order=4),
                                dmc.Text("Transactions are deduplicated, refunds isolated, and customer features point-in-time indexed.", size="sm", c="dimmed"),
                            ]),
                            dmc.Button(
                                "Reprocess Analytical Tables",
                                id="btn-reprocess-pipeline",
                                variant="filled",
                                color="blue",
                                leftSection=DashIconify(icon="tabler:refresh", width=18),
                            ),
                        ],
                    ),
                    dmc.Divider(my="md"),
                    dmc.SimpleGrid(
                        cols=4,
                        spacing="md",
                        children=[
                            dmc.Paper(
                                p="sm",
                                withBorder=True,
                                radius="sm",
                                children=[
                                    dmc.Text("Gross Revenue", size="xs", c="dimmed"),
                                    dmc.Text(f"${summary.get('total_gross_revenue', 0.0):,.2f}", size="lg", fw=700),
                                ],
                            ),
                            dmc.Paper(
                                p="sm",
                                withBorder=True,
                                radius="sm",
                                children=[
                                    dmc.Text("Returns Impact", size="xs", c="dimmed"),
                                    dmc.Text(f"-${summary.get('total_returns_revenue', 0.0):,.2f}", size="lg", fw=700, c="red"),
                                ],
                            ),
                            dmc.Paper(
                                p="sm",
                                withBorder=True,
                                radius="sm",
                                children=[
                                    dmc.Text("Net Recorded Sales", size="xs", c="dimmed"),
                                    dmc.Text(f"${summary.get('net_revenue', 0.0):,.2f}", size="lg", fw=700, c="teal"),
                                ],
                            ),
                            dmc.Paper(
                                p="sm",
                                withBorder=True,
                                radius="sm",
                                children=[
                                    dmc.Text("Registered Buyers", size="xs", c="dimmed"),
                                    dmc.Text(f"{summary.get('registered_rows', 0):,} rows", size="lg", fw=700),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ]
    )
