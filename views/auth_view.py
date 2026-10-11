"""
Authentication View (User ID & Password Login / Registration with Email OTP Verification) for ExpenseFlow.
Provides modern, secure user authentication with salted PBKDF2 password hashing and live Gmail OTP verification.
"""
import threading
import time
import flet as ft
import database
from config import ModernPalette, APP_NAME

def build_auth_view(page: ft.Page, on_login_success) -> ft.Control:
    """Builds the mobile login and sign-up view with Email OTP verification."""

    is_register_mode = False
    otp_sent = False
    cooldown_seconds = 0

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
    # Email Input (Placed BEFORE User ID for registration)
    email_input = ft.TextField(
        label="Email ID (Verification required)",
        hint_text="e.g. yourname@gmail.com",
        prefix_icon=ft.Icons.EMAIL_ROUNDED,
        border_radius=14,
        filled=True,
        bgcolor=ModernPalette.SURFACE_DARK,
        border_color=ModernPalette.CARD_BORDER,
        focused_border_color=ModernPalette.PRIMARY,
        keyboard_type=ft.KeyboardType.EMAIL,
        visible=False,
    )

    send_otp_btn = ft.OutlinedButton(
        "Send OTP ✉",
        icon=ft.Icons.MARK_EMAIL_READ_ROUNDED,
        style=ft.ButtonStyle(
            color=ModernPalette.ACCENT,
            side=ft.BorderSide(1, ModernPalette.ACCENT),
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
        height=48,
    )

    otp_input = ft.TextField(
        label="6-Digit Verification Code",
        hint_text="Enter OTP from email",
        prefix_icon=ft.Icons.KEY_ROUNDED,
        border_radius=14,
        filled=True,
        bgcolor=ModernPalette.SURFACE_DARK,
        border_color=ModernPalette.CARD_BORDER,
        focused_border_color=ModernPalette.ACCENT,
        keyboard_type=ft.KeyboardType.NUMBER,
        max_length=6,
        visible=False,
    )

    email_row = ft.Column(
        spacing=8,
        controls=[
            email_input,
            ft.Row(
                alignment=ft.MainAxisAlignment.END,
                controls=[send_otp_btn]
            ),
            otp_input,
        ],
        visible=False,
    )

    username_input = ft.TextField(
        label="User ID or Email",
        hint_text="e.g. admin, alex_99, or user@gmail.com",
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

    # 3. OTP Send Logic with Cooldown Timer
    def handle_send_otp(e):
        nonlocal otp_sent, cooldown_seconds
        em_val = email_input.value.strip() if email_input.value else ""
        if not em_val or "@" not in em_val or "." not in em_val:
            page.show_dialog(ft.SnackBar(ft.Text("Please enter a valid email address first!"), bgcolor=ModernPalette.DANGER))
            return

        send_otp_btn.disabled = True
        send_otp_btn.text = "Sending..."
        page.update()

        u_val = username_input.value.strip() if username_input.value else ""
        ok, msg = database.generate_and_send_registration_otp(em_val, u_val)

        if ok:
            otp_sent = True
            otp_input.visible = True
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"✓ Verification code sent to {em_val}! Check your inbox."),
                    bgcolor=ModernPalette.SUCCESS
                )
            )
            # Start 60s countdown timer
            def countdown():
                nonlocal cooldown_seconds
                cooldown_seconds = 60
                while cooldown_seconds > 0:
                    send_otp_btn.text = f"Resend ({cooldown_seconds}s)"
                    page.update()
                    time.sleep(1)
                    cooldown_seconds -= 1
                send_otp_btn.text = "Resend OTP ✉"
                send_otp_btn.disabled = False
                page.update()

            threading.Thread(target=countdown, daemon=True).start()
        else:
            send_otp_btn.disabled = False
            send_otp_btn.text = "Send OTP ✉"
            page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor=ModernPalette.DANGER))

        page.update()

    send_otp_btn.on_click = handle_send_otp

    # 4. Mode Toggle Buttons (Sign In vs Register)
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
        email_row.visible = register
        email_input.visible = register
        full_name_input.visible = register
        confirm_password_input.visible = register

        if register:
            tab_sign_in.bgcolor = ft.Colors.TRANSPARENT
            tab_sign_in.content.color = ModernPalette.TEXT_MUTED
            tab_register.bgcolor = ModernPalette.PRIMARY
            tab_register.content.color = ft.Colors.WHITE
            action_btn.text = "Verify OTP & Register ➔"
            action_btn.icon = ft.Icons.VERIFIED_USER_ROUNDED
            username_input.label = "User ID / Username"
            username_input.hint_text = "e.g. alex_99, john.doe (Unique)"
        else:
            tab_register.bgcolor = ft.Colors.TRANSPARENT
            tab_register.content.color = ModernPalette.TEXT_MUTED
            tab_sign_in.bgcolor = ModernPalette.PRIMARY
            tab_sign_in.content.color = ft.Colors.WHITE
            action_btn.text = "Sign In ➔"
            action_btn.icon = ft.Icons.LOGIN_ROUNDED
            username_input.label = "User ID or Email"
            username_input.hint_text = "e.g. alex_99 or user@gmail.com"
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

    # 6. Main Action Button & Handler
    def handle_auth_submit(e):
        u_val = username_input.value.strip() if username_input.value else ""
        p_val = password_input.value if password_input.value else ""

        if is_register_mode:
            # Registration Mode
            em_val = email_input.value.strip().lower() if email_input.value else ""
            otp_val = otp_input.value.strip() if otp_input.value else ""
            fn_val = full_name_input.value.strip() if full_name_input.value else u_val
            cp_val = confirm_password_input.value if confirm_password_input.value else ""

            if not em_val or "@" not in em_val or "." not in em_val:
                page.show_dialog(ft.SnackBar(ft.Text("Please enter a valid email address!"), bgcolor=ModernPalette.DANGER))
                return
            if not otp_val or len(otp_val) != 6:
                page.show_dialog(ft.SnackBar(ft.Text("Please enter the 6-digit OTP sent to your email! (Click 'Send OTP' if not received)"), bgcolor=ModernPalette.DANGER))
                return
            if not u_val:
                page.show_dialog(ft.SnackBar(ft.Text("Please choose a User ID / Username!"), bgcolor=ModernPalette.DANGER))
                return
            if len(p_val) < 4:
                page.show_dialog(ft.SnackBar(ft.Text("Password must be at least 4 characters long!"), bgcolor=ModernPalette.DANGER))
                return
            if p_val != cp_val:
                page.show_dialog(ft.SnackBar(ft.Text("Passwords do not match!"), bgcolor=ModernPalette.DANGER))
                return

            # Verify OTP first
            otp_ok, otp_err = database.verify_registration_otp(em_val, otp_val)
            if not otp_ok:
                page.show_dialog(ft.SnackBar(ft.Text(otp_err), bgcolor=ModernPalette.DANGER))
                return

            # Create User Account
            new_user, err = database.create_user(u_val, em_val, p_val, fn_val)
            if err:
                page.show_dialog(ft.SnackBar(ft.Text(err), bgcolor=ModernPalette.DANGER))
                return

            if remember_me_checkbox.value:
                database.set_current_session_user(new_user["id"])
            else:
                database.set_current_session_user(None)

            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"🎉 Welcome, {new_user['full_name']}! Email verified and account registered."),
                    bgcolor=ModernPalette.SUCCESS
                )
            )
            on_login_success(new_user)
        else:
            # Login Mode (Supports both Username and Email)
            if not u_val:
                page.show_dialog(ft.SnackBar(ft.Text("Please enter your User ID or Email!"), bgcolor=ModernPalette.DANGER))
                return
            if not p_val:
                page.show_dialog(ft.SnackBar(ft.Text("Please enter your password!"), bgcolor=ModernPalette.DANGER))
                return

            user = database.authenticate_user(u_val, p_val)
            if not user:
                page.show_dialog(
                    ft.SnackBar(
                        ft.Text("Invalid User ID/Email or Password. (If your account was disabled, contact Admin)."),
                        bgcolor=ModernPalette.DANGER
                    )
                )
                return

            if remember_me_checkbox.value:
                database.set_current_session_user(user["id"])
            else:
                database.set_current_session_user(None)

            role_badge = " [ADMIN]" if user.get("role") == "admin" else ""
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Welcome back, {user['full_name'] or user['username']}{role_badge}!"),
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

    # Security Footer Notice
    security_badge = ft.Container(
        content=ft.Row(
            tight=True,
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.SHIELD_OUTLINED, size=15, color=ModernPalette.TEXT_MUTED),
                ft.Text("Salted PBKDF2 & Real-Time SMTP Email Verification", size=11, color=ModernPalette.TEXT_MUTED),
            ]
        ),
        padding=10,
    )

    return ft.ListView(
        expand=True,
        spacing=14,
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
            # Registration: Email + OTP (placed before username)
            email_row,
            # Inputs
            username_input,
            full_name_input,
            password_input,
            confirm_password_input,
            # Remember me
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    remember_me_checkbox,
                ]
            ),
            action_btn,
            ft.Container(height=10),
            security_badge,
        ]
    )
