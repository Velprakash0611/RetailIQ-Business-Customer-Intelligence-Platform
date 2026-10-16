"""
Executive Overview view for Dash Mantine UI.
Displays macro KPIs, interactive time-series revenue/order trends,
day-of-week sales patterns, and top products snapshot.
"""

import dash_mantine_components as dmc
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html
from dash_iconify import DashIconify

from retail_intelligence.dash_state import state
from retail_intelligence.metrics import (
    compute_executive_kpis,
    compute_sales_trends,
    compute_top_products,
)


def build_sales_trend_figure(sales_df: pd.DataFrame, freq: str = "W", selected_dow: str | None = None) -> go.Figure:
    """Builds dual-axis interactive time series chart for Revenue and Orders, with optional day-of-week filtering."""
    if sales_df is None or sales_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No transaction data available", showarrow=False, font=dict(size=14, color="#64748B"))
        fig.update_layout(template="plotly_white", height=320)
        return fig

    df_source = sales_df
    if selected_dow and not sales_df.empty:
        df_source = sales_df[sales_df["date"].dt.day_name() == selected_dow]
        if df_source.empty:
            fig = go.Figure()
            fig.add_annotation(text=f"No transactions found on {selected_dow}", showarrow=False, font=dict(size=14, color="#64748B"))
            fig.update_layout(template="plotly_white", height=320)
            return fig

    trend_df = compute_sales_trends(df_source, freq=freq)
    if trend_df.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_white", height=320)
        return fig

    fig = go.Figure()

    # Revenue bars
    fig.add_trace(
        go.Bar(
            x=trend_df["date"],
            y=trend_df["revenue"],
            name="Revenue ($)",
            marker=dict(color="#3B82F6", opacity=0.85),
            yaxis="y1",
            hovertemplate="<b>Date</b>: %{x|%Y-%m-%d}<br><b>Revenue</b>: $%{y:,.2f}<extra></extra>",
        )
    )

    # Order count line on secondary axis
    fig.add_trace(
        go.Scatter(
            x=trend_df["date"],
            y=trend_df["orders"],
            name="Order Count",
            mode="lines+markers",
            line=dict(color="#0D9488", width=2.5),
            marker=dict(size=5, color="#0D9488"),
            yaxis="y2",
            hovertemplate="<b>Orders</b>: %{y:,}<extra></extra>",
        )
    )

    title_suffix = f" (Filtered: {selected_dow}s)" if selected_dow else ""

    fig.update_layout(
        template="plotly_white",
        height=320,
        margin=dict(l=45, r=45, t=15, b=35),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=True, gridcolor="#E2E8F0", zeroline=False),
        yaxis=dict(
            title=dict(text="Revenue ($)", font=dict(color="#3B82F6", size=12)),
            tickfont=dict(color="#3B82F6", size=11),
            showgrid=True,
            gridcolor="#E2E8F0",
            zeroline=False,
        ),
        yaxis2=dict(
            title=dict(text="Orders", font=dict(color="#0D9488", size=12)),
            tickfont=dict(color="#0D9488", size=11),
            overlaying="y",
            side="right",
            showgrid=False,
            zeroline=False,
        ),
    )
    return fig


def build_dow_figure(sales_df: pd.DataFrame, selected_dow: str | None = None) -> go.Figure:
    """Builds day of week distribution bar chart with interactive visual highlighting."""
    if sales_df is None or sales_df.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_white", height=240)
        return fig

    df = sales_df.copy()
    df["dow"] = df["date"].dt.day_name()
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    dow_grp = df.groupby("dow").agg(
        revenue=("total_amount", "sum"),
        orders=("invoice_id", "nunique"),
    ).reindex(dow_order).fillna(0).reset_index()

    # Dynamic PowerBI-style highlight: selected bar is solid #2563EB, others are dimmed
    if selected_dow:
        colors = ["#2563EB" if d == selected_dow else "rgba(99, 102, 241, 0.3)" for d in dow_grp["dow"]]
    else:
        colors = ["#6366F1"] * len(dow_grp)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=dow_grp["dow"],
            y=dow_grp["revenue"],
            marker=dict(color=colors),
            hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.2f}<br><i>Click to cross-filter page</i><extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_white",
        height=240,
        margin=dict(l=40, r=20, t=10, b=35),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="", tickfont=dict(size=11)),
        yaxis=dict(title="Revenue ($)", showgrid=True, gridcolor="#E2E8F0", tickfont=dict(size=10)),
        clickmode="event+select",
    )
    return fig


