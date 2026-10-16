"""
Product & Geographic Intelligence view for Dash Mantine UI.
Analyzes top performing SKUs, declining demand alerts, country distributions,
and returns impact.
"""

import dash_mantine_components as dmc
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html

from dash_iconify import DashIconify

from retail_intelligence.dash_state import state
from retail_intelligence.metrics import (
    compute_country_breakdown,
    compute_declining_products,
    compute_top_products,
)


def build_top_products_figure(
    sales_df: pd.DataFrame,
    top_n: int = 10,
    by: str = "revenue",
    selected_country: str | None = None,
) -> go.Figure:
    """Builds horizontal bar chart for top products, optionally filtered by country."""
    if sales_df is None or sales_df.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_white", height=320)
        return fig

    df_source = sales_df
    if selected_country and not sales_df.empty:
        df_source = sales_df[sales_df["country"] == selected_country]
        if df_source.empty:
            fig = go.Figure()
            fig.add_annotation(text=f"No products found for {selected_country}", showarrow=False, font=dict(size=14, color="#64748B"))
            fig.update_layout(template="plotly_white", height=320)
            return fig

    top_df = compute_top_products(df_source, top_n=top_n, by=by)
    if top_df.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_white", height=320)
        return fig

    # Reverse so top item is at the top of the chart
    top_df = top_df.iloc[::-1]

    val_col = "revenue" if by == "revenue" else "quantity"
    title_text = "Revenue ($)" if by == "revenue" else "Units Sold"
    color_hex = "#2563EB" if by == "revenue" else "#0D9488"

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=top_df["description"].str[:30],
            x=top_df[val_col],
            orientation="h",
            marker=dict(color=color_hex, opacity=0.88),
            hovertemplate="<b>%{y}</b><br>" + title_text + ": %{x:,.2f}<extra></extra>",
        )
    )

    title_suffix = f" — {selected_country}" if selected_country else ""

    fig.update_layout(
        template="plotly_white",
        height=320,
        margin=dict(l=150, r=30, t=10, b=35),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title=title_text + title_suffix, showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(title="", tickfont=dict(size=11)),
    )
    return fig


