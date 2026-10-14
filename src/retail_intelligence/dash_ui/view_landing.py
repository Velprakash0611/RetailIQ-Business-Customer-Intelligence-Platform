"""
Landing Page view for RetailIQ Dash Mantine application.
Enterprise SaaS introduction, value pillars, and interactive dataset ingestion.
"""

from typing import Optional

import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

from retail_intelligence.dash_state import state


def build_landing_dataset_status(
    is_loaded: bool,
    filename: Optional[str] = None,
    row_count: int = 0,
    customer_count: int = 0,
    net_revenue: float = 0.0,
    date_span: str = "N/A",
) -> dmc.Paper:
    """Builds the dynamic status card with the Proceed button once dataset is loaded."""
    if not is_loaded:
        return dmc.Paper(
            p="lg",
            radius="md",
            withBorder=True,
            children=[
                dmc.Alert(
                    title="Awaiting Dataset Ingestion",
                    color="blue",
                    variant="light",
                    radius="sm",
                    icon=DashIconify(icon="tabler:info-circle", width=22),
                    children=(
                        "No dataset is currently loaded. Drag and drop your store transaction file (CSV or Excel) above, "
                        "or click 'Load Demo Benchmark Dataset' to instantly explore the platform with 18 months of historical retail data."
                    ),
                ),
            ],
        )

    return dmc.Paper(
        p="xl",
        radius="md",
        withBorder=True,
        shadow="sm",
        children=[
            dmc.Group(
                justify="space-between",
                align="center",
                mb="md",
                children=[
                    dmc.Group(
                        gap="sm",
                        children=[
                            dmc.ThemeIcon(
                                DashIconify(icon="tabler:circle-check", width=24),
                                size="lg",
                                radius="xl",
                                color="teal",
                                variant="light",
                            ),
                            html.Div([
                                dmc.Text("Active Dataset Successfully Ingested", size="xs", c="teal", fw=700),
                                dmc.Title(filename or "Active Transaction File", order=3),
                            ]),
                        ],
                    ),
                    dmc.Badge("Ready for Analysis", color="teal", size="lg", variant="filled"),
                ],
            ),
            dmc.SimpleGrid(
                cols={"base": 2, "sm": 4},
                spacing="md",
                mb="xl",
                children=[
                    dmc.Paper(
                        p="md",
                        withBorder=True,
                        radius="sm",
                        children=[
                            dmc.Text("Clean Transactions", size="xs", c="dimmed"),
                            dmc.Title(f"{row_count:,}", order=4),
                        ],
                    ),
                    dmc.Paper(
                        p="md",
                        withBorder=True,
                        radius="sm",
                        children=[
                            dmc.Text("Unique Customers", size="xs", c="dimmed"),
                            dmc.Title(f"{customer_count:,}", order=4),
                        ],
                    ),
                    dmc.Paper(
                        p="md",
                        withBorder=True,
                        radius="sm",
                        children=[
                            dmc.Text("Net Sales Revenue", size="xs", c="dimmed"),
                            dmc.Title(f"${net_revenue:,.2f}", order=4),
                        ],
                    ),
                    dmc.Paper(
                        p="md",
                        withBorder=True,
                        radius="sm",
                        children=[
                            dmc.Text("Historical Date Span", size="xs", c="dimmed"),
                            dmc.Text(date_span, size="sm", fw=600),
                        ],
                    ),
                ],
            ),
        ],
    )


