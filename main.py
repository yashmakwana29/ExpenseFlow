"""
ExpenseFlow - Mobile Expense Tracker for Android (Built in Python with Flet)
Main application entry point, mobile router, bottom navigation, and Google Sheets sync engine.
"""
import sys
import types

# Ensure wsgiref is available for google_auth_oauthlib on embedded platforms (Android)
if "wsgiref" not in sys.modules:
    try:
        import wsgiref
        import wsgiref.simple_server
        import wsgiref.util
    except ImportError:
        _w = types.ModuleType("wsgiref")
        _ss = types.ModuleType("wsgiref.simple_server")
        _u = types.ModuleType("wsgiref.util")
        _ss.WSGIServer = type("WSGIServer", (), {})
        _ss.WSGIRequestHandler = type("WSGIRequestHandler", (), {})
        _ss.make_server = lambda *a, **k: None
        _u.request_uri = lambda e: ""
        _w.simple_server = _ss
        _w.util = _u
        sys.modules["wsgiref"] = _w
        sys.modules["wsgiref.simple_server"] = _ss
        sys.modules["wsgiref.util"] = _u

import threading
import flet as ft
import database
import sheets_service
from config import ModernPalette, APP_NAME
from views.dashboard_view import build_dashboard_view
from views.add_expense_view import build_add_expense_view
from views.reports_view import build_reports_view
from views.transactions_view import build_transactions_view
from views.settings_view import build_settings_view
from views.auth_view import build_auth_view

