"""
ExpenseFlow - Dedicated PC/Laptop Administrator Control Console (admin_app.py).
Provides full administrative management for registered users, password resets,
account activation/deactivation, role assignments, and live metric tracking.
Runs natively on desktop/laptop with Flet.
"""
import secrets
import flet as ft
import database
import email_service
from config import ModernPalette, APP_NAME, APP_VERSION

def main(page: ft.Page):
    database.init_db()

    # Desktop Window Styling
    page.title = f"{APP_NAME} - Admin Management Console"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ModernPalette.BG_DARK
    page.padding = 24
    page.window.width = 1100
    page.window.height = 800
    page.window.min_width = 850
    page.window.min_height = 650

    search_query = ""
    status_filter = "ALL"  # ALL, ACTIVE, DEACTIVATED, ADMIN

    # Data Container for User Cards
    users_column = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    # Stat Card References
    total_users_text = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    active_users_text = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=ModernPalette.SUCCESS)
    deactivated_users_text = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=ModernPalette.DANGER)
    total_spend_text = ft.Text("₹0.00", size=24, weight=ft.FontWeight.BOLD, color=ModernPalette.ACCENT)

    def create_stat_card(title: str, control: ft.Control, icon, icon_color: str, bg_color: str):
        return ft.Container(
            expand=True,
            bgcolor=ModernPalette.SURFACE_DARK,
            border_radius=16,
            padding=18,
            border=ft.Border.all(1, ModernPalette.CARD_BORDER),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text(title, size=12, weight=ft.FontWeight.W_600, color=ModernPalette.TEXT_MUTED),
                            control,
                        ]
                    ),
                    ft.Container(
                        content=ft.Icon(icon, size=24, color=icon_color),
                        bgcolor=bg_color,
                        border_radius=12,
                        padding=12,
                    )
                ]
            )
        )

    # Action Dialog: Reset Password
    def open_reset_password_modal(user: dict):
        new_pwd_input = ft.TextField(
            label="New Password",
            hint_text="Enter new secure password",
            password=True,
            can_reveal_password=True,
            filled=True,
            bgcolor=ModernPalette.SURFACE_DARK,
            border_radius=12,
            border_color=ModernPalette.CARD_BORDER,
        )

        send_email_cb = ft.Checkbox(
            label=f"Email new password to user ({user.get('email', 'No Email')})",
            value=bool(user.get("email") and user.get("email") != "N/A"),
            disabled=not bool(user.get("email") and user.get("email") != "N/A"),
            fill_color=ModernPalette.PRIMARY,
        )

        def generate_random_pwd(_):
            new_pwd_input.value = secrets.token_urlsafe(8)
            page.update()

        def confirm_reset(_):
            pwd = new_pwd_input.value.strip() if new_pwd_input.value else ""
            if len(pwd) < 4:
                page.show_dialog(ft.SnackBar(ft.Text("Password must be at least 4 characters long!"), bgcolor=ModernPalette.DANGER))
                return

            ok, msg = database.admin_reset_user_password(user["id"], pwd, send_email=send_email_cb.value)
            page.pop_dialog()
            page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor=ModernPalette.SUCCESS if ok else ModernPalette.DANGER))
            load_users()

        dlg = ft.AlertDialog(
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.KEY_ROUNDED, color=ModernPalette.PRIMARY),
                    ft.Text(f"Reset Password for @{user['username']}", size=18, weight=ft.FontWeight.BOLD),
                ]
            ),
            content=ft.Column(
                tight=True,
                spacing=14,
                controls=[
                    ft.Text(f"User: {user['full_name']} ({user['email']})", size=13, color=ModernPalette.TEXT_MUTED),
                    new_pwd_input,
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.TextButton("🎲 Generate Random Password", on_click=generate_random_pwd),
                        ]
                    ),
                    send_email_cb,
                ]
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton("Confirm Password Reset", on_click=confirm_reset, style=ft.ButtonStyle(bgcolor=ModernPalette.PRIMARY)),
            ]
        )
        page.show_dialog(dlg)

    # Action Dialog: Toggle Status (Activate / Deactivate)
    def toggle_user_active_status(user: dict):
        new_status = 0 if user["is_active"] == 1 else 1
        ok, msg = database.admin_toggle_user_status(user["id"], new_status)
        page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor=ModernPalette.SUCCESS if ok else ModernPalette.DANGER))
        load_users()

    # Action Dialog: Toggle Role (Admin <-> User)
    def toggle_user_role(user: dict):
        new_role = "user" if user["role"] == "admin" else "admin"
        ok, msg = database.admin_update_user_role(user["id"], new_role)
        page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor=ModernPalette.SUCCESS if ok else ModernPalette.DANGER))
        load_users()

    # Action Dialog: Delete User
    def open_delete_modal(user: dict):
        def confirm_delete(_):
            ok, msg = database.admin_delete_user(user["id"])
            page.pop_dialog()
            page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor=ModernPalette.SUCCESS if ok else ModernPalette.DANGER))
            load_users()

        dlg = ft.AlertDialog(
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.WARNING_ROUNDED, color=ModernPalette.DANGER),
                    ft.Text("Confirm User Deletion", size=18, weight=ft.FontWeight.BOLD),
                ]
            ),
            content=ft.Text(
                f"Are you sure you want to delete user '@{user['username']}' ({user['full_name']})?\n\n"
                f"All {user.get('expenses_count', 0)} expenses associated with this user will also be permanently deleted.",
                size=13
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton("Delete Permanently", on_click=confirm_delete, style=ft.ButtonStyle(bgcolor=ModernPalette.DANGER)),
            ]
        )
        page.show_dialog(dlg)

    # Action Dialog: Add New User / Admin directly
    def open_create_user_modal(_):
        u_in = ft.TextField(label="User ID / Username (Unique)", filled=True, bgcolor=ModernPalette.SURFACE_DARK, border_radius=12)
        em_in = ft.TextField(label="Email Address (Unique)", filled=True, bgcolor=ModernPalette.SURFACE_DARK, border_radius=12)
        fn_in = ft.TextField(label="Full Name", filled=True, bgcolor=ModernPalette.SURFACE_DARK, border_radius=12)
        pw_in = ft.TextField(label="Password", password=True, can_reveal_password=True, filled=True, bgcolor=ModernPalette.SURFACE_DARK, border_radius=12)
        role_dd = ft.Dropdown(
            label="Role",
            value="user",
            options=[
                ft.dropdown.Option("user", "Standard User (Limited Rights)"),
                ft.dropdown.Option("admin", "Administrator (Full Rights)"),
            ],
            filled=True,
            bgcolor=ModernPalette.SURFACE_DARK,
            border_radius=12,
        )

        def save_new_user(_):
            u = u_in.value.strip() if u_in.value else ""
            em = em_in.value.strip() if em_in.value else ""
            fn = fn_in.value.strip() if fn_in.value else u
            pw = pw_in.value if pw_in.value else ""
            r = role_dd.value or "user"

            new_u, err = database.create_user(u, em, pw, fn, role=r)
            if err:
                page.show_dialog(ft.SnackBar(ft.Text(err), bgcolor=ModernPalette.DANGER))
                return

            page.pop_dialog()
            page.show_dialog(ft.SnackBar(ft.Text(f"User '{u}' created successfully!"), bgcolor=ModernPalette.SUCCESS))
            load_users()

        dlg = ft.AlertDialog(
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.PERSON_ADD_ROUNDED, color=ModernPalette.PRIMARY),
                    ft.Text("Register New User / Admin", size=18, weight=ft.FontWeight.BOLD),
                ]
            ),
            content=ft.Column(
                tight=True,
                spacing=12,
                controls=[em_in, u_in, fn_in, pw_in, role_dd]
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton("Create Account", on_click=save_new_user, style=ft.ButtonStyle(bgcolor=ModernPalette.PRIMARY)),
            ]
        )
        page.show_dialog(dlg)

    def load_users():
        users = database.admin_get_all_users()

        # Update stats
        total_cnt = len(users)
        active_cnt = sum(1 for u in users if u["is_active"] == 1)
        deact_cnt = sum(1 for u in users if u["is_active"] == 0)
        total_spent = sum(u.get("total_spend", 0.0) for u in users)

        total_users_text.value = str(total_cnt)
        active_users_text.value = str(active_cnt)
        deactivated_users_text.value = str(deact_cnt)
        total_spend_text.value = f"₹{total_spent:,.2f}"

        # Filter users
        filtered = []
        for u in users:
            # Status Filter
            if status_filter == "ACTIVE" and u["is_active"] != 1:
                continue
            if status_filter == "DEACTIVATED" and u["is_active"] != 0:
                continue
            if status_filter == "ADMIN" and u["role"] != "admin":
                continue

            # Search Query Filter
            if search_query:
                q = search_query.lower()
                matches = (
                    q in u["username"].lower() or
                    q in (u.get("email") or "").lower() or
                    q in (u.get("full_name") or "").lower()
                )
                if not matches:
                    continue
            filtered.append(u)

        users_column.controls.clear()

        if not filtered:
            users_column.controls.append(
                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    padding=40,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, size=48, color=ModernPalette.TEXT_MUTED),
                            ft.Text("No registered users match the search criteria.", size=14, color=ModernPalette.TEXT_MUTED),
                        ]
                    )
                )
            )
            page.update()
            return

        for u in filtered:
            is_active = (u["is_active"] == 1)
            is_admin = (u["role"] == "admin" or u["username"] == "admin")
            is_primary_admin = (u["username"] == "admin")

            # Role badge
            role_badge = ft.Container(
                content=ft.Text("ADMIN" if is_admin else "USER", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                bgcolor=ModernPalette.WARNING if is_admin else ModernPalette.PRIMARY,
                border_radius=8,
                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            )

            # Status badge
            status_badge = ft.Container(
                content=ft.Row(
                    tight=True,
                    spacing=4,
                    controls=[
                        ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED if is_active else ft.Icons.BLOCK_ROUNDED, size=12, color=ModernPalette.SUCCESS if is_active else ModernPalette.DANGER),
                        ft.Text("Active" if is_active else "Deactivated", size=10, weight=ft.FontWeight.BOLD, color=ModernPalette.SUCCESS if is_active else ModernPalette.DANGER),
                    ]
                ),
                bgcolor="#132E27" if is_active else "#361616",
                border=ft.Border.all(1, ModernPalette.SUCCESS if is_active else ModernPalette.DANGER),
                border_radius=8,
                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            )

            # User Row Card
            user_card = ft.Container(
                bgcolor=ModernPalette.SURFACE_DARK,
                border_radius=14,
                padding=16,
                border=ft.Border.all(1, ModernPalette.CARD_BORDER),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        # Left Details
                        ft.Row(
                            spacing=14,
                            controls=[
                                ft.Container(
                                    content=ft.Icon(ft.Icons.SECURITY_ROUNDED if is_admin else ft.Icons.PERSON_ROUNDED, size=24, color=ft.Colors.WHITE),
                                    bgcolor=ModernPalette.WARNING if is_admin else ModernPalette.PRIMARY,
                                    border_radius=14,
                                    padding=12,
                                ),
                                ft.Column(
                                    spacing=3,
                                    controls=[
                                        ft.Row(
                                            spacing=8,
                                            controls=[
                                                ft.Text(u["full_name"], size=15, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                                                ft.Text(f"(@{u['username']})", size=13, color=ModernPalette.TEXT_MUTED),
                                                role_badge,
                                                status_badge,
                                            ]
                                        ),
                                        ft.Row(
                                            spacing=14,
                                            controls=[
                                                ft.Row(
                                                    tight=True,
                                                    spacing=4,
                                                    controls=[
                                                        ft.Icon(ft.Icons.EMAIL_OUTLINED, size=13, color=ModernPalette.ACCENT),
                                                        ft.Text(u["email"], size=12, color=ModernPalette.ACCENT),
                                                    ]
                                                ),
                                                ft.Row(
                                                    tight=True,
                                                    spacing=4,
                                                    controls=[
                                                        ft.Icon(ft.Icons.RECEIPT_LONG_ROUNDED, size=13, color=ModernPalette.TEXT_MUTED),
                                                        ft.Text(f"{u['expenses_count']} expenses (₹{u['total_spend']:,.0f})", size=12, color=ModernPalette.TEXT_MUTED),
                                                    ]
                                                ),
                                                ft.Row(
                                                    tight=True,
                                                    spacing=4,
                                                    controls=[
                                                        ft.Icon(ft.Icons.CALENDAR_TODAY_ROUNDED, size=13, color=ModernPalette.TEXT_MUTED),
                                                        ft.Text(f"Joined: {u['created_at'][:10]}", size=12, color=ModernPalette.TEXT_MUTED),
                                                    ]
                                                ),
                                            ]
                                        )
                                    ]
                                )
                            ]
                        ),
                        # Right Actions
                        ft.Row(
                            spacing=6,
                            controls=[
                                # Reset Password Button
                                ft.OutlinedButton(
                                    "Reset Password",
                                    icon=ft.Icons.LOCK_RESET_ROUNDED,
                                    style=ft.ButtonStyle(
                                        color=ModernPalette.ACCENT,
                                        side=ft.BorderSide(1, ModernPalette.ACCENT),
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                    ),
                                    on_click=lambda _, usr=u: open_reset_password_modal(usr),
                                    tooltip=f"Reset password for @{u['username']}",
                                ),
                                # Toggle Status Button
                                ft.IconButton(
                                    icon=ft.Icons.TOGGLE_ON_ROUNDED if is_active else ft.Icons.TOGGLE_OFF_ROUNDED,
                                    icon_color=ModernPalette.SUCCESS if is_active else ModernPalette.TEXT_MUTED,
                                    icon_size=28,
                                    tooltip="Deactivate account" if is_active else "Activate account",
                                    disabled=is_primary_admin,
                                    on_click=lambda _, usr=u: toggle_user_active_status(usr),
                                ),
                                # Toggle Role Button
                                ft.IconButton(
                                    icon=ft.Icons.ADMIN_PANEL_SETTINGS_ROUNDED,
                                    icon_color=ModernPalette.WARNING if is_admin else ModernPalette.TEXT_MUTED,
                                    icon_size=20,
                                    tooltip="Demote to User" if is_admin else "Promote to Admin",
                                    disabled=is_primary_admin,
                                    on_click=lambda _, usr=u: toggle_user_role(usr),
                                ),
                                # Delete Button
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                                    icon_color=ModernPalette.DANGER,
                                    icon_size=20,
                                    tooltip="Delete user account",
                                    disabled=is_primary_admin,
                                    on_click=lambda _, usr=u: open_delete_modal(usr),
                                ),
                            ]
                        )
                    ]
                )
            )
            users_column.controls.append(user_card)

        page.update()

    # Search Box handler
    def on_search_change(e):
        nonlocal search_query
        search_query = e.control.value.strip()
        load_users()

    search_input = ft.TextField(
        hint_text="Search users by name, username (@), or email...",
        prefix_icon=ft.Icons.SEARCH_ROUNDED,
        filled=True,
        bgcolor=ModernPalette.SURFACE_DARK,
        border_radius=14,
        border_color=ModernPalette.CARD_BORDER,
        expand=True,
        on_change=on_search_change,
    )

    # Filter chips
    def select_filter(val: str):
        nonlocal status_filter
        status_filter = val
        for btn in filter_buttons_row.controls:
            btn.style.bgcolor = ModernPalette.PRIMARY if btn.data == val else ModernPalette.SURFACE_DARK
            btn.style.color = ft.Colors.WHITE if btn.data == val else ModernPalette.TEXT_MUTED
        load_users()

    filter_buttons_row = ft.Row(
        spacing=8,
        controls=[
            ft.FilledButton("All Users", data="ALL", style=ft.ButtonStyle(bgcolor=ModernPalette.PRIMARY, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=10)), on_click=lambda _: select_filter("ALL")),
            ft.FilledButton("Active Only", data="ACTIVE", style=ft.ButtonStyle(bgcolor=ModernPalette.SURFACE_DARK, color=ModernPalette.TEXT_MUTED, shape=ft.RoundedRectangleBorder(radius=10)), on_click=lambda _: select_filter("ACTIVE")),
            ft.FilledButton("Deactivated", data="DEACTIVATED", style=ft.ButtonStyle(bgcolor=ModernPalette.SURFACE_DARK, color=ModernPalette.TEXT_MUTED, shape=ft.RoundedRectangleBorder(radius=10)), on_click=lambda _: select_filter("DEACTIVATED")),
            ft.FilledButton("Admins", data="ADMIN", style=ft.ButtonStyle(bgcolor=ModernPalette.SURFACE_DARK, color=ModernPalette.TEXT_MUTED, shape=ft.RoundedRectangleBorder(radius=10)), on_click=lambda _: select_filter("ADMIN")),
        ]
    )

    # Database Status Indicator
    db_name = database.get_db_type()
    db_pill = ft.Container(
        content=ft.Row(
            tight=True,
            spacing=6,
            controls=[
                ft.Icon(ft.Icons.STORAGE_ROUNDED, size=14, color=ModernPalette.SUCCESS if database.is_using_mysql() else ModernPalette.WARNING),
                ft.Text(db_name, size=11, weight=ft.FontWeight.W_600, color=ModernPalette.TEXT_PRIMARY),
            ]
        ),
        bgcolor="#1E293B",
        border_radius=12,
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        border=ft.Border.all(1, ModernPalette.CARD_BORDER),
    )

    # Top App Bar / Header
    header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Row(
                spacing=12,
                controls=[
                    ft.Container(
                        content=ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS_ROUNDED, size=28, color=ft.Colors.WHITE),
                        bgcolor=ModernPalette.PRIMARY,
                        border_radius=14,
                        padding=10,
                        gradient=ft.LinearGradient(
                            begin=ft.Alignment.TOP_LEFT,
                            end=ft.Alignment.BOTTOM_RIGHT,
                            colors=["#4F46E5", "#3730A3"],
                        )
                    ),
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(f"{APP_NAME} Admin Console", size=20, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                            ft.Text("Role-Based User Management & Security Control", size=12, color=ModernPalette.TEXT_MUTED),
                        ]
                    )
                ]
            ),
            ft.Row(
                spacing=10,
                controls=[
                    db_pill,
                    ft.IconButton(
                        icon=ft.Icons.REFRESH_ROUNDED,
                        icon_color=ModernPalette.ACCENT,
                        tooltip="Refresh user list & metrics",
                        on_click=lambda _: load_users(),
                    ),
                    ft.FilledButton(
                        "+ Add New User",
                        icon=ft.Icons.PERSON_ADD_ROUNDED,
                        style=ft.ButtonStyle(
                            bgcolor=ModernPalette.PRIMARY,
                            color=ft.Colors.WHITE,
                            shape=ft.RoundedRectangleBorder(radius=12),
                            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                        ),
                        on_click=open_create_user_modal,
                    )
                ]
            )
        ]
    )

    # Stats Row
    stats_row = ft.Row(
        spacing=14,
        controls=[
            create_stat_card("Total Registered Users", total_users_text, ft.Icons.PEOPLE_ROUNDED, ModernPalette.PRIMARY_LIGHT, "#2E365E"),
            create_stat_card("Active Accounts", active_users_text, ft.Icons.CHECK_CIRCLE_ROUNDED, ModernPalette.SUCCESS, "#16382B"),
            create_stat_card("Deactivated / Blocked", deactivated_users_text, ft.Icons.BLOCK_ROUNDED, ModernPalette.DANGER, "#3D1A1A"),
            create_stat_card("Total System Expenses", total_spend_text, ft.Icons.CURRENCY_RUPEE_ROUNDED, ModernPalette.ACCENT, "#15354A"),
        ]
    )

    # Search & Filter Toolbar
    toolbar = ft.Row(
        spacing=12,
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            search_input,
            filter_buttons_row,
        ]
    )

    page.add(
        ft.Column(
            expand=True,
            spacing=18,
            controls=[
                header,
                stats_row,
                toolbar,
                users_column,
            ]
        )
    )

    load_users()

if __name__ == "__main__":
    ft.app(target=main)