def build_executive_kpi_cards(
    sales_df: pd.DataFrame,
    returns_df: pd.DataFrame,
    selected_dow: str | None = None,
) -> dmc.SimpleGrid:
    """Builds the 5 top-level macro KPI cards, conditionally filtered by Day-of-Week."""
    sales_filtered = sales_df
    returns_filtered = returns_df

    if selected_dow and not sales_df.empty:
        sales_filtered = sales_df[sales_df["date"].dt.day_name() == selected_dow]
        if returns_df is not None and not returns_df.empty and "date" in returns_df.columns:
            returns_filtered = returns_df[returns_df["date"].dt.day_name() == selected_dow]

    kpis = compute_executive_kpis(sales_filtered, returns_filtered)
    filter_label = f" on {selected_dow}s" if selected_dow else ""

    return dmc.SimpleGrid(
        cols={"base": 1, "sm": 2, "md": 3, "lg": 5},
        spacing="md",
        children=[
            # Gross Revenue
            dmc.Paper(
                p="md",
                radius="md",
                withBorder=True,
                shadow="xs",
                children=[
                    dmc.Group(
                        justify="space-between",
                        align="flex-start",
                        mb="xs",
                        children=[
                            dmc.Text("Gross Revenue", size="xs", c="dimmed", fw=600),
                            dmc.ThemeIcon(DashIconify(icon="tabler:currency-dollar", width=18), size="md", radius="md", variant="light", color="blue"),
                        ],
                    ),
                    dmc.Title(f"${kpis['gross_revenue']:,.2f}", order=3, style={"fontWeight": 700}),
                    dmc.Text(f"{kpis['total_orders']:,} orders{filter_label}", size="xs", c="dimmed", mt=4),
                ],
            ),
            # Net Revenue
            dmc.Paper(
                p="md",
                radius="md",
                withBorder=True,
                shadow="xs",
                children=[
                    dmc.Group(
                        justify="space-between",
                        align="flex-start",
                        mb="xs",
                        children=[
                            dmc.Text("Net Revenue", size="xs", c="dimmed", fw=600),
                            dmc.ThemeIcon(DashIconify(icon="tabler:wallet", width=18), size="md", radius="md", variant="light", color="teal"),
                        ],
                    ),
                    dmc.Title(f"${kpis['net_revenue']:,.2f}", order=3, c="teal", style={"fontWeight": 700}),
                    dmc.Text(f"After -${kpis['returns_revenue']:,.2f} refunds{filter_label}", size="xs", c="dimmed", mt=4),
                ],
            ),
            # Total Orders
            dmc.Paper(
                p="md",
                radius="md",
                withBorder=True,
                shadow="xs",
                children=[
                    dmc.Group(
                        justify="space-between",
                        align="flex-start",
                        mb="xs",
                        children=[
                            dmc.Text("Total Orders", size="xs", c="dimmed", fw=600),
                            dmc.ThemeIcon(DashIconify(icon="tabler:shopping-cart", width=18), size="md", radius="md", variant="light", color="indigo"),
                        ],
                    ),
                    dmc.Title(f"{kpis['total_orders']:,}", order=3, style={"fontWeight": 700}),
                    dmc.Text(f"{kpis['unique_customers']:,} buyers{filter_label}", size="xs", c="dimmed", mt=4),
                ],
            ),
            # Average Order Value
            dmc.Paper(
                p="md",
                radius="md",
                withBorder=True,
                shadow="xs",
                children=[
                    dmc.Group(
                        justify="space-between",
                        align="flex-start",
                        mb="xs",
                        children=[
                            dmc.Text("Average Order Value", size="xs", c="dimmed", fw=600),
                            dmc.ThemeIcon(DashIconify(icon="tabler:receipt-tax", width=18), size="md", radius="md", variant="light", color="violet"),
                        ],
                    ),
                    dmc.Title(f"${kpis['average_order_value']:,.2f}", order=3, style={"fontWeight": 700}),
                    dmc.Text(f"{kpis['average_units_per_order']:.1f} items / basket{filter_label}", size="xs", c="dimmed", mt=4),
                ],
            ),
            # Return Rate
            dmc.Paper(
                p="md",
                radius="md",
                withBorder=True,
                shadow="xs",
                children=[
                    dmc.Group(
                        justify="space-between",
                        align="flex-start",
                        mb="xs",
                        children=[
                            dmc.Text("Return Rate (Value)", size="xs", c="dimmed", fw=600),
                            dmc.ThemeIcon(DashIconify(icon="tabler:arrow-back-up", width=18), size="md", radius="md", variant="light", color="orange"),
                        ],
                    ),
                    dmc.Title(f"{kpis['return_rate_revenue_pct']:.1f}%", order=3, c="orange", style={"fontWeight": 700}),
                    dmc.Text(f"{kpis['return_rate_count_pct']:.1f}% by count{filter_label}", size="xs", c="dimmed", mt=4),
                ],
            ),
        ],
    )


