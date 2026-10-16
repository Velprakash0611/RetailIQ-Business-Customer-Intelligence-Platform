import sys
from pathlib import Path

# Ensure root is on sys.path for dash_app import
sys.path.insert(0, str(Path(__file__).parent.parent))

from retail_intelligence.dash_ui.view_landing import build_landing_dataset_status, build_landing_view
from retail_intelligence.dash_ui.header import build_header
from dash_app import toggle_dark_mode, handle_page_navigation


def test_landing_view_renders_empty_state():
    """Verifies landing view renders cleanly when no dataset is loaded."""
    landing_component = build_landing_view()
    assert landing_component is not None


def test_landing_dataset_status_card():
    """Verifies status card displays correctly for empty and loaded states."""
    empty_card = build_landing_dataset_status(is_loaded=False)
    assert empty_card is not None

    loaded_card = build_landing_dataset_status(
        is_loaded=True,
        filename="test_sales.csv",
        row_count=1000,
        customer_count=450,
        net_revenue=54200.50,
        date_span="2023-01-01 to 2023-12-31",
    )
    assert loaded_card is not None


def test_header_renders():
    """Verifies header component renders with navigation and dark mode toggle."""
    header = build_header()
    assert header is not None


def test_dark_mode_toggle_logic():
    """Verifies dark mode toggle switches between light and dark."""
    new_scheme, icon, store_val = toggle_dark_mode(1, "light")
    assert new_scheme == "dark"
    assert icon == "tabler:sun"
    assert store_val == "dark"

    new_scheme2, icon2, store_val2 = toggle_dark_mode(2, "dark")
    assert new_scheme2 == "light"
    assert icon2 == "tabler:moon"
    assert store_val2 == "light"


def test_page_navigation_routing():
    """Verifies page navigation routes between landing and dashboard."""
    landing_style, dash_style, page, modal_opened = handle_page_navigation(0, 0, 0, 0, 0, 0, "landing")
    assert page == "landing"
    assert landing_style == {"display": "block"}
    assert dash_style == {"display": "none"}
    assert modal_opened is False


def test_modal_guard_when_no_data():
    """Verifies clicking dashboard without dataset opens guard modal."""
    from dash_app import state
    state.clean_sales_df = None
    # Simulate user clicking btn-nav-dashboard
    from unittest.mock import patch
    with patch("dash_app.ctx") as mock_ctx:
        mock_ctx.triggered_id = "btn-nav-dashboard"
        landing_style, dash_style, page, modal_opened = handle_page_navigation(0, 1, 0, 0, 0, 0, "landing")
        assert modal_opened is True
        assert page == "landing"


def test_landing_view_contains_permanent_proceed_button():
    """Verifies that btn-proceed-to-dashboard is permanently in landing layout."""
    landing_component = build_landing_view()

    # Recursively find component by id
    def find_id(comp, target_id):
        if getattr(comp, "id", None) == target_id:
            return comp
        children = getattr(comp, "children", None)
        if isinstance(children, list):
            for child in children:
                res = find_id(child, target_id)
                if res is not None:
                    return res
        elif children is not None:
            return find_id(children, target_id)
        return None

    btn = find_id(landing_component, "btn-proceed-to-dashboard")
    assert btn is not None
    assert btn.id == "btn-proceed-to-dashboard"


def test_load_benchmark_unified_reveals_proceed_button():
    """Verifies handle_load_benchmark_unified returns visible proceed button style."""
    from dash_app import handle_load_benchmark_unified, PROCEED_BTN_VISIBLE
    badge, status_card, btn_style, alert, trigger = handle_load_benchmark_unified(1, 0, 0, 0, 0)
    assert btn_style == PROCEED_BTN_VISIBLE
    assert "Active" in getattr(badge, "children", "")