def main(page: ft.Page):
    # Initialize SQLite database
    database.init_db()

    # Mobile Phone Presentation Settings
    page.title = f"{APP_NAME} - Android Tracker"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ModernPalette.BG_DARK
    page.padding = 0

    # Mobile viewport simulation for desktop dev
    try:
        page.window.width = 420
        page.window.height = 780
        page.window.min_width = 360
        page.window.min_height = 560
        page.window.resizable = True
    except Exception:
        pass

    # Navigation State
    current_view_name = "dashboard"
    edit_expense_id = None
    sheets_manager = sheets_service.GoogleSheetsManager()

    # Responsive inner wrapper: max 480px on desktop/tablets, full width on mobile
    responsive_wrapper = ft.Container(
        expand=True,
        alignment=ft.Alignment.TOP_CENTER,
    )

    # Content body container
    body_container = ft.Container(
        expand=True,
        bgcolor=ModernPalette.BG_DARK,
        alignment=ft.Alignment.TOP_CENTER,
        content=responsive_wrapper,
    )

    def handle_page_resize(e=None):
        if page.width and page.width > 520:
            responsive_wrapper.width = 480
        else:
            responsive_wrapper.width = None
        page.update()

    page.on_resize = handle_page_resize

    # ------------------ Google Sheets Sync Logic ------------------

    def perform_background_sync(saved_item=None):
        """Asynchronously syncs unsynced expenses to Google Sheets in background."""
        def sync_worker():
            try:
                count, msg = sheets_manager.sync_all_pending()
                if count > 0:
                    page.show_dialog(
                        ft.SnackBar(
                            content=ft.Text(f"Google Sheets: Synced {count} new expense(s)!"),
                            bgcolor=ModernPalette.SUCCESS,
                        )
                    )
                    # Refresh active screen to update sync badges
                    navigate_to(current_view_name)
            except Exception as e:
                # Silently catch; expense remains safely stored locally
                pass

        threading.Thread(target=sync_worker, daemon=True).start()

    def handle_manual_sync_request():
        """Triggered when user clicks 'Sync Now' in header or settings."""
        def worker():
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Row(
                        spacing=8,
                        tight=True,
                        controls=[
                            ft.ProgressRing(width=16, height=16, stroke_width=2, color=ft.Colors.WHITE),
                            ft.Text("Connecting to Google Sheets..."),
                        ]
                    ),
                    bgcolor=ModernPalette.PRIMARY,
                )
            )
            count, msg = sheets_manager.sync_all_pending()
            has_error = "error" in msg.lower() or "failed" in msg.lower() or "not found" in msg.lower()
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(msg),
                    bgcolor=ModernPalette.DANGER if has_error else ModernPalette.SUCCESS,
                )
            )
            navigate_to(current_view_name)

        threading.Thread(target=worker, daemon=True).start()

    def on_expense_saved(item):
        """Called when a new or edited expense is saved."""
        perform_background_sync(item)

    def on_login_success(user):
        """Called when user successfully logs in or creates an account."""
        page.navigation_bar = nav_bar
        navigate_to("dashboard")

    def on_logout():
        """Called when user logs out from settings."""
        database.set_current_session_user(None)
        page.navigation_bar = None
        navigate_to("auth")
        page.show_dialog(ft.SnackBar(ft.Text("Logged out successfully."), bgcolor=ModernPalette.INFO))

    # ------------------ Router & View Switching ------------------

    def navigate_to(view_name: str, edit_id: int = None):
        nonlocal current_view_name, edit_expense_id
        current_view_name = view_name
        edit_expense_id = edit_id

        # Auth Session Guard
        logged_user = database.get_current_session_user()
        if not logged_user and view_name != "auth":
            view_name = "auth"
            current_view_name = "auth"

        if view_name == "auth":
            page.navigation_bar = None
            responsive_wrapper.content = build_auth_view(
                page=page,
                on_login_success=on_login_success,
            )
        else:
            page.navigation_bar = nav_bar
            # Update Navigation Bar selected index
            index_map = {
                "dashboard": 0,
                "add_expense": 1,
                "reports": 2,
                "transactions": 3,
                "settings": 4,
            }
            if view_name in index_map and nav_bar.selected_index != index_map[view_name]:
                nav_bar.selected_index = index_map[view_name]

            # Render corresponding view
            if view_name == "dashboard":
                responsive_wrapper.content = build_dashboard_view(
                    page=page,
                    on_navigate=navigate_to,
                    on_sync_request=handle_manual_sync_request,
                )
            elif view_name == "add_expense":
                responsive_wrapper.content = build_add_expense_view(
                    page=page,
                    on_navigate=navigate_to,
                    on_expense_saved=on_expense_saved,
                    edit_id=edit_expense_id,
                )
            elif view_name == "reports":
                responsive_wrapper.content = build_reports_view(
                    page=page,
                    on_navigate=navigate_to,
                )
            elif view_name == "transactions":
                responsive_wrapper.content = build_transactions_view(
                    page=page,
                    on_navigate=navigate_to,
                    on_edit_request=lambda eid: navigate_to("add_expense", edit_id=eid),
                )
            elif view_name == "settings":
                responsive_wrapper.content = build_settings_view(
                    page=page,
                    on_navigate=navigate_to,
                    on_sync_request=handle_manual_sync_request,
                    on_logout=on_logout,
                )

        if page.width and page.width > 520:
            responsive_wrapper.width = 480
        else:
            responsive_wrapper.width = None

        page.update()

    # ------------------ Bottom Navigation Bar ------------------

    def on_nav_change(e):
        idx = e.control.selected_index
        routes = ["dashboard", "add_expense", "reports", "transactions", "settings"]
        if 0 <= idx < len(routes):
            navigate_to(routes[idx])

    nav_bar = ft.NavigationBar(
        selected_index=0,
        on_change=on_nav_change,
        bgcolor="#0F172A",
        indicator_color="#312E81",
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.DASHBOARD_OUTLINED,
                selected_icon=ft.Icons.DASHBOARD_ROUNDED,
                label="Home",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                selected_icon=ft.Icons.ADD_CIRCLE,
                label="Add",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.INSIGHTS_OUTLINED,
                selected_icon=ft.Icons.INSIGHTS,
                label="Reports",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.RECEIPT_LONG_OUTLINED,
                selected_icon=ft.Icons.RECEIPT_LONG,
                label="History",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS,
                label="Settings",
            ),
        ]
    )

    page.add(body_container)

    # Initial page render: check if user is logged in
    initial_user = database.get_current_session_user()
    if initial_user:
        page.navigation_bar = nav_bar
        navigate_to("dashboard")
    else:
        page.navigation_bar = None
        navigate_to("auth")

    # If first launch with 0 items, seed demo data for instant delight
    if len(database.get_expenses(limit=1)) == 0:
        database.seed_sample_data()

if __name__ == "__main__":
    # Support Flet 1.0 (ft.run) and backwards compatible (ft.app)
    if hasattr(ft, "run"):
        ft.run(main)
    else:
        ft.app(target=main)
