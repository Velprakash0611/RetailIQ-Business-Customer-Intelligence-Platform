"""
Customer Intelligence view for Dash Mantine UI.
Displays customer behavioral distributions, RFM segmentation personas,
and monthly cohort retention matrices.
"""

import dash_mantine_components as dmc
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html

from retail_intelligence.customer_features import compute_customer_features
from retail_intelligence.dash_state import state
from retail_intelligence.metrics import compute_cohort_retention
from retail_intelligence.segmentation import assign_rfm_segments, compute_segment_summary


def build_rfm_persona_figure(segment_summary_df: pd.DataFrame) -> go.Figure:
    """Builds horizontal bar chart for customer persona counts and revenue."""
    if segment_summary_df is None or segment_summary_df.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_white", height=320)
        return fig

    # Reverse so top persona is at top
    df = segment_summary_df.iloc[::-1].copy()

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df["segment"],
            x=df["customer_count"],
            name="Customer Count",
            orientation="h",
            marker=dict(color="#3B82F6", opacity=0.85),
            hovertemplate="<b>%{y}</b><br>Customers: %{x:,} (%{customdata[0]:.1f}%)<extra></extra>",
            customdata=df[["pct_customers"]].values,
        )
    )

    fig.update_layout(
        template="plotly_white",
        height=320,
        margin=dict(l=140, r=20, t=10, b=35),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Customer Count", showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(title="", tickfont=dict(size=11)),
    )
    return fig


def build_cohort_heatmap_figure(sales_df: pd.DataFrame) -> go.Figure:
    """Builds monthly cohort retention heatmap."""
    if sales_df is None or sales_df.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_white", height=320)
        return fig

    _, retention_matrix = compute_cohort_retention(sales_df)
    if retention_matrix.empty:
        fig = go.Figure()
        fig.add_annotation(text="Insufficient historical depth for cohort retention", showarrow=False, font=dict(color="#64748B"))
        fig.update_layout(template="plotly_white", height=320)
        return fig

    # Prepare values and text matrix
    z_vals = retention_matrix.values
    x_labels = [f"M+{c}" for c in retention_matrix.columns]
    y_labels = list(retention_matrix.index)

    text_vals = []
    for row in z_vals:
        row_text = []
        for val in row:
            if pd.isna(val) or np.isnan(val):
                row_text.append("")
            else:
                row_text.append(f"{val:.0f}%")
        text_vals.append(row_text)

    fig = go.Figure(
        data=go.Heatmap(
            z=z_vals,
            x=x_labels,
            y=y_labels,
            text=text_vals,
            texttemplate="%{text}",
            textfont={"size": 10},
            colorscale="Teal",
            zmin=0,
            zmax=100,
            colorbar=dict(title="Retention %", thickness=12, len=0.8),
            hoverongaps=False,
        )
    )

    fig.update_layout(
        template="plotly_white",
        height=320,
        margin=dict(l=60, r=20, t=10, b=35),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Months Since First Acquisition", tickfont=dict(size=11)),
        yaxis=dict(title="Acquisition Cohort", tickfont=dict(size=11), autorange="reversed"),
    )
    return fig


def build_recency_hist_figure(features_df: pd.DataFrame) -> go.Figure:
    """Builds recency days distribution histogram."""
    if features_df is None or features_df.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_white", height=240, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig

    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=features_df["recency_days"],
            nbinsx=25,
            marker=dict(color="#0D9488", opacity=0.8),
            hovertemplate="Recency: %{x} days<br>Count: %{y}<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_white",
        height=240,
        margin=dict(l=35, r=15, t=10, b=35),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Days Since Last Purchase", showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(title="Customers", showgrid=True, gridcolor="#E2E8F0"),
    )
    return fig


