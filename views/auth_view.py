"""
Authentication View (User ID & Password Login / Registration) for ExpenseFlow.
Provides modern, secure user authentication with salted PBKDF2 password hashing.
"""
import flet as ft
import database
from config import ModernPalette, APP_NAME

def build_auth_view(page: ft.Page, on_login_success) -> ft.Control:
    """Builds the mobile login and sign-up view."""

    is_register_mode = False

    # 1. Branding Header
    brand_icon = ft.Container(
        content=ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, size=38, color=ft.Colors.WHITE),
        bgcolor=ModernPalette.PRIMARY,
        border_radius=22,
        padding=16,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=["#6366F1", "#4F46E5", "#3730A3"],
        ),
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=16,
            color="#4F46E566",
            offset=ft.Offset(0, 6),
        ),
    )

    title_text = ft.Text(
        APP_NAME,
        size=26,
        weight=ft.FontWeight.BOLD,
        color=ModernPalette.TEXT_PRIMARY,
    )

    subtitle_text = ft.Text(
        "Secure Android Expense Tracker",
        size=13,
        color=ModernPalette.ACCENT,
        weight=ft.FontWeight.W_500,
    )

    # 2. Form Inputs
    username_input = ft.TextField(
        label="User ID / Username",
        hint_text="e.g. admin, alex_99, john.doe",
        prefix_icon=ft.Icons.PERSON_ROUNDED,
        border_radius=14,
        filled=True,
        bgcolor=ModernPalette.SURFACE_DARK,
        border_color=ModernPalette.CARD_BORDER,
        focused_border_color=ModernPalette.PRIMARY,
        autofocus=True,
    )

    full_name_input = ft.TextField(
        label="Full Name",
        hint_text="e.g. Alex Johnson",
        prefix_icon=ft.Icons.BADGE_ROUNDED,
        border_radius=14,
        filled=True,
        bgcolor=ModernPalette.SURFACE_DARK,
        border_color=ModernPalette.CARD_BORDER,
        focused_border_color=ModernPalette.PRIMARY,
        visible=False,
    )

    password_input = ft.TextField(
        label="Password",
        hint_text="Enter your secure password",
        prefix_icon=ft.Icons.LOCK_ROUNDED,
        password=True,
        can_reveal_password=True,
        border_radius=14,
        filled=True,
        bgcolor=ModernPalette.SURFACE_DARK,
        border_color=ModernPalette.CARD_BORDER,
        focused_border_color=ModernPalette.PRIMARY,
    )

    confirm_password_input = ft.TextField(
        label="Confirm Password",
        hint_text="Re-type your password",
        prefix_icon=ft.Icons.LOCK_RESET_ROUNDED,
        password=True,
        can_reveal_password=True,
        border_radius=14,
        filled=True,
        bgcolor=ModernPalette.SURFACE_DARK,
        border_color=ModernPalette.CARD_BORDER,
        focused_border_color=ModernPalette.PRIMARY,
        visible=False,
    )

    remember_me_checkbox = ft.Checkbox(
        label="Keep me signed in",
        value=True,
        fill_color=ModernPalette.PRIMARY,
    )

    # 3. Mode Toggle Buttons (Sign In vs Register)
    tab_sign_in = ft.Container(
        content=ft.Text("Sign In", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        alignment=ft.Alignment.CENTER,
        padding=ft.Padding.symmetric(vertical=10),
        bgcolor=ModernPalette.PRIMARY,
        border_radius=12,
        expand=True,
    )

    tab_register = ft.Container(
        content=ft.Text("Create Account", size=13, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_MUTED),
        alignment=ft.Alignment.CENTER,
        padding=ft.Padding.symmetric(vertical=10),
        bgcolor=ft.Colors.TRANSPARENT,
        border_radius=12,
        expand=True,
    )

    def set_auth_mode(register: bool):
        nonlocal is_register_mode
        is_register_mode = register
        full_name_input.visible = register
        confirm_password_input.visible = register
        
        if register:
            tab_sign_in.bgcolor = ft.Colors.TRANSPARENT
            tab_sign_in.content.color = ModernPalette.TEXT_MUTED
            tab_register.bgcolor = ModernPalette.PRIMARY
            tab_register.content.color = ft.Colors.WHITE
            action_btn.text = "Create Account ➔"
        else:
            tab_register.bgcolor = ft.Colors.TRANSPARENT
            tab_register.content.color = ModernPalette.TEXT_MUTED
            tab_sign_in.bgcolor = ModernPalette.PRIMARY
            tab_sign_in.content.color = ft.Colors.WHITE
            action_btn.text = "Sign In ➔"
        page.update()

    tab_sign_in.on_click = lambda _: set_auth_mode(False)
    tab_register.on_click = lambda _: set_auth_mode(True)

    mode_switcher = ft.Container(
        bgcolor="#1E293B",
        border_radius=14,
        padding=4,
        content=ft.Row(
            spacing=4,
            controls=[tab_sign_in, tab_register]
        )
    )

    # 4. Multi-User Team Member Switcher Chips
    all_users = database.get_all_users()
    team_chips_row = ft.Row(wrap=True, spacing=6, run_spacing=6)

    def select_team_member(uname: str):
        username_input.value = uname
        if uname == "admin":
            password_input.value = "admin123"
        else:
            password_input.value = ""
        page.update()

    for u in all_users:
        u_name = u["username"]
        disp_name = u.get("full_name") or u_name
        team_chips_row.controls.append(
            ft.Container(
                content=ft.Row(
                    tight=True,
                    spacing=5,
                    controls=[
                        ft.Icon(ft.Icons.PERSON, size=13, color=ModernPalette.ACCENT),
                        ft.Text(f"@{u_name}", size=11, weight=ft.FontWeight.W_600, color=ModernPalette.TEXT_PRIMARY),
                    ]
                ),
                bgcolor="#1E293B",
                border=ft.Border.all(1, ModernPalette.CARD_BORDER),
                border_radius=12,
                padding=ft.Padding.symmetric(horizontal=8, vertical=5),
                on_click=lambda _, name=u_name: select_team_member(name),
                tooltip=f"Log in as @{u_name} ({disp_name})",
            )
        )

    team_members_card = ft.Container(
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("Active Team Accounts:", size=11, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_MUTED),
                        ft.Text(f"{len(all_users)} registered", size=10, color=ModernPalette.ACCENT),
                    ]
                ),
                team_chips_row,
            ]
        ),
        bgcolor="#0B132B",
        border=ft.Border.all(1, "#1E293B"),
        border_radius=12,
        padding=10,
    )

    # Quick Demo Autofill Chip
    def autofill_demo(e):
        username_input.value = "admin"
        password_input.value = "admin123"
        page.update()
        page.show_dialog(
            ft.SnackBar(
                ft.Text("Demo credentials filled: admin / admin123"),
                bgcolor=ModernPalette.INFO
            )
        )

    demo_chip = ft.Container(
        content=ft.Row(
            tight=True,
            spacing=6,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.FLASH_ON_ROUNDED, size=15, color=ModernPalette.ACCENT),
                ft.Text("Default Admin: admin / admin123 (Tap to fill)", size=11, weight=ft.FontWeight.W_600, color=ModernPalette.ACCENT),
            ]
        ),
        bgcolor="#0F2840",
        border=ft.Border.all(1, "#1E40AF"),
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        on_click=autofill_demo,
        tooltip="Click to quickly fill admin credentials",
    )

    # 5. Main Action Button & Handler
    def handle_auth_submit(e):
        u_val = username_input.value.strip() if username_input.value else ""
        p_val = password_input.value if password_input.value else ""

        if not u_val:
            page.show_dialog(ft.SnackBar(ft.Text("Please enter your User ID / Username!"), bgcolor=ModernPalette.DANGER))
            return
        if not p_val:
            page.show_dialog(ft.SnackBar(ft.Text("Please enter your password!"), bgcolor=ModernPalette.DANGER))
            return

        if is_register_mode:
            # Registration Mode
            fn_val = full_name_input.value.strip() if full_name_input.value else u_val
            cp_val = confirm_password_input.value if confirm_password_input.value else ""
            
            if p_val != cp_val:
                page.show_dialog(ft.SnackBar(ft.Text("Passwords do not match!"), bgcolor=ModernPalette.DANGER))
                return
            
            new_user, err = database.create_user(u_val, p_val, fn_val)
            if err:
                page.show_dialog(ft.SnackBar(ft.Text(err), bgcolor=ModernPalette.DANGER))
                return
            
            if remember_me_checkbox.value:
                database.set_current_session_user(new_user["id"])
            else:
                database.set_current_session_user(None)

            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Welcome, {new_user['full_name']}! Account created successfully."),
                    bgcolor=ModernPalette.SUCCESS
                )
            )
            on_login_success(new_user)
        else:
            # Login Mode
            user = database.authenticate_user(u_val, p_val)
            if not user:
                page.show_dialog(
                    ft.SnackBar(
                        ft.Text("Invalid User ID or Password. Please try again!"),
                        bgcolor=ModernPalette.DANGER
                    )
                )
                return

            if remember_me_checkbox.value:
                database.set_current_session_user(user["id"])
            else:
                database.set_current_session_user(None)

            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Welcome back, {user['full_name'] or user['username']}!"),
                    bgcolor=ModernPalette.SUCCESS
                )
            )
            on_login_success(user)

    action_btn = ft.FilledButton(
        "Sign In ➔",
        icon=ft.Icons.LOGIN_ROUNDED,
        style=ft.ButtonStyle(
            bgcolor=ModernPalette.PRIMARY,
            color=ft.Colors.WHITE,
            padding=ft.Padding.all(16),
            shape=ft.RoundedRectangleBorder(radius=14),
        ),
        width=float("inf"),
        on_click=handle_auth_submit,
    )

    # 6. Security Footer Notice
    security_badge = ft.Container(
        content=ft.Row(
            tight=True,
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.SHIELD_OUTLINED, size=15, color=ModernPalette.TEXT_MUTED),
                ft.Text("Salted PBKDF2 Encryption & Offline SQLite", size=11, color=ModernPalette.TEXT_MUTED),
            ]
        ),
        padding=10,
    )

    return ft.ListView(
        expand=True,
        spacing=16,
        scroll=ft.ScrollMode.AUTO,
        padding=ft.Padding.only(left=20, right=20, top=30, bottom=50),
        controls=[
            ft.Container(height=10),
            # Brand Header
            ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                controls=[
                    brand_icon,
                    title_text,
                    subtitle_text,
                ]
            ),
            ft.Container(height=6),
            # Switcher: Sign In / Create Account
            mode_switcher,
            # Inputs
            username_input,
            full_name_input,
            password_input,
            confirm_password_input,
            # Team Accounts Quick Switcher
            team_members_card,
            # Remember me & Quick Demo
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    remember_me_checkbox,
                ]
            ),
            action_btn,
            ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[demo_chip]
            ),
            ft.Container(height=10),
            security_badge,
        ]
    )
