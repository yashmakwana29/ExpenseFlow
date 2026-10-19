"""
Google Sheets Integration Service for ExpenseFlow.
Uses gspread to connect with Google Drive & Google Sheets API via a Service Account.
Automatically initializes reporting sheets, automated formulas, and handles batch syncing.
"""
import os
import json
import datetime
from typing import Dict, Any, List, Tuple, Optional
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

import uuid
import gspread
from google.oauth2.service_account import Credentials
import database

# Google API Scopes required for Drive & Sheets
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

EXPENSES_HEADERS = [
    "ID", "UUID", "Date", "Category", "Amount", "Payment Mode", "Description / Notes", "User", "Month-Year", "Synced At"
]

def clean_sheet_amount(val: Any) -> float:
    """Safely extracts a float amount from Google Sheet cell string/number."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    for ch in ["₹", "$", "€", "£", "Rs.", "Rs", "rs", ","]:
        s = s.replace(ch, "")
    s = s.strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0

def normalize_sheet_date(date_str: str) -> str:
    """Normalizes any human date representation (DD/MM/YYYY, etc.) to ISO YYYY-MM-DD."""
    s = (date_str or "").strip()
    if not s:
        return datetime.date.today().strftime("%Y-%m-%d")
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    if len(s) >= 10 and s[:4].isdigit():
        return s[:10]
    return datetime.date.today().strftime("%Y-%m-%d")

class GoogleSheetsManager:
    def __init__(self, credentials_path: Optional[str] = None, sheet_name: Optional[str] = None):
        self.credentials_path = credentials_path or database.get_setting("credentials_path", "credentials.json")
        self.sheet_name = sheet_name or database.get_setting("sheet_name", "ExpenseFlow Tracker & Reports")
        self.client: Optional[gspread.Client] = None
        self.spreadsheet: Optional[gspread.Spreadsheet] = None

    def _get_credentials_data(self) -> Optional[Dict[str, Any]]:
        """Resolves Service Account credentials either from local file or embedded app config."""
        # Check local file first if present
        if self.credentials_path and os.path.exists(self.credentials_path):
            try:
                with open(self.credentials_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("project_id") and data.get("private_key") and "example_key" not in data.get("private_key", "").lower():
                        return data
            except Exception:
                pass

        # Fall back to embedded credentials in config.py (ideal for packaged Android APKs)
        try:
            from config import GOOGLE_SERVICE_ACCOUNT_INFO
            if GOOGLE_SERVICE_ACCOUNT_INFO and GOOGLE_SERVICE_ACCOUNT_INFO.get("private_key"):
                return GOOGLE_SERVICE_ACCOUNT_INFO
        except Exception:
            pass
        return None

    def get_service_account_email(self) -> Optional[str]:
        """Read the client_email from the resolved credentials without making a network call."""
        data = self._get_credentials_data()
        return data.get("client_email") if data else None

    def connect(self) -> Tuple[bool, str]:
        """
        Authenticate with Google Sheets API and open or create the spreadsheet.
        Returns: (success_bool, message_str)
        """
        creds_json = self._get_credentials_data()
        if not creds_json:
            return (
                False,
                "Google Cloud Service Account credentials not found.\n"
                "Please configure credentials in config.py or place credentials.json in the project root."
            )

        try:
            creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
            self.client = gspread.authorize(creds)

            # Try to open existing spreadsheet by URL first, then title
            from config import DEFAULT_SETTINGS
            default_url = DEFAULT_SETTINGS.get("sheet_url", "").strip()
            sheet_target = database.get_setting("sheet_url", "").strip() or default_url or self.sheet_name.strip()
            self.spreadsheet = None

            if sheet_target.startswith("https://") or "docs.google.com/spreadsheets" in sheet_target:
                try:
                    self.spreadsheet = self.client.open_by_url(sheet_target)
                except Exception as ex:
                    ex_str = str(ex).lower()
                    if ("404" in ex_str or "not found" in ex_str) and default_url and sheet_target != default_url:
                        try:
                            self.spreadsheet = self.client.open_by_url(default_url)
                        except Exception:
                            pass
                    if not self.spreadsheet:
                        if "404" in ex_str or "not found" in ex_str:
                            return False, (
                                "The previously linked Google Sheet was deleted or cannot be found (404).\n"
                                "To link your new clean sheet:\n"
                                "1. Create a sheet at https://sheets.new\n"
                                f"2. Share with: {self.get_service_account_email()} (as Editor)\n"
                                "3. Paste the new URL into Settings ➔ Google Spreadsheet URL."
                            )
                        return False, f"Could not open sheet by URL. Please check if shared with '{self.get_service_account_email()}': {ex}"
            else:
                try:
                    self.spreadsheet = self.client.open(sheet_target)
                except gspread.exceptions.SpreadsheetNotFound:
                    # Check default URL fallback
                    if default_url:
                        try:
                            self.spreadsheet = self.client.open_by_url(default_url)
                        except Exception:
                            pass

                    if not self.spreadsheet:
                        # Try creating new one
                        try:
                            self.spreadsheet = self.client.create(sheet_target)
                        except Exception as ex:
                            if "quota has been exceeded" in str(ex).lower():
                                return (
                                    False,
                                    "Google Service Accounts do not have personal Google Drive storage.\n"
                                    "To fix this:\n"
                                    "1. Open Google Sheets (https://sheets.new) and create a new sheet.\n"
                                    f"2. Click 'Share' and add this email as 'Editor':\n   {self.get_service_account_email()}\n"
                                    f"3. Name the sheet '{sheet_target}' (or paste its full URL into settings)."
                                )
                            raise ex

            # Update saved sheet URL and title
            if self.spreadsheet:
                database.set_setting("sheet_url", self.spreadsheet.url)
                database.set_setting("sheet_name", self.spreadsheet.title)

            # Ensure all tabs and report structures exist
            self._setup_sheets_structure()

            return True, f"Successfully connected to '{self.spreadsheet.title}'"

        except Exception as e:
            error_msg = str(e)
            if "invalid_grant" in error_msg.lower():
                return False, "Authentication failed: Invalid credentials or expired token."
            return False, f"Connection error: {error_msg}"

    def _setup_sheets_structure(self):
        """Initializes Expenses_Log and automated report sheets with formulas and styling."""
        if not self.spreadsheet:
            return

        # 1. Main Expenses Log Worksheet
        try:
            log_sheet = self.spreadsheet.worksheet("Expenses_Log")
        except gspread.exceptions.WorksheetNotFound:
            # If default "Sheet1" exists, rename it
            try:
                sheet1 = self.spreadsheet.worksheet("Sheet1")
                sheet1.update_title("Expenses_Log")
                log_sheet = sheet1
            except Exception:
                log_sheet = self.spreadsheet.add_worksheet(title="Expenses_Log", rows=1000, cols=12)

        # Ensure headers in Expenses_Log
        existing_headers = log_sheet.row_values(1)
        if not existing_headers:
            log_sheet.update(range_name="A1:J1", values=[EXPENSES_HEADERS])
            # Format header row: Dark Slate background (#1E293B), white bold text
            try:
                log_sheet.format("A1:J1", {
                    "backgroundColor": {"red": 0.12, "green": 0.16, "blue": 0.23},
                    "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True},
                    "horizontalAlignment": "CENTER"
                })
            except Exception:
                pass

        # 2. Monthly Summary Worksheet (with automated QUERY / SUMIF formulas)
        try:
            monthly_sheet = self.spreadsheet.worksheet("Monthly_Summary")
        except gspread.exceptions.WorksheetNotFound:
            monthly_sheet = self.spreadsheet.add_worksheet(title="Monthly_Summary", rows=200, cols=10)
            self._init_monthly_summary_sheet(monthly_sheet)

        # 3. Category Analysis Worksheet
        try:
            cat_sheet = self.spreadsheet.worksheet("Category_Analysis")
        except gspread.exceptions.WorksheetNotFound:
            cat_sheet = self.spreadsheet.add_worksheet(title="Category_Analysis", rows=100, cols=10)
            self._init_category_sheet(cat_sheet)

        # 4. Payment Method Analysis Worksheet
        try:
            pay_sheet = self.spreadsheet.worksheet("Payment_Methods")
        except gspread.exceptions.WorksheetNotFound:
            pay_sheet = self.spreadsheet.add_worksheet(title="Payment_Methods", rows=50, cols=8)
            self._init_payment_sheet(pay_sheet)

    def _init_monthly_summary_sheet(self, ws: gspread.Worksheet):
        """Set up automated Monthly Summary report."""
        content = [
            ["📊 MONTHLY EXPENSE SUMMARY REPORT", "", "", ""],
            ["Generated automatically by ExpenseFlow Mobile App", "", "", ""],
            ["Total All-Time Spend", "=IFERROR(SUM(Expenses_Log!E2:E), 0)", "Total Transactions", "=IFERROR(COUNT(Expenses_Log!E2:E), 0)"],
            ["Average Spend / Txn", "=IFERROR(AVERAGE(Expenses_Log!E2:E), 0)", "This Month Spend", "=IFERROR(SUMIF(Expenses_Log!I2:I, TEXT(TODAY(), \"yyyy-mm\"), Expenses_Log!E2:E), 0)"],
            ["", "", "", ""],
            ["Month (YYYY-MM)", "Total Spent", "Transactions", "Avg Spend / Txn"],
            # Dynamic QUERY formula that aggregates monthly data in real-time
            ["=IFERROR(QUERY(Expenses_Log!A2:J, \"SELECT I, SUM(E), COUNT(E), AVG(E) WHERE I IS NOT NULL GROUP BY I ORDER BY I DESC LABEL I 'Month', SUM(E) 'Total', COUNT(E) 'Count', AVG(E) 'Avg'\", 0), \"No expenses recorded yet\")"]
        ]
        ws.update(range_name="A1:D7", values=content, value_input_option="USER_ENTERED")
        try:
            ws.format("A1:D1", {
                "backgroundColor": {"red": 0.23, "green": 0.28, "blue": 0.65},
                "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 12}
            })
            ws.format("A6:D6", {
                "backgroundColor": {"red": 0.12, "green": 0.16, "blue": 0.23},
                "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True}
            })
        except Exception:
            pass

    def _init_category_sheet(self, ws: gspread.Worksheet):
        """Set up automated Category Breakdown report."""
        content = [
            ["🏷️ CATEGORY-WISE EXPENSE ANALYSIS", "", "", ""],
            ["Live automated breakdown from Expenses_Log", "", "", ""],
            ["", "", "", ""],
            ["Category", "Total Spent", "Transactions", "Avg Spend / Txn"],
            ["=IFERROR(QUERY(Expenses_Log!A2:J, \"SELECT D, SUM(E), COUNT(E), AVG(E) WHERE D IS NOT NULL GROUP BY D ORDER BY SUM(E) DESC LABEL D 'Category', SUM(E) 'Total Spent', COUNT(E) 'Txn Count', AVG(E) 'Avg'\", 0), \"No data yet\")"]
        ]
        ws.update(range_name="A1:D5", values=content, value_input_option="USER_ENTERED")
        try:
            ws.format("A1:D1", {
                "backgroundColor": {"red": 0.08, "green": 0.45, "blue": 0.42},
                "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 12}
            })
            ws.format("A4:D4", {
                "backgroundColor": {"red": 0.12, "green": 0.16, "blue": 0.23},
                "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True}
            })
        except Exception:
            pass

    def _init_payment_sheet(self, ws: gspread.Worksheet):
        """Set up automated Payment Method Breakdown report."""
        content = [
            ["💳 PAYMENT METHOD DISTRIBUTION REPORT", "", ""],
            ["Live payment analysis across UPI, Cards, and Cash", "", ""],
            ["", "", ""],
            ["Payment Mode", "Total Spent", "Transactions"],
            ["=IFERROR(QUERY(Expenses_Log!A2:J, \"SELECT F, SUM(E), COUNT(E) WHERE F IS NOT NULL GROUP BY F ORDER BY SUM(E) DESC LABEL F 'Payment Mode', SUM(E) 'Total Spent', COUNT(E) 'Count'\", 0), \"No data yet\")"]
        ]
        ws.update(range_name="A1:C5", values=content, value_input_option="USER_ENTERED")
        try:
            ws.format("A1:C1", {
                "backgroundColor": {"red": 0.55, "green": 0.25, "blue": 0.65},
                "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 12}
            })
            ws.format("A4:C4", {
                "backgroundColor": {"red": 0.12, "green": 0.16, "blue": 0.23},
                "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True}
            })
        except Exception:
            pass

    def get_user_sheet_title(self, username: Optional[str] = None) -> str:
        """Determines the dedicated worksheet title for a specific user (Expenses_<username>)."""
        if not username:
            curr_user = database.get_current_session_user()
            clean_name = curr_user["username"].strip() if curr_user else "admin"
        else:
            clean_name = username.strip()
        # Clean invalid characters not permitted in Google Sheets tab titles
        for ch in [":", "\\", "/", "?", "*", "[", "]"]:
            clean_name = clean_name.replace(ch, "_")
        return f"Expenses_{clean_name}"

    def get_or_create_user_worksheet(self, username: Optional[str] = None) -> gspread.Worksheet:
        """
        Retrieves or creates an isolated, dedicated worksheet for the specified user.
        Format: 'Expenses_<username>' (e.g. Expenses_yashm, Expenses_admin).
        """
        if not self.spreadsheet:
            connected, msg = self.connect()
            if not connected:
                raise RuntimeError(msg)

        title = self.get_user_sheet_title(username)
        try:
            ws = self.spreadsheet.worksheet(title)
        except gspread.exceptions.WorksheetNotFound:
            try:
                sheet1 = self.spreadsheet.worksheet("Sheet1")
                if len(sheet1.row_values(1)) == 0:
                    sheet1.update_title(title)
                    ws = sheet1
                else:
                    ws = self.spreadsheet.add_worksheet(title=title, rows=1000, cols=12)
            except Exception:
                ws = self.spreadsheet.add_worksheet(title=title, rows=1000, cols=12)

        # Check and ensure standard headers
        existing_headers = ws.row_values(1)
        if not existing_headers:
            ws.update(range_name="A1:J1", values=[EXPENSES_HEADERS])
            try:
                ws.format("A1:J1", {
                    "backgroundColor": {"red": 0.12, "green": 0.16, "blue": 0.23},
                    "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True},
                    "horizontalAlignment": "CENTER"
                })
            except Exception:
                pass
        return ws

    def sync_expense(self, expense: Dict[str, Any]) -> Tuple[bool, str]:
        """Sync a single expense to both the creator's dedicated tab and main Expenses_Log."""
        if not self.spreadsheet:
            connected, msg = self.connect()
            if not connected:
                return False, msg

        try:
            creator = (expense.get("created_by") or "admin").strip()
            user_sheet = self.get_or_create_user_worksheet(creator)

            # Format month-year
            date_val = expense.get("date", "")
            month_year = date_val[:7] if len(date_val) >= 7 else ""
            notes_str = expense.get("notes", "")
            title_str = expense.get("title", "")
            full_desc = f"{title_str} - {notes_str}" if notes_str else title_str

            row_data = [
                expense.get("id", ""),
                expense.get("uuid", ""),
                date_val,
                expense.get("category", ""),
                expense.get("amount", 0.0),
                expense.get("payment_mode", ""),
                full_desc,
                creator,
                month_year,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ]

            # 1. Sync to user-specific sheet tab
            try:
                u_uuids = set(user_sheet.col_values(2)[1:])
                if expense.get("uuid") not in u_uuids:
                    user_sheet.append_row(row_data, value_input_option="USER_ENTERED")
            except Exception:
                user_sheet.append_row(row_data, value_input_option="USER_ENTERED")

            # 2. Sync to main Expenses_Log so reports and formulas update in real-time
            try:
                log_sheet = self.spreadsheet.worksheet("Expenses_Log")
                log_uuids = set(log_sheet.col_values(2)[1:])
                if expense.get("uuid") not in log_uuids:
                    log_sheet.append_row(row_data, value_input_option="USER_ENTERED")
            except Exception:
                pass

            database.mark_expenses_as_synced([expense.get("uuid")])
            database.set_setting("last_sync_time", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return True, f"Synced successfully to Google Sheets ({user_sheet.title} & Expenses_Log)!"

        except Exception as e:
            return False, f"Failed to sync expense: {str(e)}"

    def sync_all_pending(self, username: Optional[str] = None) -> Tuple[int, str]:
        """
        Pushes unsynced expenses to each user's specific worksheet tab (Expenses_<username>)
        and synchronizes with Expenses_Log to keep all live reports up to date.
        """
        if not username:
            curr_user = database.get_current_session_user()
            if curr_user and curr_user.get("role") != "admin":
                username = curr_user["username"]

        pending = database.get_unsynced_expenses(username=username)
        if not pending:
            return 0, "All your expenses are already up to date with Google Sheets."

        if not self.spreadsheet:
            connected, msg = self.connect()
            if not connected:
                return 0, msg

        try:
            # Group pending items by user
            user_groups: Dict[str, List[Dict[str, Any]]] = {}
            for exp in pending:
                u = (exp.get("created_by") or "admin").strip()
                user_groups.setdefault(u, []).append(exp)

            total_synced = 0
            all_synced_uuids = []
            log_sheet = None
            try:
                log_sheet = self.spreadsheet.worksheet("Expenses_Log")
            except Exception:
                pass

            for u_name, exp_list in user_groups.items():
                user_sheet = self.get_or_create_user_worksheet(u_name)
                try:
                    existing_uuids = set(user_sheet.col_values(2)[1:])  # col 2 is UUID
                except Exception:
                    existing_uuids = set()

                rows_to_append = []
                for exp in exp_list:
                    if exp["uuid"] in existing_uuids:
                        all_synced_uuids.append(exp["uuid"])
                        continue

                    date_val = exp.get("date", "")
                    month_year = date_val[:7] if len(date_val) >= 7 else ""
                    notes_str = exp.get("notes", "")
                    title_str = exp.get("title", "")
                    full_desc = f"{title_str} - {notes_str}" if notes_str else title_str

                    rows_to_append.append([
                        exp.get("id", ""),
                        exp.get("uuid", ""),
                        date_val,
                        exp.get("category", ""),
                        float(exp.get("amount", 0.0)),
                        exp.get("payment_mode", ""),
                        full_desc,
                        u_name,
                        month_year,
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ])
                    all_synced_uuids.append(exp["uuid"])

                if rows_to_append:
                    user_sheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")
                    total_synced += len(rows_to_append)

                    # Also append to Expenses_Log for live reporting
                    if log_sheet:
                        try:
                            log_uuids = set(log_sheet.col_values(2)[1:])
                            log_missing = [r for r in rows_to_append if r[1] not in log_uuids]
                            if log_missing:
                                log_sheet.append_rows(log_missing, value_input_option="USER_ENTERED")
                        except Exception:
                            pass

            if all_synced_uuids:
                database.mark_expenses_as_synced(all_synced_uuids)

            database.set_setting("last_sync_time", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            target_label = self.get_user_sheet_title(username) if username else "user-specific sheet tabs"
            return len(all_synced_uuids), f"Successfully synced {len(all_synced_uuids)} expense(s) to Google Sheets ({target_label})!"

        except Exception as e:
            return 0, f"Sync error: {str(e)}"

    def sync_all_db_records(self, username: Optional[str] = None) -> Tuple[int, int, str]:
        """
        Comprehensive sync: reads records from the DB and ensures each is present
        in its dedicated user worksheet (Expenses_<username>).
        """
        if not username:
            curr_user = database.get_current_session_user()
            if curr_user and curr_user.get("role") != "admin":
                username = curr_user["username"]

        all_expenses = database.get_expenses(limit=None, username=username)
        if not all_expenses:
            return 0, 0, "No expenses found in database to synchronize."

        if not self.spreadsheet:
            connected, msg = self.connect()
            if not connected:
                return 0, len(all_expenses), msg

        try:
            user_groups: Dict[str, List[Dict[str, Any]]] = {}
            for exp in all_expenses:
                u = (exp.get("created_by") or "admin").strip()
                user_groups.setdefault(u, []).append(exp)

            new_count_total = 0
            for u_name, exps in user_groups.items():
                user_sheet = self.get_or_create_user_worksheet(u_name)
                try:
                    existing_uuids = set(user_sheet.col_values(2)[1:])
                except Exception:
                    existing_uuids = set()

                rows_to_append = []
                uuids_synced = []

                for exp in exps:
                    if exp["uuid"] in existing_uuids:
                        if not exp.get("synced"):
                            uuids_synced.append(exp["uuid"])
                        continue

                    date_val = exp.get("date", "")
                    month_year = date_val[:7] if len(date_val) >= 7 else ""
                    notes_str = exp.get("notes", "")
                    title_str = exp.get("title", "")
                    full_desc = f"{title_str} - {notes_str}" if notes_str else title_str

                    rows_to_append.append([
                        exp.get("id", ""),
                        exp.get("uuid", ""),
                        date_val,
                        exp.get("category", ""),
                        float(exp.get("amount", 0.0)),
                        exp.get("payment_mode", ""),
                        full_desc,
                        u_name,
                        month_year,
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ])
                    uuids_synced.append(exp["uuid"])

                if rows_to_append:
                    user_sheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")
                    new_count_total += len(rows_to_append)

                if uuids_synced:
                    database.mark_expenses_as_synced(uuids_synced)

            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            database.set_setting("last_sync_time", now_str)

            total_db = len(all_expenses)
            if new_count_total > 0:
                return new_count_total, total_db, f"Synced {new_count_total} new DB expense(s) to user-specific Google Sheets!"
            return 0, total_db, f"Google Sheets is fully up-to-date! All {total_db} user expenses verified."

        except Exception as e:
            return 0, len(all_expenses), f"Sync error: {str(e)}"

    def _pull_worksheet_rows(self, ws: gspread.Worksheet, default_user: str) -> int:
        """
        Extracts expense records from a worksheet, auto-assigns UUIDs to human-entered rows,
        updates the sheet with the assigned UUIDs, and inserts them into the local database.
        Returns the number of newly inserted records.
        """
        try:
            rows = ws.get_all_values()
            if not rows or len(rows) <= 1:
                return 0

            headers = [str(h).strip().lower() for h in rows[0]]
            uuid_idx = -1
            date_idx = -1
            cat_idx = -1
            amt_idx = -1
            pay_idx = -1
            desc_idx = -1
            user_idx = -1

            for idx, h in enumerate(headers):
                if "uuid" in h: uuid_idx = idx
                elif "date" in h: date_idx = idx
                elif "category" in h: cat_idx = idx
                elif "amount" in h: amt_idx = idx
                elif "payment" in h: pay_idx = idx
                elif "desc" in h or "notes" in h: desc_idx = idx
                elif "user" in h: user_idx = idx

            if uuid_idx == -1: uuid_idx = 1
            if date_idx == -1: date_idx = 2
            if cat_idx == -1: cat_idx = 3
            if amt_idx == -1: amt_idx = 4
            if pay_idx == -1: pay_idx = 5
            if desc_idx == -1: desc_idx = 6

            new_count = 0
            for idx, row in enumerate(rows[1:]):
                row_num = idx + 2  # 1-indexed for gspread
                if not row or not any(str(cell).strip() for cell in row):
                    continue

                raw_amt = row[amt_idx] if len(row) > amt_idx else ""
                amount_val = clean_sheet_amount(raw_amt)
                raw_desc = row[desc_idx].strip() if len(row) > desc_idx else ""
                category_val = row[cat_idx].strip() if len(row) > cat_idx else "Other"

                # If no amount and no title/desc/category, ignore empty row
                if amount_val == 0.0 and not raw_desc and not category_val:
                    continue

                item_uuid = row[uuid_idx].strip() if len(row) > uuid_idx else ""
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # If row was entered manually by a human in Google Sheets without a UUID
                if not item_uuid or item_uuid.lower() == "uuid" or len(item_uuid) < 8:
                    item_uuid = str(uuid.uuid4())
                    raw_date = row[date_idx].strip() if len(row) > date_idx else ""
                    norm_date = normalize_sheet_date(raw_date)
                    month_yr = norm_date[:7]
                    try:
                        # Write generated UUID and metadata back into Google Sheet
                        ws.update_cell(row_num, uuid_idx + 1, item_uuid)
                        if len(row) <= 8 or not row[8].strip():
                            ws.update_cell(row_num, 9, month_yr)
                        if len(row) <= 9 or not row[9].strip():
                            ws.update_cell(row_num, 10, now_str)
                    except Exception:
                        pass
                else:
                    raw_date = row[date_idx].strip() if len(row) > date_idx else ""
                    norm_date = normalize_sheet_date(raw_date)

                payment_val = row[pay_idx].strip() if len(row) > pay_idx and row[pay_idx].strip() else "Cash"

                if " - " in raw_desc:
                    parts = raw_desc.split(" - ", 1)
                    title_val = parts[0].strip()
                    notes_val = parts[1].strip()
                else:
                    title_val = raw_desc if raw_desc else category_val
                    notes_val = ""

                created_by_val = default_user
                if user_idx != -1 and len(row) > user_idx and row[user_idx].strip():
                    created_by_val = row[user_idx].strip()

                inserted = database.upsert_expense_from_sync(
                    uuid_str=item_uuid,
                    title=title_val,
                    amount=amount_val,
                    category=category_val,
                    payment_mode=payment_val,
                    date=norm_date,
                    notes=notes_val,
                    created_by=created_by_val,
                    synced_at=now_str
                )
                if inserted:
                    new_count += 1

            return new_count
        except Exception:
            return 0

    def pull_from_sheets_to_db(self, username: Optional[str] = None) -> Tuple[int, str]:
        """
        Pulls expense records from Google Sheets into the local database.
        Scans both the user's personal tab (Expenses_<username>) and the main Expenses_Log.
        Auto-assigns UUIDs to any human-entered rows so they are imported seamlessly into the app.
        """
        if not self.spreadsheet:
            connected, msg = self.connect()
            if not connected:
                return 0, msg

        if not username:
            curr_user = database.get_current_session_user()
            username = curr_user["username"].strip() if curr_user else "admin"

        target_title = self.get_user_sheet_title(username)
        try:
            user_sheet = self.spreadsheet.worksheet(target_title)
        except gspread.exceptions.WorksheetNotFound:
            user_sheet = self.get_or_create_user_worksheet(username)

        new_count = 0
        # 1. Pull from user's dedicated tab (Expenses_<username>)
        new_count += self._pull_worksheet_rows(user_sheet, default_user=username)

        # 2. Also pull from main Expenses_Log (if user typed in the main sheet tab)
        try:
            log_sheet = self.spreadsheet.worksheet("Expenses_Log")
            new_count += self._pull_worksheet_rows(log_sheet, default_user=username)
        except Exception:
            pass

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        database.set_setting("last_sync_time", now_str)

        if new_count > 0:
            return new_count, f"Downloaded {new_count} new expense(s) from Google Sheets!"
        return 0, f"All data is already 100% up to date with Google Sheets!"

    def sync_bidirectional(self, username: Optional[str] = None) -> Tuple[int, int, str]:
        """
        Complete 2-way data sync strictly isolated to the user's specific Google Sheet tab:
        1. Resolves active user so only that user's records are pushed/pulled.
        2. Pushes pending local expenses for that user to Expenses_<username>.
        3. Pulls cloud expenses from Expenses_<username> into the local database.
        Returns: (pushed_count, pulled_count, status_message)
        """
        if not self.spreadsheet:
            connected, msg = self.connect()
            if not connected:
                return 0, 0, msg

        if not username:
            curr_user = database.get_current_session_user()
            if curr_user:
                username = curr_user["username"]

        # Step 1: Push user's unsynced expenses to their dedicated sheet
        pushed_count, push_msg = self.sync_all_pending(username=username)

        # Step 2: Pull cloud expenses from user's dedicated sheet
        pulled_count, pull_msg = self.pull_from_sheets_to_db(username=username)

        total = pushed_count + pulled_count
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        database.set_setting("last_sync_time", now_str)

        target_title = self.get_user_sheet_title(username)
        if total == 0:
            return 0, 0, f"All data is already 100% up to date with '{target_title}'!"

        actions = []
        if pushed_count > 0:
            actions.append(f"Uploaded {pushed_count} to {target_title}")
        if pulled_count > 0:
            actions.append(f"Downloaded {pulled_count} from {target_title}")

        return pushed_count, pulled_count, f"Sync successful: {', '.join(actions)}!"

    def test_connection(self) -> Dict[str, Any]:
        """Detailed connection test returning diagnostic info."""
        email = self.get_service_account_email()
        if not email:
            return {
                "success": False,
                "email": None,
                "message": "Google Cloud Service Account credentials not found in file or app config.",
                "url": None
            }

        connected, msg = self.connect()
        return {
            "success": connected,
            "email": email,
            "message": msg,
            "url": self.spreadsheet.url if self.spreadsheet else database.get_setting("sheet_url", "")
        }