def build_customer_view() -> html.Div:
    """Renders the customer intelligence and RFM segmentation tab."""
    sales_df = state.clean_sales_df if state.clean_sales_df is not None else pd.DataFrame()
    returns_df = state.returns_df if state.returns_df is not None else pd.DataFrame()

    features_df = compute_customer_features(sales_df, returns_df=returns_df)
    segmented_df = assign_rfm_segments(features_df)
    summary_df = compute_segment_summary(segmented_df)

    # Compute high-level customer KPIs
    total_custs = len(features_df) if not features_df.empty else 0
    repeat_custs = len(features_df[features_df["frequency"] > 1]) if not features_df.empty else 0
    repeat_rate = (repeat_custs / total_custs * 100.0) if total_custs > 0 else 0.0
    avg_spend = float(features_df["total_spend"].mean()) if not features_df.empty else 0.0
    avg_recency = float(features_df["recency_days"].mean()) if not features_df.empty else 0.0

    # Figures
    persona_fig = build_rfm_persona_figure(summary_df)
    cohort_fig = build_cohort_heatmap_figure(sales_df)
    recency_fig = build_recency_hist_figure(features_df)

    # RFM Segment Summary Table
    seg_head = ["Segment Persona", "Customers", "Share (%)", "Total Revenue ($)", "Avg Spend ($)", "Avg Frequency", "Avg Recency"]
    seg_body = []
    for _, row in summary_df.iterrows():
        seg_body.append([
            str(row["segment"]),
            f"{int(row['customer_count']):,}",
            f"{float(row['pct_customers']):.1f}%",
            f"${float(row['total_revenue']):,.2f}",
            f"${float(row['avg_revenue']):,.2f}",
            f"{float(row['avg_frequency']):.1f}",
            f"{float(row['avg_recency_days']):.0f}d",
        ])

    return html.Div(
        children=[
            # 4 Customer KPI Cards
            dmc.SimpleGrid(
                cols={"base": 1, "sm": 2, "md": 4},
                spacing="md",
                mb="lg",
                children=[
                    dmc.Paper(
                        p="md",
                        radius="md",
                        withBorder=True,
                        shadow="xs",
                        children=[
                            dmc.Text("Total Registered Buyers", size="xs", c="dimmed", fw=600),
                            dmc.Title(f"{total_custs:,}", order=3),
                            dmc.Text("Unique tracked identities", size="xs", c="dimmed", mt=4),
                        ],
                    ),
                    dmc.Paper(
                        p="md",
                        radius="md",
                        withBorder=True,
                        shadow="xs",
                        children=[
                            dmc.Text("Repeat Buyer Rate", size="xs", c="dimmed", fw=600),
                            dmc.Title(f"{repeat_rate:.1f}%", order=3, c="teal"),
                            dmc.Text(f"{repeat_custs:,} buyers with >= 2 orders", size="xs", c="dimmed", mt=4),
                        ],
                    ),
                    dmc.Paper(
                        p="md",
                        radius="md",
                        withBorder=True,
                        shadow="xs",
                        children=[
                            dmc.Text("Average Customer Lifetime Spend", size="xs", c="dimmed", fw=600),
                            dmc.Title(f"${avg_spend:,.2f}", order=3),
                            dmc.Text("Cumulative net recorded revenue", size="xs", c="dimmed", mt=4),
                        ],
                    ),
                    dmc.Paper(
                        p="md",
                        radius="md",
                        withBorder=True,
                        shadow="xs",
                        children=[
                            dmc.Text("Average Customer Recency", size="xs", c="dimmed", fw=600),
                            dmc.Title(f"{avg_recency:.0f} days", order=3, c="indigo"),
                            dmc.Text("Time elapsed since last invoice", size="xs", c="dimmed", mt=4),
                        ],
                    ),
                ],
            ),
            # Persona Distribution & Recency Curve
            dmc.SimpleGrid(
                cols={"base": 1, "md": 2},
                spacing="lg",
                mb="lg",
                style={"minWidth": 0},
                children=[
                    dmc.Paper(
                        p="lg",
                        radius="md",
                        withBorder=True,
                        shadow="xs",
                        style={"minWidth": 0, "overflow": "hidden"},
                        children=[
                            dmc.Title("RFM Persona Size Distribution", order=4, mb="xs"),
                            dmc.Text("Quantile-scored classification across Recency, Frequency, and Monetary value", size="xs", c="dimmed", mb="md"),
                            dcc.Graph(
                                id="cust-persona-chart",
                                figure=persona_fig,
                                config={"displayModeBar": False},
                                responsive=True,
                                style={"height": "320px", "width": "100%", "minWidth": 0},
                            ),
                        ],
                    ),
                    dmc.Paper(
                        p="lg",
                        radius="md",
                        withBorder=True,
                        shadow="xs",
                        style={"minWidth": 0, "overflow": "hidden"},
                        children=[
                            dmc.Title("Customer Recency Distribution", order=4, mb="xs"),
                            dmc.Text("Count of customers by elapsed days since their latest transaction", size="xs", c="dimmed", mb="md"),
                            dcc.Graph(
                                id="cust-recency-chart",
                                figure=recency_fig,
                                config={"displayModeBar": False},
                                responsive=True,
                                style={"height": "320px", "width": "100%", "minWidth": 0},
                            ),
                        ],
                    ),
                ],
            ),
            # RFM Segment Summary Table
            dmc.Paper(
                p="lg",
                radius="md",
                withBorder=True,
                shadow="xs",
                mb="lg",
                style={"minWidth": 0, "overflow": "hidden"},
                children=[
                    dmc.Title("RFM Customer Persona Scorecard", order=4, mb="xs"),
                    dmc.Text("Aggregate volume, contribution, and engagement statistics across each behavioral persona", size="xs", c="dimmed", mb="md"),
                    html.Div(
                        dmc.Table(
                            data={"head": seg_head, "body": seg_body},
                            striped=True,
                            highlightOnHover=True,
                            withTableBorder=True,
                        ),
                        style={"overflowX": "auto"},
                    ),
                ],
            ),
            # Monthly Cohort Retention Heatmap
            dmc.Paper(
                p="lg",
                radius="md",
                withBorder=True,
                shadow="xs",
                style={"minWidth": 0, "overflow": "hidden"},
                children=[
                    dmc.Title("Monthly Customer Cohort Retention", order=4, mb="xs"),
                    dmc.Text("Percentage of newly acquired buyers in each monthly cohort who returned in subsequent months", size="xs", c="dimmed", mb="md"),
                    dcc.Graph(
                        id="cust-cohort-chart",
                        figure=cohort_fig,
                        config={"displayModeBar": False},
                        responsive=True,
                        style={"height": "320px", "width": "100%", "minWidth": 0},
                    ),
                ],
            ),
        ]
    )