def test_landing_upload_valid_csv():
    """Verifies uploading a valid CSV succeeds and reveals proceed button."""
    import base64
    from dash_app import handle_landing_upload, PROCEED_BTN_VISIBLE

    csv_data = (
        "InvoiceNo,StockCode,Description,Quantity,InvoiceDate,UnitPrice,CustomerID,Country\n"
        "536365,85123A,WHITE HANGING HEART T-LIGHT HOLDER,6,2023-01-01 08:26:00,2.55,17850,United Kingdom\n"
    )
    b64_content = "data:text/csv;base64," + base64.b64encode(csv_data.encode("utf-8")).decode()

    msg, badge, status_card, btn_style, trigger = handle_landing_upload(b64_content, "valid_sales.csv", 0)
    assert btn_style == PROCEED_BTN_VISIBLE
    assert "Active: valid_sales.csv" in getattr(badge, "children", "")


def test_landing_upload_missing_required_column():
    """Verifies uploading CSV missing required column returns schema mismatch and hides proceed button."""
    import base64
    from dash_app import handle_landing_upload, PROCEED_BTN_HIDDEN

    # Missing UnitPrice and Quantity
    csv_data = (
        "InvoiceNo,StockCode,Description,InvoiceDate,CustomerID,Country\n"
        "536365,85123A,WHITE HANGING HEART T-LIGHT HOLDER,2023-01-01 08:26:00,17850,United Kingdom\n"
    )
    b64_content = "data:text/csv;base64," + base64.b64encode(csv_data.encode("utf-8")).decode()

    msg, badge, status_card, btn_style, trigger = handle_landing_upload(b64_content, "bad_sales.csv", 0)
    assert btn_style == PROCEED_BTN_HIDDEN
    assert "Schema Mismatch" in getattr(badge, "children", "")
    assert "Missing essential fields" in getattr(msg, "children", "")


def test_render_tab_content_animated_wrapper():
    """Verifies render_tab_content wraps output in animated div with dynamic key."""
    from dash_app import render_tab_content
    comp = render_tab_content("tab-executive", 1)
    assert getattr(comp, "className", None) == "tab-view-animated"
    assert getattr(comp, "key", None) == "tab-executive-1"


def test_six_canonical_dashboard_tabs():
    """Verifies that main-tabs contains exactly 6 canonical tabs including Audit & Governance."""
    from dash_app import app
    import dash_mantine_components as dmc

    tabs_component = None
    for comp in app.layout._traverse():
        if getattr(comp, "id", None) == "main-tabs":
            tabs_component = comp
            break

    assert tabs_component is not None, "main-tabs not found in app layout"
    # Find dmc.TabsList
    tabs_list = None
    for child in tabs_component.children:
        if isinstance(child, dmc.TabsList):
            tabs_list = child
            break

    assert tabs_list is not None, "dmc.TabsList not found inside main-tabs"
    tab_values = [tab.value for tab in tabs_list.children if hasattr(tab, "value")]
    assert len(tab_values) == 6
    assert tab_values == [
        "tab-executive",
        "tab-product",
        "tab-customer",
        "tab-prediction",
        "tab-prioritisation",
        "tab-report",
    ]


def test_all_views_render_valid_components():
    """Verifies all 6 tab view functions execute and render with graphs and cards."""
    from retail_intelligence.dash_ui.view_executive import build_executive_view
    from retail_intelligence.dash_ui.view_product import build_product_view
    from retail_intelligence.dash_ui.view_customer import build_customer_view
    from retail_intelligence.dash_ui.view_prediction import build_prediction_view
    from retail_intelligence.dash_ui.view_prioritisation import build_prioritisation_view
    from retail_intelligence.dash_ui.view_report import build_report_view

    exec_view = build_executive_view()
    assert exec_view is not None

    prod_view = build_product_view()
    assert prod_view is not None

    cust_view = build_customer_view()
    assert cust_view is not None

    pred_view = build_prediction_view()
    assert pred_view is not None

    prio_view = build_prioritisation_view()
    assert prio_view is not None

    rep_view = build_report_view()
    assert rep_view is not None



