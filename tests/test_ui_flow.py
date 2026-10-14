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