def build_country_figure(country_df: pd.DataFrame, selected_country: str | None = None) -> go.Figure:
    """Builds country share donut chart with PowerBI-style slice explosion / highlighting."""
    if country_df is None or country_df.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_white", height=280)
        return fig

    top_countries = country_df.head(6).copy()
    other_rev = country_df["revenue"].iloc[6:].sum() if len(country_df) > 6 else 0.0

    if other_rev > 0:
        top_countries = pd.concat([
            top_countries,
            pd.DataFrame([{"country": "Other Countries", "revenue": other_rev}]),
        ], ignore_index=True)

    # Pull out selected slice if clicked
    pull_values = [0.12 if c == selected_country else 0 for c in top_countries["country"]]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=top_countries["country"],
                values=top_countries["revenue"],
                hole=0.55,
                pull=pull_values,
                marker=dict(colors=["#2563EB", "#0D9488", "#6366F1", "#F59E0B", "#EC4899", "#8B5CF6", "#94A3B8"]),
                textinfo="label+percent",
                insidetextorientation="radial",
                hovertemplate="<b>%{label}</b><br>Revenue: $%{value:,.2f} (%{percent})<br><i>Click to cross-filter page</i><extra></extra>",
            )
        ]
    )
    fig.update_layout(
        template="plotly_white",
        height=280,
        margin=dict(l=20, r=20, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        clickmode="event+select",
    )
    return fig


def build_declining_products_table(sales_df: pd.DataFrame, selected_country: str | None = None) -> html.Div:
    """Builds declining demand table, optionally filtered by country."""
    df_source = sales_df
    if selected_country and not sales_df.empty:
        df_source = sales_df[sales_df["country"] == selected_country]

    declining_df = compute_declining_products(df_source, min_orders=2 if selected_country else 3, top_n=8)
    declining_head = ["Product ID", "Description", "Earlier Rev ($)", "Recent Rev ($)", "Change (%)"]
    declining_body = []
    for _, row in declining_df.iterrows():
        declining_body.append([
            str(row["product_id"]),
            str(row["description"])[:35],
            f"${float(row['earlier_revenue']):,.2f}",
            f"${float(row['recent_revenue']):,.2f}",
            f"{float(row['pct_change']):.1f}%",
        ])

    return html.Div(
        dmc.Table(
            data={"head": declining_head, "body": declining_body},
            striped=True,
            highlightOnHover=True,
            withTableBorder=True,
        ),
        style={"overflowX": "auto"},
    )


def build_country_summary_table(country_df: pd.DataFrame, selected_country: str | None = None) -> html.Div:
    """Builds country revenue share table."""
    country_head = ["Country", "Revenue ($)", "Orders", "Share (%)"]
    country_body = []
    for _, row in country_df.head(8).iterrows():
        country_body.append([
            str(row["country"]),
            f"${float(row['revenue']):,.2f}",
            f"{int(row['orders']):,}",
            f"{float(row['pct_of_total_revenue']):.1f}%",
        ])

    return html.Div(
        dmc.Table(
            data={"head": country_head, "body": country_body},
            striped=True,
            highlightOnHover=True,
            withTableBorder=True,
        ),
        style={"overflowX": "auto"},
    )


def build_product_returns_table(returns_df: pd.DataFrame, selected_country: str | None = None) -> html.Div:
    """Builds product refund audit table, optionally filtered by country."""
    ret_source = returns_df
    if selected_country and not returns_df.empty and "country" in returns_df.columns:
        ret_source = returns_df[returns_df["country"] == selected_country]

    returned_items_body = []
    if not ret_source.empty:
        ret_grp = ret_source.groupby(["product_id", "description"]).agg(
            returned_qty=("quantity", "sum"),
            returned_amount=("total_amount", "sum"),
        ).reset_index().sort_values(by="returned_amount", ascending=False).head(5)

        for _, row in ret_grp.iterrows():
            returned_items_body.append([
                str(row["product_id"]),
                str(row["description"])[:35],
                f"{int(row['returned_qty']):,}",
                f"${float(row['returned_amount']):,.2f}",
            ])
    ret_head = ["Product ID", "Description", "Units Returned", "Refund Value ($)"]

    return html.Div(
        dmc.Table(
            data={"head": ret_head, "body": returned_items_body},
            striped=True,
            highlightOnHover=True,
            withTableBorder=True,
        ),
        style={"overflowX": "auto"},
    )


def build_product_view() -> html.Div:
    """Renders the product & geographic intelligence tab with full PowerBI-style cross-filtering."""
    sales_df = state.clean_sales_df if state.clean_sales_df is not None else pd.DataFrame()
    returns_df = state.returns_df if state.returns_df is not None else pd.DataFrame()

    top_fig = build_top_products_figure(sales_df, top_n=10, by="revenue")
    country_df = compute_country_breakdown(sales_df)
    country_fig = build_country_figure(country_df)
    declining_table = build_declining_products_table(sales_df)
    country_table = build_country_summary_table(country_df)
    returns_table = build_product_returns_table(returns_df)

    return html.Div(
        children=[
            # Cross-Filtering In-Memory State
            dcc.Store(id="product-filter-country-store", data=None),

            # Top SKUs Section
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
                            dmc.Group(
                                gap="xs",
                                children=[
                                    html.Div([
                                        dmc.Title("Top Performing SKUs", order=4),
                                        dmc.Text("Volume and revenue distribution across best-selling catalog items", size="xs", c="dimmed"),
                                    ]),
                                    html.Div(id="product-top-filter-badge"),
                                ],
                            ),
                            dmc.Group(
                                gap="sm",
                                children=[
                                    dmc.SegmentedControl(
                                        id="product-sort-metric",
                                        value="revenue",
                                        data=[
                                            {"label": "Rank by Revenue", "value": "revenue"},
                                            {"label": "Rank by Quantity", "value": "quantity"},
                                        ],
                                        size="sm",
                                        radius="md",
                                    ),
                                    dmc.Tooltip(
                                        label="Reset Product View",
                                        children=dmc.ActionIcon(
                                            DashIconify(icon="tabler:rotate-2", width=16),
                                            id="btn-reset-product-top",
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
                        id="product-top-chart",
                        figure=top_fig,
                        config={"displayModeBar": False},
                        responsive=True,
                        style={"height": "320px", "width": "100%", "minWidth": 0},
                    ),
                ],
            ),
            # 2 Columns: Declining Products & Geographic Breakdown
            dmc.SimpleGrid(
                cols={"base": 1, "md": 2},
                spacing="lg",
                mb="lg",
                style={"minWidth": 0},
                children=[
                    # Declining Products Card
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
                                    dmc.Title("Declining Demand Alert", order=4),
                                    dmc.Badge("Anomaly Detection", color="orange", variant="light", radius="sm"),
                                ],
                            ),
                            dmc.Text("Products with highest revenue drop between early and recent halves", size="xs", c="dimmed", mb="md"),
                            html.Div(
                                id="product-declining-table-container",
                                children=declining_table,
                            ),
                        ],
                    ),
                    # Geographic Distribution Card
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
                                            dmc.Title("Geographic Revenue Distribution", order=4),
                                            html.Div(id="product-country-filter-badge"),
                                        ],
                                    ),
                                    dmc.Tooltip(
                                        label="Reset Country Filter",
                                        children=dmc.ActionIcon(
                                            DashIconify(icon="tabler:rotate-2", width=16),
                                            id="btn-reset-product-country",
                                            variant="light",
                                            color="gray",
                                            size="sm",
                                            radius="md",
                                        ),
                                    ),
                                ],
                            ),
                            dmc.Text("Touch / click any country slice to cross-filter products and alerts", size="xs", c="dimmed", mb="sm"),
                            dcc.Graph(
                                id="product-country-chart",
                                figure=country_fig,
                                config={"displayModeBar": False},
                                responsive=True,
                                style={"height": "280px", "width": "100%", "minWidth": 0},
                            ),
                            html.Div(
                                id="product-country-table-container",
                                children=country_table,
                            ),
                        ],
                    ),
                ],
            ),
            # Isolated Returns Summary Card
            dmc.Paper(
                p="lg",
                radius="md",
                withBorder=True,
                shadow="xs",
                children=[
                    dmc.Group(
                        justify="space-between",
                        align="center",
                        mb="xs",
                        children=[
                            dmc.Title("High Return Products Audit", order=4),
                            dmc.Badge("Quality & Refund Tracking", color="red", variant="light", radius="sm"),
                        ],
                    ),
                    dmc.Text("Items generating the highest refund claims and returned quantities", size="xs", c="dimmed", mb="md"),
                    html.Div(
                        id="product-return-table-container",
                        children=returns_table,
                    ),
                ],
            ),
        ]
    )
