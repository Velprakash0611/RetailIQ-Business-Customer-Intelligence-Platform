"""
Header component for RetailIQ Dash Mantine application.
Enterprise navbar with branding, page navigation, active dataset status, and dark mode toggle.
"""

import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify

from retail_intelligence.dash_state import state


def build_header() -> dmc.Paper:
    """Builds top enterprise navbar with branding, active file status, and quick load actions."""
    has_data = state.clean_sales_df is not None and not state.clean_sales_df.empty
    filename = state.filename or "No dataset loaded"
    rows_count = len(state.clean_sales_df) if has_data else 0

    badge_component = (
        dmc.Badge(
            f"Active: {filename} ({rows_count:,} records)",
            color="teal",
            variant="light",
            size="lg",
            radius="sm",
        )
        if has_data
        else dmc.Badge(
            "No dataset loaded",
            color="gray",
            variant="light",
            size="lg",
            radius="sm",
        )
    )

    return dmc.Paper(
        p="md",
        radius=0,
        withBorder=True,
        shadow="xs",
        children=dmc.Group(
            justify="space-between",
            align="center",
            children=[
                # Brand (Clickable to return to Landing)
                dmc.UnstyledButton(
                    id="header-brand-button",
                    children=dmc.Group(
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
                                dmc.Title("RetailIQ", order=3, style={"fontWeight": 700, "letterSpacing": "-0.5px", "lineHeight": 1.2}),
                                dmc.Text("Business & Customer Intelligence Platform", size="xs", c="dimmed"),
                            ]),
                        ],
                    ),
                ),
                # Navigation & Actions
                dmc.Group(
                    gap="sm",
                    align="center",
                    children=[
                        # Page navigation buttons
                        dmc.Button(
                            "Home",
                            id="btn-nav-landing",
                            variant="subtle",
                            color="gray",
                            size="sm",
                            leftSection=DashIconify(icon="tabler:home", width=16),
                        ),
                        dmc.Button(
                            "Dashboard",
                            id="btn-nav-dashboard",
                            variant="subtle",
                            color="blue",
                            size="sm",
                            leftSection=DashIconify(icon="tabler:layout-dashboard", width=16),
                        ),
                        # Dataset Badge
                        html.Div(
                            id="header-dataset-badge-container",
                            children=badge_component,
                        ),
                        # Load Demo Button
                        dmc.Button(
                            "Load Demo Dataset",
                            id="btn-load-benchmark",
                            variant="light",
                            color="blue",
                            size="sm",
                            leftSection=DashIconify(icon="tabler:database", width=16),
                        ),
                        # Dark Mode Toggle Button at Top Right Corner
                        dmc.Tooltip(
                            label="Toggle Light / Dark Mode",
                            children=dmc.ActionIcon(
                                DashIconify(id="color-scheme-icon", icon="tabler:moon", width=18),
                                id="color-scheme-toggle",
                                variant="default",
                                size="lg",
                                radius="md",
                            ),
                        ),
                    ],
                ),
            ],
        ),
    )
