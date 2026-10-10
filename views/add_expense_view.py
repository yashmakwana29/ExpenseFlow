"""
Add / Edit Expense View for ExpenseFlow.
Allows quick expense entry with category chips, payment mode selectors,
date picker, quick amount buttons, and instant Google Sheets sync.
"""
import datetime
import flet as ft
import database
from config import CATEGORIES, PAYMENT_MODES, ModernPalette

def build_add_expense_view(page: ft.Page, on_navigate, on_expense_saved, edit_id: int = None) -> ft.Control:
    """Builds the Add / Edit Expense screen."""
    
    currency = database.get_setting("currency_symbol", "₹")
    existing_data = database.get_expense_by_id(edit_id) if edit_id else None
    
    # State variables
    initial_amount = str(existing_data["amount"]) if existing_data else ""
    initial_title = existing_data["title"] if existing_data else ""
    all_categories = database.get_categories()
    initial_cat = existing_data["category"] if existing_data else (all_categories[0]["key"] if all_categories else "Other")
    initial_pay = existing_data["payment_mode"] if existing_data else PAYMENT_MODES[0]["key"]
    initial_date = existing_data["date"] if existing_data else datetime.date.today().strftime("%Y-%m-%d")
    initial_notes = existing_data["notes"] if existing_data else ""
    
    selected_category = initial_cat
    selected_payment = initial_pay
    selected_date = initial_date

    current_user = database.get_current_session_user()
    curr_username = current_user["username"] if current_user else "admin"

    # 1. Title / Header
    header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Column(
                spacing=2,
                controls=[
                    ft.Text(
                        "Edit Expense" if edit_id else "Add New Expense",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=ModernPalette.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        f"Recording as @{curr_username}",
                        size=11,
                        weight=ft.FontWeight.W_500,
                        color=ModernPalette.ACCENT,
                    ),
                ]
            ),
            ft.IconButton(
                icon=ft.Icons.CLOSE,
                icon_color=ModernPalette.TEXT_MUTED,
                on_click=lambda _: on_navigate("dashboard"),
            )
        ]
    )

    # 2. Amount Input
    amount_input = ft.TextField(
        value=initial_amount,
        label="Amount",
        prefix=ft.Text(f"{currency} ", size=20, weight=ft.FontWeight.BOLD, color=ModernPalette.PRIMARY),
        text_style=ft.TextStyle(size=24, weight=ft.FontWeight.BOLD),
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=14,
        filled=True,
        bgcolor=ModernPalette.SURFACE_DARK,
        border_color=ModernPalette.PRIMARY,
        focused_border_color=ModernPalette.ACCENT,
        autofocus=True,
    )

    # Quick Amount Buttons
    def add_to_amount(val: float):
        try:
            curr = float(amount_input.value) if amount_input.value else 0.0
            amount_input.value = f"{curr + val:.0f}"
        except ValueError:
            amount_input.value = f"{val:.0f}"
        page.update()

    def make_quick_btn(val: int):
        return ft.Container(
            content=ft.Text(f"+{currency}{val}", size=12, weight=ft.FontWeight.W_600, color=ModernPalette.ACCENT),
            bgcolor=ModernPalette.SURFACE_DARK,
            border=ft.Border.all(1, ModernPalette.CARD_BORDER),
            border_radius=12,
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            on_click=lambda _: add_to_amount(val),
        )

    quick_amount_row = ft.Row(
        wrap=True,
        spacing=8,
        run_spacing=8,
        controls=[
            make_quick_btn(50),
            make_quick_btn(100),
            make_quick_btn(200),
            make_quick_btn(500),
            make_quick_btn(1000),
        ]
    )

    # 3. Description / Title Input
    title_input = ft.TextField(
        value=initial_title,
        label="Description / Merchant",
        hint_text="e.g. Starbucks, Groceries, Metro Card",
        border_radius=14,
        filled=True,
        bgcolor=ModernPalette.SURFACE_DARK,
        border_color=ModernPalette.CARD_BORDER,
        focused_border_color=ModernPalette.PRIMARY,
    )

    # 4. Category Selector (Horizontal chips with dynamic list & auto-detect creator)
    cat_chips_container = ft.Row(wrap=True, spacing=8, run_spacing=8)

    def select_cat(cat_key: str):
        nonlocal selected_category
        selected_category = cat_key
        render_cat_chips()
        page.update()

    def open_add_category_dialog():
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
            nonlocal selected_category
            selected_category = new_cat["key"]
            render_cat_chips()
            page.update()
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Added category '{new_cat['key']}' with auto-detected symbol!"),
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

    def render_cat_chips():
        cat_chips_container.controls.clear()
        categories_list = database.get_categories()
        for cat in categories_list:
            is_active = (cat["key"] == selected_category)
            cat_chips_container.controls.append(
                ft.Container(
                    content=ft.Row(
                        spacing=5,
                        tight=True,
                        controls=[
                            ft.Icon(cat["icon"], size=15, color=cat["color"]),
                            ft.Text(cat["label"], size=11, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE if is_active else ModernPalette.TEXT_MUTED),
                        ]
                    ),
                    bgcolor="#312E81" if is_active else ModernPalette.SURFACE_DARK,
                    border=ft.Border.all(1.5 if is_active else 1, ModernPalette.PRIMARY if is_active else ModernPalette.CARD_BORDER),
                    border_radius=14,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                    on_click=lambda _, k=cat["key"]: select_cat(k),
                )
            )

        # Add Category Button Chip
        cat_chips_container.controls.append(
            ft.Container(
                content=ft.Row(
                    spacing=5,
                    tight=True,
                    controls=[
                        ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, size=15, color=ModernPalette.ACCENT),
                        ft.Text("+ Add Category", size=11, weight=ft.FontWeight.BOLD, color=ModernPalette.ACCENT),
                    ]
                ),
                bgcolor="#0F2840",
                border=ft.Border.all(1.5, ModernPalette.ACCENT),
                border_radius=14,
                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                on_click=lambda _: open_add_category_dialog(),
                tooltip="Create a custom category with auto-detected icon",
            )
        )

    render_cat_chips()

    # 5. Payment Mode Selector
    pay_chips_container = ft.Row(wrap=True, spacing=8, run_spacing=8)

    def select_pay(pay_key: str):
        nonlocal selected_payment
        selected_payment = pay_key
        render_pay_chips()
        page.update()

    def render_pay_chips():
        pay_chips_container.controls.clear()
        for p in PAYMENT_MODES:
            is_active = (p["key"] == selected_payment)
            pay_chips_container.controls.append(
                ft.Container(
                    content=ft.Row(
                        spacing=5,
                        tight=True,
                        controls=[
                            ft.Icon(p["icon"], size=15, color=p["color"]),
                            ft.Text(p["key"], size=11, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE if is_active else ModernPalette.TEXT_MUTED),
                        ]
                    ),
                    bgcolor="#1E3A8A" if is_active else ModernPalette.SURFACE_DARK,
                    border=ft.Border.all(1.5 if is_active else 1, ModernPalette.ACCENT if is_active else ModernPalette.CARD_BORDER),
                    border_radius=14,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                    on_click=lambda _, k=p["key"]: select_pay(k),
                )
            )

    render_pay_chips()

    # 6. Date Selector
    date_display = ft.Text(selected_date, size=14, weight=ft.FontWeight.W_600, color=ModernPalette.TEXT_PRIMARY)

    def on_date_picked(e):
        nonlocal selected_date
        if date_picker.value:
            selected_date = date_picker.value.strftime("%Y-%m-%d")
            date_display.value = selected_date
            page.update()

    date_picker = ft.DatePicker(
        on_change=on_date_picked,
        first_date=datetime.datetime(2020, 1, 1),
        last_date=datetime.datetime(2035, 12, 31),
    )

    def open_date_picker(e):
        page.show_dialog(date_picker)

    date_card = ft.Container(
        bgcolor=ModernPalette.SURFACE_DARK,
        border_radius=14,
        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        border=ft.Border.all(1, ModernPalette.CARD_BORDER),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(
                    spacing=10,
                    controls=[
                        ft.Icon(ft.Icons.CALENDAR_MONTH, color=ModernPalette.PRIMARY, size=20),
                        date_display,
                    ]
                ),
                ft.TextButton("Change Date", on_click=open_date_picker)
            ]
        )
    )

    # 7. Notes Input
    notes_input = ft.TextField(
        value=initial_notes,
        label="Notes / Remarks (Optional)",
        hint_text="e.g. Bill #123, with team, reimbursement",
        multiline=True,
        min_lines=2,
        max_lines=3,
        border_radius=14,
        filled=True,
        bgcolor=ModernPalette.SURFACE_DARK,
        border_color=ModernPalette.CARD_BORDER,
    )

    # 8. Save Button
    save_button = ft.FilledButton(
        "Update Expense" if edit_id else "Save & Auto-Sync to Google Sheets",
        icon=ft.Icons.SAVE,
        style=ft.ButtonStyle(
            bgcolor=ModernPalette.PRIMARY,
            color=ft.Colors.WHITE,
            padding=ft.Padding.all(16),
            shape=ft.RoundedRectangleBorder(radius=14),
        ),
        width=float("inf"),
    )

    def save_expense_handler(e):
        # Validate amount
        try:
            amt = float(amount_input.value)
            if amt <= 0:
                raise ValueError()
        except Exception:
            page.show_dialog(ft.SnackBar(ft.Text("Please enter a valid expense amount!"), bgcolor=ModernPalette.DANGER))
            return

        # Validate title
        title = title_input.value.strip()
        if not title:
            title = selected_category  # default to category name if title is empty

        if edit_id:
            database.update_expense(
                expense_id=edit_id,
                title=title,
                amount=amt,
                category=selected_category,
                payment_mode=selected_payment,
                date=selected_date,
                notes=notes_input.value.strip()
            )
            saved_item = database.get_expense_by_id(edit_id)
            page.show_dialog(ft.SnackBar(ft.Text("Expense updated successfully!"), bgcolor=ModernPalette.SUCCESS))
        else:
            saved_item = database.add_expense(
                title=title,
                amount=amt,
                category=selected_category,
                payment_mode=selected_payment,
                date=selected_date,
                notes=notes_input.value.strip(),
                synced=0
            )
            page.show_dialog(ft.SnackBar(ft.Text(f"Saved {currency}{amt:,.2f} for {title}!"), bgcolor=ModernPalette.SUCCESS))

        # Trigger auto-sync callback
        on_expense_saved(saved_item)
        on_navigate("dashboard")

    save_button.on_click = save_expense_handler

    return ft.ListView(
        expand=True,
        spacing=16,
        scroll=ft.ScrollMode.AUTO,
        padding=ft.Padding.only(left=16, right=16, top=16, bottom=120),
        controls=[
            header,
            amount_input,
            quick_amount_row,
            title_input,
            # Category label & chips
            ft.Column(
                spacing=6,
                controls=[
                    ft.Text("Select Category", size=13, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                    cat_chips_container,
                ]
            ),
            # Payment mode label & chips
            ft.Column(
                spacing=6,
                controls=[
                    ft.Text("Payment Mode", size=13, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                    pay_chips_container,
                ]
            ),
            # Date
            ft.Column(
                spacing=6,
                controls=[
                    ft.Text("Date", size=13, weight=ft.FontWeight.BOLD, color=ModernPalette.TEXT_PRIMARY),
                    date_card,
                ]
            ),
            notes_input,
            save_button,
            ft.Container(height=40),
        ]
    )