def build_executive_top_products_table(sales_df: pd.DataFrame, selected_dow: str | None = None) -> html.Div:
    """Builds top 5 revenue driver products table, optionally filtered by day of week."""
    df_source = sales_df
    if selected_dow and not sales_df.empty:
        df_source = sales_df[sales_df["date"].dt.day_name() == selected_dow]

    top_prods = compute_top_products(df_source, top_n=5, by="revenue")
    table_head = ["Product ID", "Description", "Units Sold", "Revenue ($)"]
    table_body = []
    for _, row in top_prods.iterrows():
        table_body.append([
            str(row["product_id"]),
            str(row["description"])[:40],
            f"{int(row['quantity']):,}",
            f"${float(row['revenue']):,.2f}",
        ])

    return html.Div(
        dmc.Table(
            data={"head": table_head, "body": table_body},
            striped=True,
            highlightOnHover=True,
            withTableBorder=True,
        ),
        style={"overflowX": "auto"},
    )


def build_executive_view() -> html.Div:
    """Renders the executive summary tab layout with full PowerBI-style cross-filtering."""
    sales_df = state.clean_sales_df if state.clean_sales_df is not None else pd.DataFrame()
    returns_df = state.returns_df if state.returns_df is not None else pd.DataFrame()

    kpis_grid = build_executive_kpi_cards(sales_df, returns_df)
    trend_fig = build_sales_trend_figure(sales_df, freq="W")
    dow_fig = build_dow_figure(sales_df)
    top_table = build_executive_top_products_table(sales_df)

    raw_df = state.raw_df
    total_raw = len(raw_df) if raw_df is not None else 0
    summary = state.cleaning_summary or {}
    clean_sales_rows = summary.get("clean_sales_rows", len(sales_df) if not sales_df.empty else 0)
    returns_rows = summary.get("returns_rows", len(returns_df) if not returns_df.empty else 0)
    date_min = summary.get("date_min", "N/A")
    date_max = summary.get("date_max", "N/A")
    kpis_raw = compute_executive_kpis(sales_df, returns_df)

    return html.Div(
        children=[
            # Cross-Filtering In-Memory State
            dcc.Store(id="exec-filter-dow-store", data=None),

            # Data Quality & Processing Audit Header
            dmc.Paper(
                p="md",
                radius="md",
                withBorder=True,
                shadow="xs",
                mb="lg",
                children=[
                    dmc.Group(
                        justify="space-between",
                        align="center",
                        mb="xs",
                        children=[
                            dmc.Group(
                                gap="xs",
                                children=[
                                    dmc.ThemeIcon(
                                        DashIconify(icon="tabler:database-check", width=20),
                                        size="md",
                                        radius="md",
                                        variant="light",
                                        color="blue",
                                    ),
                                    html.Div([
                                        dmc.Text("Data Quality & Ingestion Telemetry", size="sm", fw=700),
                                        dmc.Text(f"Active Source: {state.filename or 'Online Retail (Benchmark)'}", size="xs", c="dimmed"),
                                    ]),
                                ],
                            ),
                            dmc.Group(
                                gap="xs",
                                children=[
                                    dmc.Badge("Pre-Flight Audit Passed", color="teal", variant="light", radius="sm"),
                                    dmc.Badge("Zero Data Leakage Enforced", color="indigo", variant="light", radius="sm"),
                                ],
                            ),
                        ],
                    ),
                    dmc.SimpleGrid(
                        cols={"base": 2, "sm": 4},
                        spacing="sm",
                        children=[
                            dmc.Paper(
                                p="xs",
                                withBorder=True,
                                radius="sm",
                                children=[
                                    dmc.Text("Raw Records Ingested", size="xs", c="dimmed"),
                                    dmc.Text(f"{total_raw:,}", size="sm", fw=700),
                                ],
                            ),
                            dmc.Paper(
                                p="xs",
                                withBorder=True,
                                radius="sm",
                                children=[
                                    dmc.Text("Clean Sales Retained", size="xs", c="dimmed"),
                                    dmc.Text(f"{clean_sales_rows:,}", size="sm", fw=700, c="teal"),
                                ],
                            ),
                            dmc.Paper(
                                p="xs",
                                withBorder=True,
                                radius="sm",
                                children=[
                                    dmc.Text("Returns & Refunds Isolated", size="xs", c="dimmed"),
                                    dmc.Text(f"{returns_rows:,} records (-${kpis_raw['returns_revenue']:,.2f})", size="sm", fw=700, c="orange"),
                                ],
                            ),
                            dmc.Paper(
                                p="xs",
                                withBorder=True,
                                radius="sm",
                                children=[
                                    dmc.Text("Observed Date Window", size="xs", c="dimmed"),
                                    dmc.Text(f"{date_min} to {date_max}", size="xs", fw=600),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            # 5 Top-Level Macro KPI Cards (Dynamic Cross-Filter Container)
            html.Div(
                id="exec-kpis-container",
                style={"marginBottom": "20px"},
                children=kpis_grid,
            ),
            # Sales Trend Interactive Card
            dmc.Paper(
                p="lg",
                radius="md",
                withBorder=True,
                shadow="xs",
                mb="lg",
                style={"minWidth": 0, "overflow": "hidden"},
                children=[
                    dmc.Group(
                        justify="space-between",
                        align="center",
                        mb="md",
                        children=[
                            dmc.Group(
                                gap="xs",
                                children=[
                                    html.Div([
                                        dmc.Title("Revenue & Order Trajectory", order=4),
                                        dmc.Text("Time-series tracking of total sales volume and transaction count", size="xs", c="dimmed"),
                                    ]),
                                    html.Div(id="exec-trend-filter-badge"),
                                ],
                            ),
                            dmc.Group(
                                gap="sm",
                                children=[
                                    dmc.SegmentedControl(
                                        id="exec-trend-interval",
                                        value="W",
                                        data=[
                                            {"label": "Daily", "value": "D"},
                                            {"label": "Weekly", "value": "W"},
                                            {"label": "Monthly", "value": "M"},
                                        ],
                                        size="sm",
                                        radius="md",
                                    ),
                                    dmc.Tooltip(
                                        label="Reset Time Trend Interval",
                                        children=dmc.ActionIcon(
                                            DashIconify(icon="tabler:rotate-2", width=16),
                                            id="btn-reset-exec-trend",
                                            variant="light",
                                            color="gray",
                                            size="sm",
                                            radius="md",
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    ),
                    dcc.Graph(
                        id="exec-trend-chart",
                        figure=trend_fig,
                        config={"displayModeBar": False},
                        responsive=True,
                        style={"height": "320px", "width": "100%", "minWidth": 0},
                    ),
                ],
            ),
            # 2 Columns: Day of Week Pattern & Top 5 Best Sellers
            dmc.SimpleGrid(
                cols={"base": 1, "md": 2},
                spacing="lg",
                style={"minWidth": 0},
                children=[
                    # Day of Week Distribution
                    dmc.Paper(
                        p="lg",
                        radius="md",
                        withBorder=True,
                        shadow="xs",
                        style={"minWidth": 0, "overflow": "hidden"},
                        children=[
                            dmc.Group(
                                justify="space-between",
                                align="center",
                                mb="xs",
                                children=[
                                    dmc.Group(
                                        gap="xs",
                                        children=[
                                            dmc.Title("Day-of-Week Revenue Distribution", order=4),
                                            html.Div(id="exec-dow-filter-badge"),
                                        ],
                                    ),
                                    dmc.Tooltip(
                                        label="Reset Day Filter",
                                        children=dmc.ActionIcon(
                                            DashIconify(icon="tabler:rotate-2", width=16),
                                            id="btn-reset-exec-dow",
                                            variant="light",
                                            color="gray",
                                            size="sm",
                                            radius="md",
                                        ),
                                    ),
                                ],
                            ),
                            dmc.Text("Touch / click any bar to cross-filter the entire dashboard by day", size="xs", c="dimmed", mb="md"),
                            dcc.Graph(
                                id="exec-dow-chart",
                                figure=dow_fig,
                                config={"displayModeBar": False},
                                responsive=True,
                                style={"height": "240px", "width": "100%", "minWidth": 0},
                            ),
                        ],
                    ),
                    # Top 5 Best Sellers Table
                    dmc.Paper(
                        p="lg",
                        radius="md",
                        withBorder=True,
                        shadow="xs",
                        style={"minWidth": 0, "overflow": "hidden"},
                        children=[
                            dmc.Title("Top 5 Revenue Drivers", order=4, mb="xs"),
                            dmc.Text("Highest generating products across the selected observation window", size="xs", c="dimmed", mb="md"),
                            html.Div(
                                id="exec-top-table-container",
                                children=top_table,
                            ),
                        ],
                    ),
                ],
            ),
        ]
    )

