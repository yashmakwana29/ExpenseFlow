"""
Transactions View for ExpenseFlow.
Allows full history search, multi-factor filtering by category and payment mode,
details viewing, editing, and deletion.
"""
import flet as ft
import database
from config import CATEGORIES, PAYMENT_MODES, CATEGORY_MAP, PAYMENT_MAP, ModernPalette

def build_transactions_view(page: ft.Page, on_navigate, on_edit_request) -> ft.Control:
    """Builds the transactions history screen."""
    
    currency = database.get_setting("currency_symbol", "₹")
    
    curr_user = database.get_current_session_user()
    curr_username = curr_user["username"] if curr_user else "admin"

    # Filter state - defaults to current logged-in user
    search_query = [""]
    selected_category = ["All"]
    selected_payment = ["All"]
    selected_user = [curr_username]

    transactions_list_column = ft.Column(spacing=8)

    def refresh_list():
        expenses = database.get_expenses(
            search=search_query[0] if search_query[0] else None,
            category=selected_category[0] if selected_category[0] != "All" else None,
            payment_mode=selected_payment[0] if selected_payment[0] != "All" else None,
            username=selected_user[0] if selected_user[0] != "All" else None,
        )

        transactions_list_column.controls.clear()

        if not expenses:
            transactions_list_column.controls.append(
                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    padding=40,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.SEARCH_OFF, size=48, color=ModernPalette.TEXT_MUTED),
                            ft.Text("No transactions found", size=14, color=ModernPalette.TEXT_MUTED, weight=ft.FontWeight.W_500),
                            ft.Text("Try adjusting your search or filters", size=12, color="#64748B"),
                        ]
                    )
                )
            )
            return

        cat_map = database.get_category_map()
        for exp in expenses:
            exp_id = exp["id"]
            cat_info = cat_map.get(exp["category"], {})
            color = cat_info.get("color", ModernPalette.PRIMARY)
            is_synced = (exp.get("synced") == 1)

            # Details / Action Dialog
            def open_actions(e, item=exp):
                def confirm_delete(_):
                    database.delete_expense(item["id"])
                    page.pop_dialog()
                    refresh_list()
                    page.update()
                    page.show_dialog(ft.SnackBar(ft.Text("Expense deleted."), bgcolor=ModernPalette.WARNING))

                def trigger_edit(_):
                    page.pop_dialog()
                    on_edit_request(item["id"])

                dialog = ft.AlertDialog(
                    title=ft.Text(item["title"], weight=ft.FontWeight.BOLD),
                    content=ft.Column(
                        tight=True,
                        spacing=6,
                        controls=[
                            ft.Text(f"Amount: {currency}{item['amount']:,.2f}", size=14, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Category: {item['category']}", size=13),
                            ft.Text(f"Payment: {item['payment_mode']}", size=13),
                            ft.Text(f"Date: {item['date']}", size=13),
                            ft.Text(f"Added by: @{item.get('created_by', 'admin')}", size=13, color=ModernPalette.ACCENT, weight=ft.FontWeight.W_600),
                            ft.Text(f"Notes: {item['notes'] or 'None'}", size=12, color=ModernPalette.TEXT_MUTED),
                            ft.Text(
                                "Status: Synced to Google Sheets" if item.get("synced") == 1 else "Status: Pending Sync",
                                size=12,
                                color=ModernPalette.SUCCESS if item.get("synced") == 1 else ModernPalette.WARNING,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ]
                    ),
                    actions=[
                        ft.TextButton("Edit", on_click=trigger_edit),
                        ft.TextButton("Delete", on_click=confirm_delete, style=ft.ButtonStyle(color=ModernPalette.DANGER)),
                        ft.TextButton("Close", on_click=lambda _: page.pop_dialog()),
                    ],
                )
                page.show_dialog(dialog)

            item_card = ft.Container(
                bgcolor=ModernPalette.SURFACE_DARK,
                border_radius=14,
                padding=12,
                border=ft.Border.all(1, ModernPalette.CARD_BORDER),
                on_click=open_actions,
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=12,
                            controls=[
                                ft.Container(
                                    content=ft.Icon(cat_info.get("icon", ft.Icons.PAYMENTS), size=20, color=color),
                                    bgcolor="#0F172A",
                                    padding=10,
                                    border_radius=12,
                                ),
                                ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text(exp["title"], size=13, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                                        ft.Row(
                                            spacing=5,
                                            controls=[
                                                ft.Text(exp["date"], size=11, color=ModernPalette.TEXT_MUTED),
                                                ft.Text("•", size=11, color=ModernPalette.TEXT_MUTED),
                                                ft.Text(exp["category"], size=11, color=color),
                                                ft.Text("•", size=11, color=ModernPalette.TEXT_MUTED),
                                                ft.Text(f"@{exp.get('created_by', 'admin')}", size=11, weight=ft.FontWeight.W_600, color=ModernPalette.ACCENT),
                                            ]
                                        ),
                                        *( [ft.Text(exp["notes"], size=10, color="#64748B", max_lines=1)] if exp.get("notes") else [] )
                                    ]
                                )
                            ]
                        ),
                        ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            spacing=3,
                            controls=[
                                ft.Text(
                                    f"-{currency}{exp['amount']:,.2f}",
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                    color="#F87171",
                                ),
                                ft.Row(
                                    spacing=4,
                                    tight=True,
                                    controls=[
                                        ft.Container(
                                            bgcolor="#0F172A",
                                            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                            border_radius=6,
                                            content=ft.Text(exp["payment_mode"], size=9, color=ModernPalette.ACCENT)
                                        ),
                                        ft.Icon(
                                            ft.Icons.CHECK_CIRCLE if is_synced else ft.Icons.CLOUD_QUEUE,
                                            size=13,
                                            color=ModernPalette.SUCCESS if is_synced else ModernPalette.WARNING,
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                )
            )
            transactions_list_column.controls.append(item_card)

    # Search Field
    search_field = ft.TextField(
        hint_text="Search by description or notes...",
        prefix_icon=ft.Icons.SEARCH,
        dense=True,
        border_radius=12,
        filled=True,
        bgcolor=ModernPalette.SURFACE_DARK,
        border_color=ModernPalette.CARD_BORDER,
        on_change=lambda e: (search_query.__setitem__(0, e.control.value), refresh_list(), page.update()),
    )

    # Filter Dropdowns
    category_options = [ft.dropdown.Option("All", "All Categories")] + [ft.dropdown.Option(c["key"], c["label"]) for c in database.get_categories()]
    cat_dropdown = ft.Dropdown(
        value="All",
        options=category_options,
        dense=True,
        expand=True,
        border_radius=12,
        bgcolor=ModernPalette.SURFACE_DARK,
        border_color=ModernPalette.CARD_BORDER,
        on_select=lambda e: (selected_category.__setitem__(0, e.control.value), refresh_list(), page.update()),
    )

    payment_options = [ft.dropdown.Option("All", "All Payment Modes")] + [ft.dropdown.Option(p["key"], p["key"]) for p in PAYMENT_MODES]
    pay_dropdown = ft.Dropdown(
        value="All",
        options=payment_options,
        dense=True,
        expand=True,
        border_radius=12,
        bgcolor=ModernPalette.SURFACE_DARK,
        border_color=ModernPalette.CARD_BORDER,
        on_select=lambda e: (selected_payment.__setitem__(0, e.control.value), refresh_list(), page.update()),
    )

    is_admin = bool(curr_user and curr_user.get("role") == "admin")
    filter_controls = [cat_dropdown, pay_dropdown]

    if is_admin:
        all_users = database.get_all_users()
        user_options = [
            ft.dropdown.Option(curr_username, f"My txns (@{curr_username})"),
            ft.dropdown.Option("All", "All Members")
        ] + [ft.dropdown.Option(u["username"], f"@{u['username']}") for u in all_users if u["username"] != curr_username]

        user_dropdown = ft.Dropdown(
            value=curr_username,
            options=user_options,
            dense=True,
            expand=True,
            border_radius=12,
            bgcolor=ModernPalette.SURFACE_DARK,
            border_color=ModernPalette.CARD_BORDER,
            on_select=lambda e: (selected_user.__setitem__(0, e.control.value), refresh_list(), page.update()),
        )
        filter_controls.append(user_dropdown)

    filter_row = ft.Row(spacing=6, controls=filter_controls)

    # Initial render
    refresh_list()

    return ft.ListView(
        expand=True,
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        padding=ft.Padding.only(left=16, right=16, top=16, bottom=120),
        controls=[
            ft.Text("Transaction History", size=18, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
            search_field,
            filter_row,
            transactions_list_column,
            ft.Container(height=40),
        ]
    )
