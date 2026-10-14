"""
Header component for RetailIQ Dash Mantine application.
"""

import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify

from retail_intelligence.dash_state import state


def build_header() -> dmc.Paper:
    """Builds top enterprise navbar with branding, active file status, and quick load actions."""
    filename = state.filename or "No dataset loaded"
    rows_count = len(state.clean_sales_df) if state.clean_sales_df is not None else 0

    return dmc.Paper(
        p="md",
        radius=0,
        withBorder=True,
        shadow="xs",
        style={"backgroundColor": "#FFFFFF", "borderBottom": "1px solid #E2E8F0"},
        children=dmc.Group(
            justify="space-between",
            align="center",
            children=[
                # Brand
                dmc.Group(
                    align="center",
                    gap="sm",
                    children=[
                        dmc.ThemeIcon(
                            DashIconify(icon="tabler:chart-arrows-vertical", width=22),
                            size="lg",
                            radius="md",
                            variant="filled",
                            color="blue",
                        ),
                        html.Div([
                            dmc.Title("RetailIQ", order=3, style={"fontWeight": 700, "letterSpacing": "-0.5px", "color": "#0F172A", "lineHeight": 1.2}),
                            dmc.Text("Business & Customer Intelligence Platform", size="xs", c="dimmed"),
                        ]),
                    ],
                ),
                # Status & Actions
                dmc.Group(
                    gap="md",
                    align="center",
                    children=[
                        html.Div(
                            id="header-dataset-badge-container",
                            children=dmc.Badge(
                                f"Active: {filename} ({rows_count:,} records)",
                                color="teal",
                                variant="light",
                                size="lg",
                                radius="sm",
                            ),
                        ),
                        dmc.Button(
                            "Load Benchmark Dataset",
                            id="btn-load-benchmark",
                            variant="light",
                            color="blue",
                            size="sm",
                            leftSection=DashIconify(icon="tabler:database", width=16),
                        ),
                    ],
                ),
            ],
        ),
    )
