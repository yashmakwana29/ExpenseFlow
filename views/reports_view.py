"""
Reports & Analytics View for ExpenseFlow.
Provides mobile in-app analytics: category breakdown, payment mode distribution,
monthly comparisons, key performance indicators, and Google Sheet report links.
"""
import datetime
import flet as ft
import database
from config import CATEGORY_MAP, PAYMENT_MAP, ModernPalette

def build_reports_view(page: ft.Page, on_navigate) -> ft.Control:
    """Builds the comprehensive mobile in-app reports screen."""
    
    curr_user = database.get_current_session_user()
    curr_user_id = curr_user["id"] if curr_user else None
    user_display = curr_user["full_name"] if curr_user and curr_user.get("full_name") else (curr_user["username"] if curr_user else "User")
    username_display = curr_user["username"] if curr_user else "admin"

    currency = database.get_setting("currency_symbol", "₹")
    available_months = database.get_available_months(user_id=curr_user_id)
    
    # Current month as default
    curr_month = datetime.datetime.now().strftime("%Y-%m")
    if curr_month not in available_months:
        available_months.insert(0, curr_month)
    
    selected_month = [curr_month]  # mutable container for closure
    selected_scope = ["my"]        # "my" = Personal (Default), "team" = All Team

    # Main dynamic report content container
    content_area = ft.Column(spacing=16)

    def render_report_data():
        m_val = selected_month[0]
        uid_filter = curr_user_id if selected_scope[0] == "my" else None
        stats = database.get_stats(None if m_val == "All" else m_val, user_id=uid_filter)
        kpis = stats["kpis"]
        categories = stats["categories"]
        payment_modes = stats["payment_modes"]

        total_spent = kpis["total_amount"]
        total_txns = kpis["total_count"]
        avg_spend = kpis["avg_amount"]
        max_spend = kpis["max_amount"]
        cat_map = database.get_category_map()

        content_area.controls.clear()


        # 1. KPI Cards Grid
        kpi_row_1 = ft.Row(
            spacing=10,
            controls=[
                ft.Container(
                    expand=True,
                    bgcolor=ModernPalette.SURFACE_DARK,
                    border_radius=16,
                    padding=14,
                    border=ft.Border.all(1, ModernPalette.CARD_BORDER),
                    content=ft.Column(
                        spacing=4,
                        controls=[
                            ft.Row(
                                spacing=6,
                                controls=[
                                    ft.Icon(ft.Icons.MONEY, size=16, color=ModernPalette.ACCENT),
                                    ft.Text("Total Spending", size=11, color=ModernPalette.TEXT_MUTED),
                                ]
                            ),
                            ft.Text(f"{currency} {total_spent:,.2f}", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ]
                    )
                ),
                ft.Container(
                    expand=True,
                    bgcolor=ModernPalette.SURFACE_DARK,
                    border_radius=16,
                    padding=14,
                    border=ft.Border.all(1, ModernPalette.CARD_BORDER),
                    content=ft.Column(
                        spacing=4,
                        controls=[
                            ft.Row(
                                spacing=6,
                                controls=[
                                    ft.Icon(ft.Icons.RECEIPT_LONG, size=16, color=ModernPalette.PRIMARY_LIGHT),
                                    ft.Text("Transactions", size=11, color=ModernPalette.TEXT_MUTED),
                                ]
                            ),
                            ft.Text(f"{total_txns} entries", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ]
                    )
                ),
            ]
        )

        kpi_row_2 = ft.Row(
            spacing=10,
            controls=[
                ft.Container(
                    expand=True,
                    bgcolor=ModernPalette.SURFACE_DARK,
                    border_radius=16,
                    padding=14,
                    border=ft.Border.all(1, ModernPalette.CARD_BORDER),
                    content=ft.Column(
                        spacing=4,
                        controls=[
                            ft.Row(
                                spacing=6,
                                controls=[
                                    ft.Icon(ft.Icons.CALCULATE, size=16, color=ModernPalette.WARNING),
                                    ft.Text("Avg / Transaction", size=11, color=ModernPalette.TEXT_MUTED),
                                ]
                            ),
                            ft.Text(f"{currency} {avg_spend:,.0f}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ]
                    )
                ),
                ft.Container(
                    expand=True,
                    bgcolor=ModernPalette.SURFACE_DARK,
                    border_radius=16,
                    padding=14,
                    border=ft.Border.all(1, ModernPalette.CARD_BORDER),
                    content=ft.Column(
                        spacing=4,
                        controls=[
                            ft.Row(
                                spacing=6,
                                controls=[
                                    ft.Icon(ft.Icons.NORTH_EAST, size=16, color=ModernPalette.DANGER),
                                    ft.Text("Single Highest", size=11, color=ModernPalette.TEXT_MUTED),
                                ]
                            ),
                            ft.Text(f"{currency} {max_spend:,.0f}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ]
                    )
                ),
            ]
        )

        content_area.controls.extend([kpi_row_1, kpi_row_2])

        # 2. Multi-Color Distribution Proportion Bar
        if categories and total_spent > 0:
            segment_bars = []
            for cat in categories[:6]:
                info = cat_map.get(cat["category"], {})
                c_color = info.get("color", ModernPalette.PRIMARY)
                p_val = max(1, int(cat["percent"]))
                segment_bars.append(
                    ft.Container(
                        expand=p_val,
                        bgcolor=c_color,
                        height=12,
                        tooltip=f"{cat['category']}: {cat['percent']:.1f}%",
                    )
                )

            distribution_card = ft.Container(
                bgcolor=ModernPalette.SURFACE_DARK,
                border_radius=16,
                padding=14,
                border=ft.Border.all(1, ModernPalette.CARD_BORDER),
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Text("Spending Proportion", size=13, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                        ft.Container(
                            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                            border_radius=6,
                            content=ft.Row(spacing=2, controls=segment_bars),
                        ),
                        # Legend chips
                        ft.Row(
                            wrap=True,
                            spacing=10,
                            run_spacing=6,
                            controls=[
                                ft.Row(
                                    spacing=4,
                                    tight=True,
                                    controls=[
                                        ft.Container(width=8, height=8, border_radius=4, bgcolor=cat_map.get(c["category"], {}).get("color", ModernPalette.PRIMARY)),
                                        ft.Text(f"{c['category']} ({c['percent']:.0f}%)", size=10, color=ModernPalette.TEXT_MUTED),
                                    ]
                                ) for c in categories[:5]
                            ]
                        )
                    ]
                )
            )
            content_area.controls.append(distribution_card)

        # 3. Category Breakdown Details
        cat_items = []
        for cat in categories:
            info = cat_map.get(cat["category"], {})
            color = info.get("color", ModernPalette.PRIMARY)
            pct = cat["percent"]

            cat_items.append(
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
                                            ft.Column(
                                                spacing=1,
                                                controls=[
                                                    ft.Text(cat["category"], size=13, weight=ft.FontWeight.W_600, color=ModernPalette.TEXT_PRIMARY),
                                                    ft.Text(f"{cat['count']} transaction(s)", size=10, color=ModernPalette.TEXT_MUTED),
                                                ]
                                            )
                                        ]
                                    ),
                                    ft.Column(
                                        horizontal_alignment=ft.CrossAxisAlignment.END,
                                        spacing=1,
                                        controls=[
                                            ft.Text(f"{currency} {cat['total_amount']:,.2f}", size=13, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                                            ft.Text(f"{pct:.1f}%", size=11, color=color, weight=ft.FontWeight.W_600),
                                        ]
                                    )
                                ]
                            ),
                            ft.ProgressBar(
                                value=pct / 100.0,
                                color=color,
                                bgcolor="#0F172A",
                                height=6,
                                border_radius=3,
                            )
                        ]
                    )
                )
            )

        cat_section = ft.Column(
            spacing=8,
            controls=[
                ft.Text("Category Breakdown", size=14, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                *(cat_items if cat_items else [
                    ft.Container(
                        padding=20,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text("No category data available for this timeframe.", size=12, color=ModernPalette.TEXT_MUTED)
                    )
                ])
            ]
        )
        content_area.controls.append(cat_section)

        # 4. Payment Methods Analysis
        pay_items = []
        for p in payment_modes:
            info = PAYMENT_MAP.get(p["payment_mode"], {})
            color = info.get("color", ModernPalette.ACCENT)
            pay_items.append(
                ft.Container(
                    bgcolor=ModernPalette.SURFACE_DARK,
                    border_radius=12,
                    padding=10,
                    border=ft.Border.all(1, ModernPalette.CARD_BORDER),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=8,
                                controls=[
                                    ft.Icon(info.get("icon", ft.Icons.PAYMENT), size=18, color=color),
                                    ft.Text(p["payment_mode"], size=13, weight=ft.FontWeight.W_600, color=ModernPalette.TEXT_PRIMARY),
                                ]
                            ),
                            ft.Row(
                                spacing=10,
                                controls=[
                                    ft.Text(f"{p['count']} txns", size=11, color=ModernPalette.TEXT_MUTED),
                                    ft.Text(f"{currency} {p['total_amount']:,.0f}", size=13, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                                    ft.Container(
                                        bgcolor="#1E293B",
                                        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                        border_radius=6,
                                        content=ft.Text(f"{p['percent']:.1f}%", size=10, weight=ft.FontWeight.BOLD, color=color)
                                    )
                                ]
                            )
                        ]
                    )
                )
            )

        pay_section = ft.Column(
            spacing=8,
            controls=[
                ft.Text("Payment Mode Distribution", size=14, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                *(pay_items if pay_items else [
                    ft.Container(
                        padding=20,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text("No payment mode data available.", size=12, color=ModernPalette.TEXT_MUTED)
                    )
                ])
            ]
        )
        content_area.controls.append(pay_section)

        # 5. Google Sheets Live Reports Integration Card
        sheet_url = database.get_setting("sheet_url", "").strip()
        sheet_name = database.get_setting("sheet_name", "ExpenseFlow")

        sheets_banner = ft.Container(
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=["#064E3B", "#065F46", "#1E293B"],
            ),
            border_radius=16,
            padding=16,
            border=ft.Border.all(1, "#059669"),
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.TABLE_CHART, color="#34D399", size=22),
                            ft.Text("Google Sheets Live Reports", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ]
                    ),
                    ft.Text(
                        f"Spreadsheet: '{sheet_name}'\n"
                        "Live reports are automatically maintained across isolated user tabs and summary sheets.",
                        size=11,
                        color="#A7F3D0",
                    ),
                    ft.FilledButton(
                        "Open Google Sheet in Browser" if sheet_url else "Configure Google Sheets in Settings",
                        icon=ft.Icons.OPEN_IN_NEW if sheet_url else ft.Icons.SETTINGS,
                        style=ft.ButtonStyle(bgcolor="#10B981", color=ft.Colors.WHITE),
                        url=sheet_url if sheet_url else None,
                        on_click=(lambda _: on_navigate("settings")) if not sheet_url else None,
                    ),
                    *( [
                        ft.Container(
                            bgcolor="rgba(0,0,0,0.25)",
                            border_radius=8,
                            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                            content=ft.Row(
                                spacing=6,
                                controls=[
                                    ft.Icon(ft.Icons.LINK, size=13, color="#34D399"),
                                    ft.Text(sheet_url, size=10, color="#A7F3D0", selectable=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                                ]
                            )
                        )
                    ] if sheet_url else [] )
                ]
            )
        )
        content_area.controls.append(sheets_banner)
        content_area.controls.append(ft.Container(height=30))

    # Header with Month Picker
    month_dropdown = ft.Dropdown(
        value=selected_month[0],
        options=[ft.dropdown.Option(m, f"{m}") for m in available_months] + [ft.dropdown.Option("All", "All Time")],
        width=160,
        dense=True,
        border_radius=12,
        bgcolor=ModernPalette.SURFACE_DARK,
        border_color=ModernPalette.CARD_BORDER,
    )

    def on_month_change(e):
        selected_month[0] = month_dropdown.value
        render_report_data()
        page.update()

    month_dropdown.on_select = on_month_change

    header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Text("Analytics & Reports", size=18, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
            month_dropdown,
        ]
    )

    is_admin = bool(curr_user and curr_user.get("role") == "admin")

    def on_scope_change(scope_val):
        selected_scope[0] = scope_val
        my_chip.selected = (scope_val == "my")
        if is_admin:
            team_chip.selected = (scope_val == "team")
        render_report_data()
        page.update()

    my_chip = ft.Chip(
        label=ft.Text(f"My Reports (@{username_display})"),
        selected=True,
        on_select=lambda _: on_scope_change("my"),
    )
    scope_controls = [my_chip]
    if is_admin:
        team_chip = ft.Chip(
            label=ft.Text("All Team"),
            selected=False,
            on_select=lambda _: on_scope_change("team"),
        )
        scope_controls.append(team_chip)

    scope_row = ft.Row(
        spacing=8,
        controls=scope_controls
    )

    # Initial render
    render_report_data()

    return ft.ListView(
        expand=True,
        spacing=16,
        scroll=ft.ScrollMode.AUTO,
        padding=ft.Padding.only(left=16, right=16, top=16, bottom=120),
        controls=[
            header,
            scope_row,
            content_area,
            ft.Container(height=40),
        ]
    )

