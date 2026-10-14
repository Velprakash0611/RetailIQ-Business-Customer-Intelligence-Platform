"""
Customer Prioritisation & Action Queue view for Dash Mantine UI.
Blends calibrated inactivity risk with lifetime customer value into a 4-quadrant
matrix, interactive 2x2 scatter, filterable queue, and customer inspector.
"""

import dash_mantine_components as dmc
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html
from dash_iconify import DashIconify

from retail_intelligence.dash_state import state
from retail_intelligence.prioritisation import (
    compute_prioritisation_summary,
)


def build_scatter_matrix_figure(
    df: pd.DataFrame,
    risk_threshold: float,
    val_cutoff: float,
) -> go.Figure:
    """Builds 2x2 interactive Risk vs Value scatter matrix with quadrant crosshairs."""
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_white", height=380)
        return fig

    color_map = {
        "High Risk, High Value": "#EF4444",   # Red
        "High Risk, Lower Value": "#F97316",  # Orange
        "Low Risk, High Value": "#10B981",    # Emerald
        "Low Risk, Lower Value": "#94A3B8",   # Slate
    }

    fig = go.Figure()

    for group_name, group_df in df.groupby("priority_group"):
        c = color_map.get(group_name, "#64748B")
        fig.add_trace(
            go.Scatter(
                x=group_df["inactivity_prob_90d"] * 100.0,
                y=group_df["total_spend"],
                mode="markers",
                name=group_name,
                marker=dict(size=7, color=c, opacity=0.82),
                hovertemplate=(
                    "<b>Customer %{customdata[0]}</b><br>"
                    "Inactivity Risk: %{x:.1f}%<br>"
                    "Lifetime Spend: $%{y:,.2f}<br>"
                    "Orders: %{customdata[1]} | Recency: %{customdata[2]}d<extra></extra>"
                ),
                customdata=group_df[["customer_id", "frequency", "recency_days"]].values,
            )
        )

    # Threshold crosshairs
    fig.add_vline(
        x=risk_threshold * 100.0,
        line=dict(color="#64748B", dash="dash", width=1.5),
        annotation_text=f"Risk Threshold ({risk_threshold*100:.0f}%)",
        annotation_position="top left",
    )
    fig.add_hline(
        y=val_cutoff,
        line=dict(color="#64748B", dash="dash", width=1.5),
        annotation_text=f"Value Cutoff (${val_cutoff:,.0f})",
        annotation_position="bottom right",
    )

    fig.update_layout(
        template="plotly_white",
        height=380,
        margin=dict(l=60, r=20, t=25, b=45),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="Predicted Inactivity Probability (%)", range=[0, 102], showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(title="Customer Lifetime Spend ($)", showgrid=True, gridcolor="#E2E8F0"),
    )
    return fig