def build_landing_view() -> html.Div:
    """Renders the comprehensive, impressive enterprise landing page."""
    has_data = state.clean_sales_df is not None and not state.clean_sales_df.empty
    row_count = len(state.clean_sales_df) if has_data else 0
    cust_count = int(state.clean_sales_df["customer_id"].nunique()) if has_data else 0
    net_rev = float(state.cleaning_summary.get("net_revenue", 0.0)) if state.cleaning_summary else 0.0
    date_min = state.cleaning_summary.get("date_min", "N/A") if state.cleaning_summary else "N/A"
    date_max = state.cleaning_summary.get("date_max", "N/A") if state.cleaning_summary else "N/A"
    date_span = f"{date_min} to {date_max}" if has_data else "N/A"

    return html.Div(
        children=[
            # 1. HERO SECTION
            dmc.Paper(
                p={"base": "lg", "md": "xl"},
                radius="lg",
                withBorder=True,
                mb="xl",
                style={"position": "relative", "overflow": "hidden"},
                children=[
                    dmc.Stack(
                        align="center",
                        gap="md",
                        style={"textAlign": "center", "maxWidth": "880px", "margin": "0 auto"},
                        children=[
                            dmc.Badge(
                                "Enterprise Retail & Customer Intelligence Platform",
                                color="blue",
                                variant="light",
                                size="lg",
                                radius="sm",
                            ),
                            dmc.Title(
                                "Transform Transaction Data into Predictive Retention & Revenue Growth",
                                order=1,
                                style={
                                    "fontWeight": 800,
                                    "letterSpacing": "-0.7px",
                                    "fontSize": "38px",
                                    "lineHeight": 1.2,
                                },
                            ),
                            dmc.Text(
                                "Upload your raw store transactions to instantly unlock executive sales diagnostics, "
                                "RFM behavioral personas, calibrated 90-day inactivity predictions, and a prioritized "
                                "VIP intervention queue designed to protect customer relationships before they churn.",
                                size="md",
                                c="dimmed",
                                style={"maxWidth": "720px", "lineHeight": 1.6},
                            ),
                            # Action button row
                            dmc.Group(
                                gap="md",
                                justify="center",
                                mt="sm",
                                children=[
                                    dmc.Anchor(
                                        dmc.Button(
                                            "Ingest Your Dataset Below",
                                            size="md",
                                            color="blue",
                                            radius="md",
                                            leftSection=DashIconify(icon="tabler:upload", width=18),
                                        ),
                                        href="#ingestion-section",
                                        underline=False,
                                    ),
                                    dmc.Button(
                                        "Load Demo Benchmark (18 Months)",
                                        id="btn-hero-load-demo",
                                        size="md",
                                        variant="outline",
                                        color="teal",
                                        radius="md",
                                        leftSection=DashIconify(icon="tabler:database", width=18),
                                    ),
                                ],
                            ),
                            # Highlights pill row
                            dmc.SimpleGrid(
                                cols={"base": 2, "sm": 4},
                                spacing="md",
                                mt="lg",
                                style={"width": "100%"},
                                children=[
                                    dmc.Paper(
                                        p="sm",
                                        withBorder=True,
                                        radius="sm",
                                        children=[
                                            DashIconify(icon="tabler:shield-check", width=22, color="#0D9488"),
                                            dmc.Text("Zero Data Leakage", size="xs", fw=700, mt="xs"),
                                            dmc.Text("Point-in-time temporal cutoffs", size="xs", c="dimmed"),
                                        ],
                                    ),
                                    dmc.Paper(
                                        p="sm",
                                        withBorder=True,
                                        radius="sm",
                                        children=[
                                            DashIconify(icon="tabler:layout-grid", width=22, color="#3B82F6"),
                                            dmc.Text("4-Quadrant Matrix", size="xs", fw=700, mt="xs"),
                                            dmc.Text("Inactivity risk × Lifetime spend", size="xs", c="dimmed"),
                                        ],
                                    ),
                                    dmc.Paper(
                                        p="sm",
                                        withBorder=True,
                                        radius="sm",
                                        children=[
                                            DashIconify(icon="tabler:users-group", width=22, color="#8B5CF6"),
                                            dmc.Text("11 RFM Personas", size="xs", fw=700, mt="xs"),
                                            dmc.Text("Quantile behavioral segmentation", size="xs", c="dimmed"),
                                        ],
                                    ),
                                    dmc.Paper(
                                        p="sm",
                                        withBorder=True,
                                        radius="sm",
                                        children=[
                                            DashIconify(icon="tabler:file-certificate", width=22, color="#F59E0B"),
                                            dmc.Text("Pre-Flight Data Audit", size="xs", fw=700, mt="xs"),
                                            dmc.Text("Refunds & guest checkout hygiene", size="xs", c="dimmed"),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            # 2. HOW IT WORKS IN 3 STEPS
            dmc.Stack(
                gap="xs",
                mb="lg",
                style={"textAlign": "center"},
                children=[
                    dmc.Badge("Platform Workflow", color="gray", variant="light", size="md"),
                    dmc.Title("End-to-End Retail Intelligence Architecture", order=2),
                    dmc.Text(
                        "From messy CSV/Excel export to targeted customer intervention in three seamless phases.",
                        size="sm",
                        c="dimmed",
                    ),
                ],
            ),
            dmc.SimpleGrid(
                cols={"base": 1, "md": 3},
                spacing="lg",
                mb="xl",
                children=[
                    # Step 1
                    dmc.Paper(
                        p="lg",
                        radius="md",
                        withBorder=True,
                        children=[
                            dmc.Group(
                                justify="space-between",
                                mb="sm",
                                children=[
                                    dmc.ThemeIcon(
                                        DashIconify(icon="tabler:database-import", width=22),
                                        size="lg",
                                        radius="md",
                                        color="blue",
                                        variant="light",
                                    ),
                                    dmc.Badge("Step 01", color="blue", variant="subtle"),
                                ],
                            ),
                            dmc.Title("Ingest & Audit", order=4, mb="xs"),
                            dmc.Text(
                                "Upload raw sales logs from Shopify, Magento, WooCommerce, or your ERP. "
                                "RetailIQ automatically detects column headers, isolates returns into a dedicated ledger, "
                                "tags guest checkouts, and verifies date span sufficiency.",
                                size="sm",
                                c="dimmed",
                                style={"lineHeight": 1.5},
                            ),
                        ],
                    ),
                    # Step 2
                    dmc.Paper(
                        p="lg",
                        radius="md",
                        withBorder=True,
                        children=[
                            dmc.Group(
                                justify="space-between",
                                mb="sm",
                                children=[
                                    dmc.ThemeIcon(
                                        DashIconify(icon="tabler:brain", width=22),
                                        size="lg",
                                        radius="md",
                                        color="teal",
                                        variant="light",
                                    ),
                                    dmc.Badge("Step 02", color="teal", variant="subtle"),
                                ],
                            ),
                            dmc.Title("Analyze & Predict", order=4, mb="xs"),
                            dmc.Text(
                                "Explore executive sales trends, AOV, declining product anomalies, and 11-persona RFM segmentation. "
                                "Trains a time-aware machine learning classifier with cross-validated probability calibration "
                                "to forecast 90-day inactivity risk.",
                                size="sm",
                                c="dimmed",
                                style={"lineHeight": 1.5},
                            ),
                        ],
                    ),
                    # Step 3
                    dmc.Paper(
                        p="lg",
                        radius="md",
                        withBorder=True,
                        children=[
                            dmc.Group(
                                justify="space-between",
                                mb="sm",
                                children=[
                                    dmc.ThemeIcon(
                                        DashIconify(icon="tabler:list-check", width=22),
                                        size="lg",
                                        radius="md",
                                        color="indigo",
                                        variant="light",
                                    ),
                                    dmc.Badge("Step 03", color="indigo", variant="subtle"),
                                ],
                            ),
                            dmc.Title("Prioritize & Retain", order=4, mb="xs"),
                            dmc.Text(
                                "View customers plotted on an interactive 2x2 Risk vs. Value scatter matrix. "
                                "Filter immediately to VIP At-Risk customers, customize priority score formulas, and export "
                                "a clean CSV retention list directly into your CRM or marketing platform.",
                                size="sm",
                                c="dimmed",
                                style={"lineHeight": 1.5},
                            ),
                        ],
                    ),
                ],
            ),
            # 3. INTERACTIVE INGESTION SECTION
            html.Div(id="ingestion-section", style={"paddingTop": "20px"}),
            dmc.Paper(
                p="xl",
                radius="lg",
                withBorder=True,
                mb="xl",
                children=[
                    dmc.Stack(
                        align="center",
                        gap="xs",
                        mb="xl",
                        style={"textAlign": "center"},
                        children=[
                            dmc.Badge("Dataset Ingestion", color="blue", variant="light", size="md"),
                            dmc.Title("Ingest Your Retail Dataset", order=2),
                            dmc.Text(
                                "Upload your transaction file (CSV or Excel) or test immediately with our bundled 18-month retail benchmark dataset.",
                                size="sm",
                                c="dimmed",
                            ),
                        ],
                    ),
                    dmc.SimpleGrid(
                        cols={"base": 1, "md": 2},
                        spacing="lg",
                        mb="xl",
                        children=[
                            # Option A: File Upload
                            dmc.Paper(
                                p="lg",
                                radius="md",
                                withBorder=True,
                                children=[
                                    dmc.Group(
                                        gap="xs",
                                        mb="xs",
                                        children=[
                                            dmc.ThemeIcon(DashIconify(icon="tabler:upload", width=18), color="blue", variant="light"),
                                            dmc.Title("Option A: Upload Transaction File", order=4),
                                        ],
                                    ),
                                    dmc.Text(
                                        "Accepts CSV or Excel (.xlsx, .xls) files. Automatically identifies required retail fields.",
                                        size="xs",
                                        c="dimmed",
                                        mb="md",
                                    ),
                                    dcc.Upload(
                                        id="upload-data-file-landing",
                                        children=html.Div(
                                            style={
                                                "border": "2px dashed #94A3B8",
                                                "borderRadius": "8px",
                                                "padding": "36px 16px",
                                                "textAlign": "center",
                                                "cursor": "pointer",
                                                "transition": "border-color 0.2s ease",
                                            },
                                            children=[
                                                DashIconify(icon="tabler:cloud-upload", width=42, color="#3B82F6"),
                                                dmc.Text("Drag & drop your file here, or click to browse", size="sm", fw=600, mt="xs"),
                                                dmc.Text("Supported: CSV, XLSX, XLS (Max 100MB)", size="xs", c="dimmed"),
                                            ],
                                        ),
                                        multiple=False,
                                    ),
                                    html.Div(id="landing-upload-status", style={"marginTop": "10px"}),
                                ],
                            ),
                            # Option B: Demo Benchmark Dataset
                            dmc.Paper(
                                p="lg",
                                radius="md",
                                withBorder=True,
                                children=[
                                    dmc.Group(
                                        gap="xs",
                                        mb="xs",
                                        children=[
                                            dmc.ThemeIcon(DashIconify(icon="tabler:sparkles", width=18), color="teal", variant="light"),
                                            dmc.Title("Option B: Instant 18-Month Demo Dataset", order=4),
                                        ],
                                    ),
                                    dmc.Text(
                                        "Pre-configured 18-month synthetic retail transaction dataset with 8,910 clean records.",
                                        size="xs",
                                        c="dimmed",
                                        mb="md",
                                    ),
                                    dmc.Paper(
                                        p="md",
                                        radius="sm",
                                        withBorder=True,
                                        mb="md",
                                        children=[
                                            dmc.SimpleGrid(
                                                cols=2,
                                                spacing="xs",
                                                children=[
                                                    dmc.Text("• 8,910 Transaction Rows", size="xs"),
                                                    dmc.Text("• 4,372 Unique Customers", size="xs"),
                                                    dmc.Text("• 18-Month History Depth", size="xs"),
                                                    dmc.Text("• Pre-Trained ML Model", size="xs"),
                                                ],
                                            ),
                                        ],
                                    ),
                                    dmc.Button(
                                        "Load Demo Benchmark Dataset",
                                        id="btn-landing-load-benchmark",
                                        color="teal",
                                        variant="light",
                                        size="md",
                                        fullWidth=True,
                                        radius="md",
                                        leftSection=DashIconify(icon="tabler:database", width=18),
                                    ),
                                    html.Div(id="landing-demo-status", style={"marginTop": "10px"}),
                                ],
                            ),
                        ],
                    ),
                    # Dynamic Status Card
                    html.Div(
                        id="landing-dataset-status-container",
                        children=build_landing_dataset_status(
                            is_loaded=has_data,
                            filename=state.filename,
                            row_count=row_count,
                            customer_count=cust_count,
                            net_revenue=net_rev,
                            date_span=date_span,
                        ),
                    ),
                    # Permanent Proceed Button (Callback Input Target)
                    dmc.Button(
                        "Proceed to Intelligence Dashboard",
                        id="btn-proceed-to-dashboard",
                        size="lg",
                        color="blue",
                        variant="filled",
                        fullWidth=True,
                        radius="md",
                        leftSection=DashIconify(icon="tabler:arrow-right", width=22),
                        style={
                            "display": "block" if has_data else "none",
                            "height": "52px",
                            "fontSize": "16px",
                            "fontWeight": 600,
                            "marginTop": "20px",
                        },
                    ),
                ],
            ),
        ],
    )

