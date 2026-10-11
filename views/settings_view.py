"""
Settings View for ExpenseFlow.
Configures Google Sheets synchronization, Service Account credentials,
monthly budget limits, currency symbols, and demo data utilities.
"""
import os
import flet as ft
import database
import sheets_service
from config import CURRENCIES, ModernPalette, APP_NAME, APP_VERSION, DEVELOPER_INFO

def build_settings_view(page: ft.Page, on_navigate, on_sync_request, on_logout=None) -> ft.Control:
    """Builds the Settings & Google Sheets configuration screen."""
    
    mgr = sheets_service.GoogleSheetsManager()
    service_email = mgr.get_service_account_email()
    has_creds = bool(service_email)
    saved_sheet_name = database.get_setting("sheet_name", "ExpenseFlow Tracker & Reports")
    saved_currency = database.get_setting("currency_symbol", "₹")
    saved_budget = database.get_setting("monthly_budget", "25000")
    last_sync = database.get_setting("last_sync_time", "Never")
    sheet_url = database.get_setting("sheet_url", "")

    # 0. Account & Security Profile Section
    current_user = database.get_current_session_user()
    user_display = current_user["full_name"] if current_user and current_user.get("full_name") else (current_user["username"] if current_user else "Administrator")
    username_display = current_user["username"] if current_user else "admin"

    def open_change_password_dialog(_):
        old_pwd = ft.TextField(
            label="Current Password",
            password=True,
            can_reveal_password=True,
            filled=True,
            bgcolor=ModernPalette.SURFACE_DARK,
        )
        new_pwd = ft.TextField(
            label="New Password",
            password=True,
            can_reveal_password=True,
            filled=True,
            bgcolor=ModernPalette.SURFACE_DARK,
        )
        confirm_pwd = ft.TextField(
            label="Confirm New Password",
            password=True,
            can_reveal_password=True,
            filled=True,
            bgcolor=ModernPalette.SURFACE_DARK,
        )

        def save_new_password(_):
            if not old_pwd.value or not new_pwd.value:
                page.show_dialog(ft.SnackBar(ft.Text("Please fill all password fields!"), bgcolor=ModernPalette.DANGER))
                return
            if new_pwd.value != confirm_pwd.value:
                page.show_dialog(ft.SnackBar(ft.Text("New passwords do not match!"), bgcolor=ModernPalette.DANGER))
                return

            uid = current_user["id"] if current_user else 1
            ok, msg = database.change_user_password(uid, old_pwd.value, new_pwd.value)
            if ok:
                page.pop_dialog()
                page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor=ModernPalette.SUCCESS))
            else:
                page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor=ModernPalette.DANGER))

        dlg = ft.AlertDialog(
            title=ft.Text("Change Password", weight=ft.FontWeight.BOLD),
            content=ft.Column(
                tight=True,
                spacing=12,
                controls=[
                    ft.Text(f"Account: @{username_display}", size=12, color=ModernPalette.TEXT_MUTED),
                    old_pwd,
                    new_pwd,
                    confirm_pwd,
                ]
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton("Update Password", on_click=save_new_password, style=ft.ButtonStyle(bgcolor=ModernPalette.PRIMARY)),
            ]
        )
        page.show_dialog(dlg)

    def handle_logout(_):
        def confirm_logout(_):
            page.pop_dialog()
            database.set_current_session_user(None)
            if on_logout:
                on_logout()
            else:
                on_navigate("auth")

        confirm_dlg = ft.AlertDialog(
            title=ft.Text("Log Out", weight=ft.FontWeight.BOLD),
            content=ft.Text(f"Are you sure you want to log out of '@{username_display}'?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton(
                    "Log Out",
                    style=ft.ButtonStyle(bgcolor=ModernPalette.DANGER),
                    on_click=confirm_logout,
                )
            ]
        )
        page.show_dialog(confirm_dlg)

    account_section = ft.Container(
        bgcolor=ModernPalette.SURFACE_DARK,
        border_radius=16,
        padding=16,
        border=ft.Border.all(1, ModernPalette.CARD_BORDER),
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=10,
                            controls=[
                                ft.Container(
                                    content=ft.Icon(ft.Icons.PERSON_ROUNDED, color=ft.Colors.WHITE, size=20),
                                    bgcolor=ModernPalette.PRIMARY,
                                    border_radius=12,
                                    padding=8,
                                ),
                                ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Row(
                                            spacing=6,
                                            controls=[
                                                ft.Text(user_display, size=14, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                                                ft.Container(
                                                    content=ft.Text(
                                                        "ADMIN" if (current_user and current_user.get("role") == "admin") else "USER",
                                                        size=9,
                                                        weight=ft.FontWeight.BOLD,
                                                        color=ft.Colors.WHITE
                                                    ),
                                                    bgcolor=ModernPalette.WARNING if (current_user and current_user.get("role") == "admin") else ModernPalette.PRIMARY,
                                                    border_radius=6,
                                                    padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                                ),
                                            ]
                                        ),
                                        ft.Text(f"@{username_display} • {current_user.get('email', 'No Email') if current_user else ''}", size=11, color=ModernPalette.TEXT_MUTED),
                                    ]
                                )
                            ]
                        ),
                        ft.Container(
                            content=ft.Text("Active", size=10, weight=ft.FontWeight.BOLD, color=ModernPalette.SUCCESS),
                            bgcolor="#132E27",
                            border=ft.Border.all(1, ModernPalette.SUCCESS),
                            border_radius=10,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                        )
                    ]
                ),
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.OutlinedButton(
                            "Change Password",
                            icon=ft.Icons.LOCK_RESET_ROUNDED,
                            on_click=open_change_password_dialog,
                        ),
                        ft.OutlinedButton(
                            "Log Out",
                            icon=ft.Icons.LOGOUT_ROUNDED,
                            style=ft.ButtonStyle(color=ModernPalette.DANGER),
                            on_click=handle_logout,
                        ),
                    ]
                )
            ]
        )
    )

    # 1. MySQL Database Connection Card
    db_test_info = database.test_mysql_connection()
    is_db_connected = db_test_info["success"]

    def handle_test_mysql(_):
        res = database.test_mysql_connection()
        dlg = ft.AlertDialog(
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE if res["success"] else ft.Icons.ERROR_OUTLINE,
                        color=ModernPalette.SUCCESS if res["success"] else ModernPalette.DANGER,
                    ),
                    ft.Text("MySQL Connection Diagnostic", weight=ft.FontWeight.BOLD),
                ]
            ),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.Text(f"Status: {'CONNECTED' if res['success'] else 'FAILED'}", weight=ft.FontWeight.BOLD, color=ModernPalette.SUCCESS if res["success"] else ModernPalette.DANGER),
                    ft.Text(f"Server Host: {res.get('host', 'localhost:3306')}", size=12),
                    ft.Text(f"Database: {res.get('database', 'expenseflow_db')}", size=12),
                    ft.Text(f"Username: {res.get('user', 'root')}", size=12),
                    ft.Text(f"MySQL Version: {res.get('version', 'Unknown')}", size=12),
                    ft.Divider(color=ModernPalette.CARD_BORDER),
                    ft.Text(f"Total Expenses in DB: {res.get('expenses_count', 0)}", size=12),
                    ft.Text(f"Synced with Google Sheets: {res.get('synced_count', 0)}", size=12),
                    ft.Text(f"Pending Sync: {res.get('unsynced_count', 0)}", size=12),
                    ft.Text(f"Registered Users: {res.get('users_count', 0)}", size=12),
                    ft.Text(f"Categories: {res.get('categories_count', 0)}", size=12),
                ]
            ),
            actions=[
                ft.TextButton("Close", on_click=lambda _: page.pop_dialog())
            ]
        )
        page.show_dialog(dlg)

    def handle_sync_db_to_sheets(_):
        page.show_dialog(
            ft.SnackBar(
                content=ft.Row(
                    spacing=8,
                    tight=True,
                    controls=[
                        ft.ProgressRing(width=16, height=16, stroke_width=2, color=ft.Colors.WHITE),
                        ft.Text("Synchronizing DB & Google Sheets (2-Way)..."),
                    ]
                ),
                bgcolor=ModernPalette.PRIMARY,
            )
        )
        pushed, pulled, msg = mgr.sync_bidirectional()
        has_error = "error" in msg.lower() or "failed" in msg.lower()
        page.show_dialog(
            ft.SnackBar(
                content=ft.Text(msg),
                bgcolor=ModernPalette.DANGER if has_error else ModernPalette.SUCCESS,
            )
        )
        page.update()

    mysql_status_card = ft.Container(
        bgcolor=ModernPalette.SURFACE_DARK,
        border_radius=16,
        padding=16,
        border=ft.Border.all(1, ModernPalette.SUCCESS if is_db_connected else ModernPalette.WARNING),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(
                                    ft.Icons.STORAGE_ROUNDED,
                                    color=ModernPalette.SUCCESS if is_db_connected else ModernPalette.WARNING,
                                    size=22,
                                ),
                                ft.Text(
                                    "MySQL Database: Connected" if is_db_connected else "MySQL: Offline Fallback",
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                    color=ModernPalette.TEXT_PRIMARY,
                                ),
                            ]
                        ),
                        ft.Container(
                            content=ft.Text(
                                "Live DB" if is_db_connected else "Offline",
                                size=10,
                                weight=ft.FontWeight.BOLD,
                                color=ModernPalette.SUCCESS if is_db_connected else ModernPalette.WARNING,
                            ),
                            bgcolor="#132E27" if is_db_connected else "#3A2914",
                            border=ft.Border.all(1, ModernPalette.SUCCESS if is_db_connected else ModernPalette.WARNING),
                            border_radius=10,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                        )
                    ]
                ),
                ft.Text(
                    f"Connected to MySQL (root@localhost:3306/expenseflow_db)\n"
                    f"All data in MySQL is synchronized with Google Sheets in real-time.",
                    size=12,
                    color=ModernPalette.TEXT_MUTED,
                ),
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.FilledButton(
                            "2-Way Cloud Sync",
                            icon=ft.Icons.CLOUD_SYNC,
                            style=ft.ButtonStyle(bgcolor=ModernPalette.SUCCESS, color=ft.Colors.WHITE),
                            on_click=handle_sync_db_to_sheets,
                        ),
                        ft.OutlinedButton(
                            "Test DB Connection",
                            icon=ft.Icons.DATA_OBJECT,
                            on_click=handle_test_mysql,
                        ),
                    ]
                )
            ]
        )
    )

    # 2. Google Sheets Connection Banner
    sheets_status_card = ft.Container(
        bgcolor=ModernPalette.SURFACE_DARK,
        border_radius=16,
        padding=16,
        border=ft.Border.all(1, ModernPalette.SUCCESS if has_creds else ModernPalette.WARNING),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(
                                    ft.Icons.CHECK_CIRCLE if has_creds else ft.Icons.WARNING_AMBER,
                                    color=ModernPalette.SUCCESS if has_creds else ModernPalette.WARNING,
                                    size=22,
                                ),
                                ft.Text(
                                    "Google Service Account: Connected" if has_creds else "Credentials Not Found",
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                    color=ModernPalette.TEXT_PRIMARY,
                                ),
                            ]
                        ),
                    ]
                ),
                ft.Text(
                    f"Service Account Email:\n{service_email}" if service_email else
                    "Place your Google Cloud Service Account 'credentials.json' file into the app folder to enable automatic Google Sheets synchronization.",
                    size=12,
                    color=ModernPalette.TEXT_MUTED if service_email else "#FCD34D",
                ),
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.FilledButton(
                            "Test & Sync All",
                            icon=ft.Icons.SYNC,
                            style=ft.ButtonStyle(bgcolor=ModernPalette.PRIMARY, color=ft.Colors.WHITE),
                            on_click=lambda _: on_sync_request(),
                        ),
                        ft.OutlinedButton(
                            "Setup Instructions",
                            icon=ft.Icons.HELP_OUTLINE,
                            on_click=lambda _: show_setup_guide_dialog(),
                        ),
                    ]
                )
            ]
        )
    )

    # Setup Guide Dialog
    def show_setup_guide_dialog():

        dialog = ft.AlertDialog(
            title=ft.Text("Google Sheets Setup Guide", weight=ft.FontWeight.BOLD),
            content=ft.Column(
                tight=True,
                scroll=ft.ScrollMode.ADAPTIVE,
                spacing=10,
                controls=[
                    ft.Text("1. Create Google Cloud Project:", weight=ft.FontWeight.BOLD, size=13),
                    ft.Text("• Visit console.cloud.google.com and create a new project.", size=12),
                    ft.Text("2. Enable APIs:", weight=ft.FontWeight.BOLD, size=13),
                    ft.Text("• Enable 'Google Sheets API' & 'Google Drive API' in API Library.", size=12),
                    ft.Text("3. Create Service Account:", weight=ft.FontWeight.BOLD, size=13),
                    ft.Text("• Go to IAM & Admin ➔ Service Accounts ➔ Create Service Account.", size=12),
                    ft.Text("• Under 'Keys' tab, click 'Add Key' ➔ 'Create new key' ➔ JSON.", size=12),
                    ft.Text("• Rename the downloaded file to 'credentials.json' and place it in the project directory.", size=12),
                    ft.Text("4. Share your Google Sheet:", weight=ft.FontWeight.BOLD, size=13),
                    ft.Text(f"• Share your Google Sheet with the Service Account email:\n{service_email or '(Check credentials.json client_email)'}\nwith 'Editor' access.", size=12, color=ModernPalette.ACCENT),
                ]
            ),
            actions=[
                ft.TextButton("Close", on_click=lambda _: page.pop_dialog())
            ]
        )
        page.show_dialog(dialog)

    # 2. Spreadsheet Settings
    sheet_name_input = ft.TextField(
        value=saved_sheet_name,
        label="Spreadsheet Name",
        hint_text="ExpenseFlow Tracker & Reports",
        border_radius=12,
        filled=True,
        bgcolor=ModernPalette.SURFACE_DARK,
        border_color=ModernPalette.CARD_BORDER,
    )

    def save_sheet_name(_):
        val = sheet_name_input.value.strip()
        if val:
            database.set_setting("sheet_name", val)
            page.show_dialog(ft.SnackBar(ft.Text("Spreadsheet name saved!"), bgcolor=ModernPalette.SUCCESS))

    sheet_save_btn = ft.FilledButton(
        "Save Sheet Name",
        icon=ft.Icons.SAVE,
        style=ft.ButtonStyle(bgcolor=ModernPalette.PRIMARY, color=ft.Colors.WHITE),
        on_click=save_sheet_name,
    )

    spreadsheet_section = ft.Container(
        bgcolor=ModernPalette.SURFACE_DARK,
        border_radius=16,
        padding=16,
        border=ft.Border.all(1, ModernPalette.CARD_BORDER),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Text("Google Spreadsheet Name", size=14, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                sheet_name_input,
                ft.Row(
                    spacing=8,
                    controls=[
                        sheet_save_btn,
                        *( [ft.OutlinedButton("Open Sheet", icon=ft.Icons.OPEN_IN_NEW, url=sheet_url)] if sheet_url else [] )
                    ]
                ),
                ft.Text(f"Last sync: {last_sync}", size=11, color=ModernPalette.TEXT_MUTED),
            ]
        )
    )

    # 3. Currency & Budget Preferences
    currency_dropdown = ft.Dropdown(
        value=saved_currency,
        options=[ft.dropdown.Option(c, c) for c in CURRENCIES],
        label="Currency Symbol",
        border_radius=12,
        filled=True,
        bgcolor=ModernPalette.SURFACE_DARK,
        border_color=ModernPalette.CARD_BORDER,
    )

    budget_input = ft.TextField(
        value=saved_budget,
        label="Monthly Budget Target",
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=12,
        filled=True,
        bgcolor=ModernPalette.SURFACE_DARK,
        border_color=ModernPalette.CARD_BORDER,
    )

    def save_preferences(_):
        database.set_setting("currency_symbol", currency_dropdown.value)
        try:
            b_val = float(budget_input.value)
            database.set_setting("monthly_budget", str(b_val))
        except ValueError:
            pass
        page.show_dialog(ft.SnackBar(ft.Text("Preferences updated!"), bgcolor=ModernPalette.SUCCESS))

    pref_save_btn = ft.FilledButton(
        "Save Preferences",
        icon=ft.Icons.CHECK,
        style=ft.ButtonStyle(bgcolor=ModernPalette.PRIMARY, color=ft.Colors.WHITE),
        on_click=save_preferences,
    )

    pref_section = ft.Container(
        bgcolor=ModernPalette.SURFACE_DARK,
        border_radius=16,
        padding=16,
        border=ft.Border.all(1, ModernPalette.CARD_BORDER),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Text("Budget & Currency Preferences", size=14, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                currency_dropdown,
                budget_input,
                pref_save_btn,
            ]
        )
    )

    # 4. Categories & Auto Symbols Management
    def open_add_category_modal():
        new_cat_input = ft.TextField(
            label="Category Name",
            hint_text="e.g. Gym, Coffee, Books, Pets, Rent, Gaming",
            border_radius=12,
            filled=True,
            bgcolor=ModernPalette.SURFACE_DARK,
            autofocus=True,
        )

        preview_icon = ft.Icon(ft.Icons.LABEL, size=20, color=ModernPalette.PRIMARY)
        preview_label = ft.Text("Type category name above", size=12, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE)
        preview_chip = ft.Container(
            content=ft.Row(
                spacing=8,
                tight=True,
                controls=[preview_icon, preview_label]
            ),
            bgcolor="#1E293B",
            border=ft.Border.all(1, ModernPalette.PRIMARY),
            border_radius=16,
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
        )

        def on_name_type(e):
            val = new_cat_input.value.strip()
            if val:
                from config import auto_detect_category_info
                detected = auto_detect_category_info(val)
                preview_icon.name = detected["icon_name"]
                preview_icon.color = detected["color"]
                preview_label.value = f"{val} (Auto-detected: {detected['icon_name']})"
                preview_chip.border = ft.Border.all(1.5, detected["color"])
                preview_chip.bgcolor = detected["bg_color"]
            else:
                preview_icon.name = "LABEL"
                preview_icon.color = ModernPalette.PRIMARY
                preview_label.value = "Type category name above"
                preview_chip.border = ft.Border.all(1, ModernPalette.PRIMARY)
                preview_chip.bgcolor = "#1E293B"
            page.update()

        new_cat_input.on_change = on_name_type

        def save_new_category(_):
            val = new_cat_input.value.strip()
            if not val:
                page.show_dialog(ft.SnackBar(ft.Text("Please enter a category name!"), bgcolor=ModernPalette.DANGER))
                return
            new_cat = database.add_category(val)
            page.pop_dialog()
            render_category_chips()
            page.update()
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Added '{new_cat['key']}' with auto-detected symbol!"),
                    bgcolor=ModernPalette.SUCCESS
                )
            )

        dialog = ft.AlertDialog(
            title=ft.Text("Add New Category", weight=ft.FontWeight.BOLD),
            content=ft.Column(
                tight=True,
                spacing=12,
                controls=[
                    ft.Text(
                        "The app automatically detects the matching symbol and color as you type!",
                        size=12,
                        color=ModernPalette.TEXT_MUTED
                    ),
                    new_cat_input,
                    ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text("Auto-Detected Symbol Preview:", size=11, color=ModernPalette.TEXT_MUTED),
                            preview_chip,
                        ]
                    ),
                ]
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton(
                    "Save Category",
                    icon=ft.Icons.CHECK,
                    style=ft.ButtonStyle(bgcolor=ModernPalette.PRIMARY, color=ft.Colors.WHITE),
                    on_click=save_new_category,
                )
            ]
        )
        page.show_dialog(dialog)

    category_chips_row = ft.Row(wrap=True, spacing=6, run_spacing=6)

    def render_category_chips():
        category_chips_row.controls.clear()
        for cat in database.get_categories():
            category_chips_row.controls.append(
                ft.Container(
                    content=ft.Row(
                        spacing=5,
                        tight=True,
                        controls=[
                            ft.Icon(cat["icon"], size=14, color=cat["color"]),
                            ft.Text(cat["label"], size=11, color=ModernPalette.TEXT_PRIMARY),
                        ]
                    ),
                    bgcolor=ModernPalette.BG_DARK,
                    border=ft.Border.all(1, ModernPalette.CARD_BORDER),
                    border_radius=12,
                    padding=ft.Padding.symmetric(horizontal=8, vertical=5),
                )
            )

    render_category_chips()

    categories_section = ft.Container(
        bgcolor=ModernPalette.SURFACE_DARK,
        border_radius=16,
        padding=16,
        border=ft.Border.all(1, ModernPalette.CARD_BORDER),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("Categories & Auto Symbols", size=14, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                        ft.FilledButton(
                            "+ Add",
                            icon=ft.Icons.ADD,
                            style=ft.ButtonStyle(bgcolor=ModernPalette.PRIMARY, color=ft.Colors.WHITE),
                            on_click=lambda _: open_add_category_modal(),
                        ),
                    ]
                ),
                ft.Text("Categories have intelligent auto-detected symbols and colors:", size=11, color=ModernPalette.TEXT_MUTED),
                category_chips_row,
            ]
        )
    )

    # 5. Data Management (Sample Data & Clear)
    def handle_seed_data(_):
        database.seed_sample_data()
        page.show_dialog(ft.SnackBar(ft.Text("Added 18 realistic sample expenses! Check Dashboard & Reports."), bgcolor=ModernPalette.SUCCESS))
        on_navigate("dashboard")

    def handle_clear_data(_):
        def confirm_clear(_):
            database.clear_all_expenses()
            page.pop_dialog()
            page.show_dialog(ft.SnackBar(ft.Text("All expenses cleared."), bgcolor=ModernPalette.WARNING))
            on_navigate("dashboard")

        dialog = ft.AlertDialog(
            title=ft.Text("Clear All Expenses?", weight=ft.FontWeight.BOLD),
            content=ft.Text("This will delete all local expenses. This action cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.TextButton("Clear All", on_click=confirm_clear, style=ft.ButtonStyle(color=ModernPalette.DANGER)),
            ]
        )
        page.show_dialog(dialog)

    data_mgmt_section = ft.Container(
        bgcolor=ModernPalette.SURFACE_DARK,
        border_radius=16,
        padding=16,
        border=ft.Border.all(1, ModernPalette.CARD_BORDER),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Text("Data Management", size=14, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                ft.OutlinedButton(
                    "Generate Demo Expenses (18 Items)",
                    icon=ft.Icons.DATA_SAVER_ON,
                    on_click=handle_seed_data,
                ),
                ft.OutlinedButton(
                    "Clear All Expenses",
                    icon=ft.Icons.DELETE_FOREVER,
                    style=ft.ButtonStyle(color=ModernPalette.DANGER),
                    on_click=handle_clear_data,
                ),
            ]
        )
    )

    # 6. About the Developer & Creator Section
    developer_section = ft.Container(
        bgcolor=ModernPalette.SURFACE_DARK,
        border_radius=16,
        padding=18,
        border=ft.Border.all(1, ModernPalette.CARD_BORDER),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            content=ft.Icon(ft.Icons.CODE_ROUNDED, color=ft.Colors.WHITE, size=24),
                            bgcolor=ModernPalette.PRIMARY,
                            border_radius=12,
                            padding=10,
                            gradient=ft.LinearGradient(
                                begin=ft.Alignment.TOP_LEFT,
                                end=ft.Alignment.BOTTOM_RIGHT,
                                colors=["#6366F1", "#8B5CF6"]
                            )
                        ),
                    ]
                ),
                ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2,
                    controls=[
                        ft.Text("Created & Developed By", size=11, weight=ft.FontWeight.W_500, color=ModernPalette.TEXT_MUTED),
                        ft.Text(DEVELOPER_INFO["name"], size=18, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                        ft.Text("Full-Stack & Mobile Developer", size=12, color=ModernPalette.ACCENT, weight=ft.FontWeight.W_600),
                    ]
                ),
                ft.Divider(color=ModernPalette.CARD_BORDER, height=1),
                # Contact Details
                ft.Column(
                    spacing=8,
                    controls=[
                        # Phone & WhatsApp
                        ft.Container(
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Row(
                                        spacing=8,
                                        controls=[
                                            ft.Icon(ft.Icons.PHONE_ROUNDED, size=16, color=ModernPalette.SUCCESS),
                                            ft.Text("Phone & WhatsApp:", size=12, color=ModernPalette.TEXT_MUTED),
                                        ]
                                    ),
                                    ft.Text(DEVELOPER_INFO["phone"], size=12, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                                ]
                            ),
                            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                        ),
                        # Email ID
                        ft.Container(
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Row(
                                        spacing=8,
                                        controls=[
                                            ft.Icon(ft.Icons.EMAIL_ROUNDED, size=16, color=ModernPalette.ACCENT),
                                            ft.Text("Email Address:", size=12, color=ModernPalette.TEXT_MUTED),
                                        ]
                                    ),
                                    ft.Text(DEVELOPER_INFO["email"], size=12, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                                ]
                            ),
                            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                        ),
                    ]
                ),
                # Quick Action Buttons: WhatsApp & Email
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                    controls=[
                        ft.FilledButton(
                            "Chat on WhatsApp",
                            icon=ft.Icons.CHAT_ROUNDED,
                            url=DEVELOPER_INFO["whatsapp_url"],
                            style=ft.ButtonStyle(
                                bgcolor="#25D366",
                                color=ft.Colors.WHITE,
                                shape=ft.RoundedRectangleBorder(radius=10),
                                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                            ),
                        ),
                        ft.OutlinedButton(
                            "Send Email",
                            icon=ft.Icons.MAIL_OUTLINE_ROUNDED,
                            url=f"mailto:{DEVELOPER_INFO['email']}",
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=10),
                                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                            ),
                        ),
                    ]
                ),
                ft.Container(height=4),
                ft.Text(f"{APP_NAME} v{APP_VERSION} • Built with Python & Flet for Android", size=10, color=ModernPalette.TEXT_MUTED),
            ]
        )
    )

    return ft.ListView(
        expand=True,
        spacing=16,
        scroll=ft.ScrollMode.AUTO,
        padding=ft.Padding.only(left=16, right=16, top=16, bottom=120),
        controls=[
            ft.Text("Settings & Sync", size=18, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
            account_section,
            mysql_status_card,
            sheets_status_card,
            spreadsheet_section,
            pref_section,
            categories_section,
            data_mgmt_section,
            developer_section,
            ft.Container(height=40),
        ]
    )