def build_prioritisation_view() -> html.Div:
    """Renders the 4-quadrant prioritisation matrix and actionable customer list."""
    prioritised_df = state.prioritised_df if state.prioritised_df is not None else pd.DataFrame()
    summary_df = compute_prioritisation_summary(prioritised_df)

    risk_thresh = state.risk_threshold
    val_cutoff_pct = state.value_cutoff_pct
    val_cutoff_amount = float(prioritised_df["total_spend"].quantile(val_cutoff_pct / 100.0)) if not prioritised_df.empty else 500.0

    scatter_fig = build_scatter_matrix_figure(prioritised_df, risk_thresh, val_cutoff_amount)

    # Extract quadrant counts
    quad_stats = {}
    if not summary_df.empty:
        for _, r in summary_df.iterrows():
            quad_stats[r["priority_group"]] = {
                "count": int(r["customer_count"]),
                "spend": float(r["total_spend"]),
                "action": r["suggested_action"],
            }

    vip_at_risk = quad_stats.get("High Risk, High Value", {"count": 0, "spend": 0.0, "action": "Review first for targeted retention."})
    churn_base = quad_stats.get("High Risk, Lower Value", {"count": 0, "spend": 0.0, "action": "Consider automated re-engagement."})
    vip_loyals = quad_stats.get("Low Risk, High Value", {"count": 0, "spend": 0.0, "action": "Focus on loyalty and repeat purchases."})
    routine = quad_stats.get("Low Risk, Lower Value", {"count": 0, "spend": 0.0, "action": "Continue routine monitoring."})

    # Prepare top 10 queue table rows
    table_head = ["Rank", "Customer ID", "Priority Score", "Quadrant", "Risk Prob", "Spend ($)", "Orders", "Recency"]
    table_body = []
    top_queue = prioritised_df.head(10) if not prioritised_df.empty else pd.DataFrame()
    for idx, row in top_queue.iterrows():
        table_body.append([
            f"#{idx + 1}",
            str(row["customer_id"]),
            f"{float(row['priority_score']):.1f}",
            str(row["priority_group"]),
            f"{float(row['inactivity_prob_90d'])*100.0:.1f}%",
            f"${float(row['total_spend']):,.2f}",
            f"{int(row['frequency']):,}",
            f"{int(row['recency_days']):,}d",
        ])

    return html.Div(
        children=[
            # 4 Quadrant Cards
            dmc.SimpleGrid(
                cols={"base": 1, "sm": 2, "md": 4},
                spacing="md",
                mb="lg",
                children=[
                    # Quadrant 1: VIP At-Risk
                    dmc.Paper(
                        p="md",
                        radius="md",
                        withBorder=True,
                        shadow="xs",
                        style={"borderLeft": "4px solid #EF4444"},
                        children=[
                            dmc.Group(
                                justify="space-between",
                                align="center",
                                mb="xs",
                                children=[
                                    dmc.Text("VIP At-Risk", size="xs", fw=700, c="red"),
                                    dmc.Badge("Urgency 1", color="red", variant="light", size="sm", radius="sm"),
                                ],
                            ),
                            dmc.Title(f"{vip_at_risk['count']:,} customers", order=4),
                            dmc.Text(f"${vip_at_risk['spend']:,.2f} revenue at risk", size="xs", c="dimmed", mt=2),
                            dmc.Text(vip_at_risk["action"], size="xs", fw=500, mt=6),
                        ],
                    ),
                    # Quadrant 2: Churning Base
                    dmc.Paper(
                        p="md",
                        radius="md",
                        withBorder=True,
                        shadow="xs",
                        style={"borderLeft": "4px solid #F97316"},
                        children=[
                            dmc.Group(
                                justify="space-between",
                                align="center",
                                mb="xs",
                                children=[
                                    dmc.Text("Churning Base", size="xs", fw=700, c="orange"),
                                    dmc.Badge("Urgency 2", color="orange", variant="light", size="sm", radius="sm"),
                                ],
                            ),
                            dmc.Title(f"{churn_base['count']:,} customers", order=4),
                            dmc.Text(f"${churn_base['spend']:,.2f} revenue", size="xs", c="dimmed", mt=2),
                            dmc.Text(churn_base["action"], size="xs", fw=500, mt=6),
                        ],
                    ),
                    # Quadrant 3: VIP Loyals
                    dmc.Paper(
                        p="md",
                        radius="md",
                        withBorder=True,
                        shadow="xs",
                        style={"borderLeft": "4px solid #10B981"},
                        children=[
                            dmc.Group(
                                justify="space-between",
                                align="center",
                                mb="xs",
                                children=[
                                    dmc.Text("VIP Loyals", size="xs", fw=700, c="teal"),
                                    dmc.Badge("Urgency 3", color="teal", variant="light", size="sm", radius="sm"),
                                ],
                            ),
                            dmc.Title(f"{vip_loyals['count']:,} customers", order=4),
                            dmc.Text(f"${vip_loyals['spend']:,.2f} revenue", size="xs", c="dimmed", mt=2),
                            dmc.Text(vip_loyals["action"], size="xs", fw=500, mt=6),
                        ],
                    ),
                    # Quadrant 4: Routine Shoppers
                    dmc.Paper(
                        p="md",
                        radius="md",
                        withBorder=True,
                        shadow="xs",
                        style={"borderLeft": "4px solid #94A3B8"},
                        children=[
                            dmc.Group(
                                justify="space-between",
                                align="center",
                                mb="xs",
                                children=[
                                    dmc.Text("Routine Shoppers", size="xs", fw=700, c="dimmed"),
                                    dmc.Badge("Urgency 4", color="gray", variant="light", size="sm", radius="sm"),
                                ],
                            ),
                            dmc.Title(f"{routine['count']:,} customers", order=4),
                            dmc.Text(f"${routine['spend']:,.2f} revenue", size="xs", c="dimmed", mt=2),
                            dmc.Text(routine["action"], size="xs", fw=500, mt=6),
                        ],
                    ),
                ],
            ),
            # Threshold Configuration & Strategy Controls
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
                                dmc.Title("Prioritisation Strategy Tuning", order=4),
                                dmc.Text("Configure risk decision thresholds, monetary cutoff percentiles, and formula weights", size="xs", c="dimmed"),
                            ]),
                            dmc.Button(
                                "Recalculate Priorities",
                                id="btn-recalculate-priorities",
                                variant="light",
                                color="blue",
                                leftSection=DashIconify(icon="tabler:adjustments", width=18),
                            ),
                        ],
                    ),
                    dmc.SimpleGrid(
                        cols={"base": 1, "sm": 3},
                        spacing="lg",
                        children=[
                            html.Div([
                                dmc.Text("Inactivity Risk Cutoff", size="sm", fw=600),
                                dmc.Text("Flagged as High Risk above this probability", size="xs", c="dimmed", mb="xs"),
                                dcc.Slider(
                                    id="slider-risk-threshold",
                                    min=0.30,
                                    max=0.80,
                                    step=0.05,
                                    value=risk_thresh,
                                    marks={0.3: "30%", 0.5: "50%", 0.7: "70%"},
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),
                            ]),
                            html.Div([
                                dmc.Text("High-Value Spend Cutoff Percentile", size="sm", fw=600),
                                dmc.Text(f"Top {100 - int(val_cutoff_pct)}% spenders deemed High Value (${val_cutoff_amount:,.0f})", size="xs", c="dimmed", mb="xs"),
                                dcc.Slider(
                                    id="slider-val-cutoff",
                                    min=50,
                                    max=90,
                                    step=5,
                                    value=val_cutoff_pct,
                                    marks={50: "Top 50%", 70: "Top 30%", 90: "Top 10%"},
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),
                            ]),
                            html.Div([
                                dmc.Text("Composite Weight: Risk vs Value", size="sm", fw=600),
                                dmc.Text(f"Risk Weight: {state.risk_weight:.2f} | Value: {1.0 - state.risk_weight:.2f}", size="xs", c="dimmed", mb="xs"),
                                dcc.Slider(
                                    id="slider-risk-weight",
                                    min=0.20,
                                    max=0.80,
                                    step=0.05,
                                    value=state.risk_weight,
                                    marks={0.2: "Value-heavy", 0.5: "Balanced", 0.8: "Risk-heavy"},
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),
                            ]),
                        ],
                    ),
                ],
            ),
            # 2x2 Risk vs Value Scatter Matrix
            dmc.Paper(
                p="lg",
                radius="md",
                withBorder=True,
                shadow="xs",
                mb="lg",
                children=[
                    dmc.Title("2x2 Risk vs. Value Scatter Matrix", order=4, mb="xs"),
                    dmc.Text("Interactive distribution of individual customers with boundary crosshairs", size="xs", c="dimmed", mb="md"),
                    dcc.Graph(
                        id="prioritisation-scatter-chart",
                        figure=scatter_fig,
                        config={"displayModeBar": False, "responsive": True},
                    ),
                ],
            ),
            # Action Queue Table & Download
            dmc.Paper(
                p="lg",
                radius="md",
                withBorder=True,
                shadow="xs",
                children=[
                    dmc.Group(
                        justify="space-between",
                        align="center",
                        mb="md",
                        children=[
                            html.Div([
                                dmc.Title("Top Priority Contact Queue", order=4),
                                dmc.Text("Actionable ranking ordered by quadrant urgency and composite priority score", size="xs", c="dimmed"),
                            ]),
                            dmc.Group(
                                children=[
                                    dmc.Button(
                                        "Download Action Queue (CSV)",
                                        id="btn-download-queue-csv",
                                        variant="filled",
                                        color="teal",
                                        size="sm",
                                        leftSection=DashIconify(icon="tabler:download", width=18),
                                    ),
                                    dcc.Download(id="download-queue-csv"),
                                ]
                            ),
                        ],
                    ),
                    dmc.Table(
                        id="prioritisation-queue-table",
                        data={"head": table_head, "body": table_body},
                        striped=True,
                        highlightOnHover=True,
                        withTableBorder=True,
                    ),
                ],
            ),
        ]
    )
