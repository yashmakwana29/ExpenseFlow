"""
Dashboard View (Home Screen) for ExpenseFlow.
Displays current month spending, budget health, quick action shortcuts,
category spend summary, and recent transaction history.
"""
import datetime
import flet as ft
import database
from config import CATEGORY_MAP, PAYMENT_MAP, ModernPalette, APP_NAME

def build_dashboard_view(page: ft.Page, on_navigate, on_sync_request) -> ft.Control:
    """Builds the mobile dashboard screen."""
    
    # Fetch current month and settings
    curr_user = database.get_current_session_user()
    curr_user_id = curr_user["id"] if curr_user else None
    user_display = curr_user["full_name"] if curr_user and curr_user.get("full_name") else (curr_user["username"] if curr_user else "User")
    username_display = curr_user["username"] if curr_user else "admin"

    # Fetch current month and settings
    now = datetime.datetime.now()
    curr_month_str = now.strftime("%Y-%m")
    curr_month_display = now.strftime("%B %Y")
    currency = database.get_setting("currency_symbol", "₹")
    
    try:
        monthly_budget = float(database.get_setting("monthly_budget", "25000"))
    except ValueError:
        monthly_budget = 25000.0

    # Fetch user-isolated stats
    stats = database.get_stats(month_str=curr_month_str, user_id=curr_user_id)
    kpis = stats["kpis"]
    total_spent = kpis["total_amount"]
    avg_spent = kpis["avg_amount"]
    max_spent = kpis["max_amount"]
    
    # Budget calculations
    budget_percent = (total_spent / monthly_budget) if monthly_budget > 0 else 0.0
    budget_percent_clamped = min(budget_percent, 1.0)
    remaining_budget = max(0.0, monthly_budget - total_spent)
    
    budget_status_color = ModernPalette.SUCCESS
    if budget_percent > 0.9:
        budget_status_color = ModernPalette.DANGER
    elif budget_percent > 0.7:
        budget_status_color = ModernPalette.WARNING

    # Unsynced items count for this user
    all_unsynced = database.get_unsynced_expenses()
    unsynced_items = [e for e in all_unsynced if curr_user_id is None or e.get("user_id") == curr_user_id]
    unsynced_count = len(unsynced_items)

    # 1. Top Mobile App Header Bar (Brand + Live Cloud/DB Status Badges)
    app_header_bar = ft.Container(
        padding=ft.Padding.only(top=4, bottom=6),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                # Brand Logo & Title
                ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            content=ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, color=ft.Colors.WHITE, size=20),
                            bgcolor=ModernPalette.PRIMARY,
                            border_radius=10,
                            padding=7,
                            gradient=ft.LinearGradient(
                                begin=ft.Alignment.TOP_LEFT,
                                end=ft.Alignment.BOTTOM_RIGHT,
                                colors=["#6366F1", "#4F46E5"]
                            )
                        ),
                        ft.Column(
                            spacing=1,
                            controls=[
                                ft.Text(APP_NAME, size=15, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                                ft.Text("Expense Tracker", size=10, color=ModernPalette.TEXT_MUTED, weight=ft.FontWeight.W_500),
                            ]
                        )
                    ]
                ),
                # Status Badges: MySQL/SQLite Database + Google Sheets 2-Way Sync
                ft.Row(
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        # Database Indicator Badge
                        ft.Container(
                            content=ft.Row(
                                spacing=4,
                                tight=True,
                                controls=[
                                    ft.Icon(
                                        ft.Icons.STORAGE_ROUNDED,
                                        size=12,
                                        color=ModernPalette.SUCCESS if database.is_using_mysql() else ModernPalette.WARNING,
                                    ),
                                    ft.Text(
                                        "MySQL" if database.is_using_mysql() else "SQLite",
                                        size=10,
                                        weight=ft.FontWeight.W_600,
                                        color=ModernPalette.SUCCESS if database.is_using_mysql() else ModernPalette.WARNING,
                                    ),
                                ]
                            ),
                            bgcolor="#1E293B",
                            border=ft.Border.all(1, ModernPalette.SUCCESS if database.is_using_mysql() else ModernPalette.WARNING),
                            border_radius=16,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=5),
                            tooltip=database.get_db_type(),
                        ),
                        # Google Sheets 2-Way Cloud Sync Badge (Interactive Button)
                        ft.Container(
                            content=ft.Row(
                                spacing=4,
                                tight=True,
                                controls=[
                                    ft.Icon(
                                        ft.Icons.SYNC if unsynced_count > 0 else ft.Icons.CLOUD_DONE_ROUNDED,
                                        size=12,
                                        color=ModernPalette.WARNING if unsynced_count > 0 else ModernPalette.SUCCESS,
                                    ),
                                    ft.Text(
                                        f"{unsynced_count} Pending" if unsynced_count > 0 else "Sheets Synced",
                                        size=10,
                                        weight=ft.FontWeight.W_600,
                                        color=ModernPalette.WARNING if unsynced_count > 0 else ModernPalette.SUCCESS,
                                    ),
                                ]
                            ),
                            bgcolor="#1E293B",
                            border=ft.Border.all(1, ModernPalette.WARNING if unsynced_count > 0 else ModernPalette.SUCCESS),
                            border_radius=16,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=5),
                            on_click=lambda _: on_sync_request(),
                            tooltip="Tap to 2-Way Sync with Google Sheets",
                        ),
                    ]
                )
            ]
        )
    )

    # 2. User Greeting Section (Starts cleanly below the top mobile header)
    greeting_section = ft.Container(
        padding=ft.Padding.only(top=4, bottom=2),
        content=ft.Column(
            spacing=2,
            controls=[
                ft.Text(
                    f"Hi, {user_display} 👋",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=ModernPalette.TEXT_PRIMARY,
                ),
                ft.Row(
                    spacing=6,
                    tight=True,
                    controls=[
                        ft.Text(
                            f"@{username_display}",
                            size=12,
                            color=ModernPalette.ACCENT,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text("•", size=12, color=ModernPalette.TEXT_MUTED),
                        ft.Text(
                            "Personal Finance Hub",
                            size=12,
                            color=ModernPalette.TEXT_MUTED,
                            weight=ft.FontWeight.W_500,
                        ),
                    ]
                )
            ]
        )
    )


    # 2. Hero Gradient Spend Card
    hero_card = ft.Container(
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=["#1E1B4B", "#312E81", "#1E293B"],
        ),
        border_radius=22,
        padding=20,
        border=ft.Border.all(1, "#4338CA"),
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(f"Total Spent ({curr_month_display})", size=13, color="#C7D2FE", weight=ft.FontWeight.W_500),
                        ft.Container(
                            content=ft.Text(f"{budget_percent * 100:.1f}% used", size=11, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                            bgcolor=budget_status_color,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                            border_radius=10,
                        )
                    ]
                ),
                ft.Text(
                    f"{currency} {total_spent:,.2f}",
                    size=30,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE,
                ),
                # Progress Bar
                ft.Column(
                    spacing=6,
                    controls=[
                        ft.ProgressBar(
                            value=budget_percent_clamped,
                            color=budget_status_color,
                            bgcolor="#3730A3",
                            height=8,
                            border_radius=4,
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(f"Remaining: {currency} {remaining_budget:,.0f}", size=11, color="#A5B4FC"),
                                ft.Text(f"Budget: {currency} {monthly_budget:,.0f}", size=11, color="#A5B4FC"),
                            ]
                        )
                    ]
                ),
                # Quick Stat chips
                ft.Row(
                    spacing=10,
                    controls=[
                        ft.Container(
                            expand=True,
                            bgcolor="#1E293B",
                            border_radius=12,
                            padding=8,
                            content=ft.Column(
                                spacing=2,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Text("Daily Average", size=10, color=ModernPalette.TEXT_MUTED),
                                    ft.Text(f"{currency} {avg_spent:,.0f}", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                ]
                            )
                        ),
                        ft.Container(
                            expand=True,
                            bgcolor="#1E293B",
                            border_radius=12,
                            padding=8,
                            content=ft.Column(
                                spacing=2,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Text("Highest Expense", size=10, color=ModernPalette.TEXT_MUTED),
                                    ft.Text(f"{currency} {max_spent:,.0f}", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                ]
                            )
                        ),
                    ]
                )
            ]
        )
    )

    # 3. Quick Actions Row
    def quick_add_handler(title: str, amount: float, cat: str, mode: str):
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        database.add_expense(
            title=title,
            amount=amount,
            category=cat,
            payment_mode=mode,
            date=today_str,
            notes="Added via Quick Action shortcut",
            synced=0,
            user_id=curr_user_id,
            created_by=username_display
        )
        on_navigate("dashboard")
        page.show_dialog(ft.SnackBar(ft.Text(f"Added {currency}{amount} for {title}!"), bgcolor=ModernPalette.SUCCESS))

    quick_actions = ft.Column(
        spacing=8,
        controls=[
            ft.Text("Quick Actions", size=14, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
            ft.Row(
                spacing=8,
                scroll=ft.ScrollMode.ADAPTIVE,
                controls=[
                    ft.FilledButton(
                        "Add Expense",
                        icon=ft.Icons.ADD,
                        style=ft.ButtonStyle(bgcolor=ModernPalette.PRIMARY, color=ft.Colors.WHITE),
                        on_click=lambda _: on_navigate("add_expense"),
                    ),
                    ft.OutlinedButton(
                        f"+ {currency}100 Snack",
                        icon=ft.Icons.FASTFOOD,
                        on_click=lambda _: quick_add_handler("Quick Snack", 100.0, "Food & Dining", "UPI"),
                    ),
                    ft.OutlinedButton(
                        f"+ {currency}200 Fuel",
                        icon=ft.Icons.LOCAL_GAS_STATION,
                        on_click=lambda _: quick_add_handler("Quick Fuel", 200.0, "Transport", "UPI"),
                    ),
                ]
            )
        ]
    )

    # 4. Top Spending Categories Snapshot
    cat_map = database.get_category_map()
    top_categories = stats["categories"][:4]
    category_cards = []
    for cat in top_categories:
        info = cat_map.get(cat["category"], {})
        color = info.get("color", ModernPalette.PRIMARY)
        pct = cat.get("percent", 0.0)

        category_cards.append(
            ft.Container(
                bgcolor=ModernPalette.SURFACE_DARK,
                border_radius=14,
                padding=12,
                border=ft.Border.all(1, ModernPalette.CARD_BORDER),
                content=ft.Column(
                    spacing=6,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Row(
                                    spacing=8,
                                    controls=[
                                        ft.Container(
                                            content=ft.Icon(info.get("icon", ft.Icons.CATEGORY), size=16, color=color),
                                            bgcolor="#0F172A",
                                            padding=6,
                                            border_radius=8,
                                        ),
                                        ft.Text(cat["category"], size=13, weight=ft.FontWeight.W_600, color=ModernPalette.TEXT_PRIMARY),
                                    ]
                                ),
                                ft.Text(f"{currency} {cat['total_amount']:,.0f}", size=13, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                            ]
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.ProgressBar(
                                    value=pct / 100.0,
                                    color=color,
                                    bgcolor="#0F172A",
                                    height=6,
                                    border_radius=3,
                                    expand=True,
                                ),
                                ft.Container(width=10),
                                ft.Text(f"{pct:.1f}%", size=11, color=ModernPalette.TEXT_MUTED, weight=ft.FontWeight.W_500),
                            ]
                        )
                    ]
                )
            )
        )

    categories_section = ft.Column(
        spacing=8,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("Top Spending Categories", size=14, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                    ft.TextButton(
                        "Full Reports ➔",
                        on_click=lambda _: on_navigate("reports"),
                    )
                ]
            ),
            *(category_cards if category_cards else [
                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    padding=20,
                    content=ft.Text("No expenses recorded yet for this month.", size=12, color=ModernPalette.TEXT_MUTED)
                )
            ])
        ]
    )

    # 5. Recent Transactions
    recent_expenses = database.get_expenses(limit=5, user_id=curr_user_id)
    recent_items = []
    
    if not recent_expenses:
        recent_items.append(
            ft.Container(
                alignment=ft.Alignment.CENTER,
                padding=24,
                bgcolor=ModernPalette.SURFACE_DARK,
                border_radius=16,
                border=ft.Border.all(1, ModernPalette.CARD_BORDER),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                    controls=[
                        ft.Icon(ft.Icons.RECEIPT_LONG_OUTLINED, size=36, color=ModernPalette.PRIMARY_LIGHT),
                        ft.Text(f"Welcome, {user_display}!", size=13, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                        ft.Text("No transactions logged yet. Tap '+ Add Expense' or use Quick Actions above to record your first expense!", size=11, color=ModernPalette.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                    ]
                )
            )
        )

    for exp in recent_expenses:

        cat_info = cat_map.get(exp["category"], {})
        color = cat_info.get("color", ModernPalette.PRIMARY)
        is_synced = (exp.get("synced") == 1)

        recent_items.append(
            ft.Container(
                bgcolor=ModernPalette.SURFACE_DARK,
                border_radius=14,
                padding=12,
                border=ft.Border.all(1, ModernPalette.CARD_BORDER),
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
                                                ft.Text(exp["payment_mode"], size=11, color=ModernPalette.ACCENT),
                                                ft.Text("•", size=11, color=ModernPalette.TEXT_MUTED),
                                                ft.Text(f"@{exp.get('created_by', 'admin')}", size=11, weight=ft.FontWeight.W_600, color=ModernPalette.PRIMARY),
                                            ]
                                        )
                                    ]
                                )
                            ]
                        ),
                        ft.Column(
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            spacing=2,
                            controls=[
                                ft.Text(
                                    f"-{currency}{exp['amount']:,.2f}",
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                    color="#F87171",
                                ),
                                ft.Icon(
                                    ft.Icons.CHECK_CIRCLE if is_synced else ft.Icons.CLOUD_QUEUE,
                                    size=13,
                                    color=ModernPalette.SUCCESS if is_synced else ModernPalette.WARNING,
                                    tooltip="Synced to Google Sheets" if is_synced else "Pending sync to Google Sheets"
                                )
                            ]
                        )
                    ]
                )
            )
        )

    recent_section = ft.Column(
        spacing=8,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("Recent Transactions", size=14, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                    ft.TextButton(
                        "See All ➔",
                        on_click=lambda _: on_navigate("transactions"),
                    )
                ]
            ),
            *(recent_items if recent_items else [
                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    padding=20,
                    content=ft.Text("No transactions yet. Tap 'Add Expense' to record one!", size=12, color=ModernPalette.TEXT_MUTED)
                )
            ])
        ]
    )

    # Return full scrollable mobile dashboard container
    return ft.ListView(
        expand=True,
        spacing=18,
        scroll=ft.ScrollMode.AUTO,
        padding=ft.Padding.only(left=16, right=16, top=12, bottom=120),
        controls=[
            app_header_bar,
            greeting_section,
            hero_card,
            quick_actions,
            categories_section,
            recent_section,
            # Extra bottom padding for navigation bar
            ft.Container(height=40),
        ]
    )
