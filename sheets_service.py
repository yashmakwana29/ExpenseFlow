"""
Google Sheets Integration Service for ExpenseFlow.
Uses gspread to connect with Google Drive & Google Sheets API via a Service Account.
Automatically initializes reporting sheets, automated formulas, and handles batch syncing.
"""
import os
import json
import datetime
from typing import Dict, Any, List, Tuple, Optional
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

class GoogleSheetsManager:
    def __init__(self, credentials_path: Optional[str] = None, sheet_name: Optional[str] = None):
        self.credentials_path = credentials_path or database.get_setting("credentials_path", "credentials.json")
        self.sheet_name = sheet_name or database.get_setting("sheet_name", "ExpenseFlow Tracker & Reports")
        self.client: Optional[gspread.Client] = None
        self.spreadsheet: Optional[gspread.Spreadsheet] = None

    def get_service_account_email(self) -> Optional[str]:
        """Read the client_email from the credentials file without making a network call."""
        if not os.path.exists(self.credentials_path):
            return None
        try:
            with open(self.credentials_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("client_email")
        except Exception:
            return None

    def connect(self) -> Tuple[bool, str]:
        """
        Authenticate with Google Sheets API and open or create the spreadsheet.
        Returns: (success_bool, message_str)
        """
        if not os.path.exists(self.credentials_path):
            return (
                False,
                f"Credentials file '{self.credentials_path}' not found.\n"
                "Please place your Google Cloud Service Account JSON key in the project root."
            )

        try:
            with open(self.credentials_path, "r", encoding="utf-8") as f:
                creds_json = json.load(f)
            
            if "project_id" not in creds_json or "private_key" not in creds_json:
                return False, "Invalid service account file: missing project_id or private_key."
            
            if "example_key" in creds_json.get("private_key", "").lower():
                return False, "Credentials file is still a template! Please download your actual service account key from Google Cloud Console."

            creds = Credentials.from_service_account_file(self.credentials_path, scopes=SCOPES)
            self.client = gspread.authorize(creds)

            # Try to open existing spreadsheet by URL, Key, or Title
            sheet_target = self.sheet_name.strip()
            self.spreadsheet = None

            if sheet_target.startswith("https://") or "docs.google.com/spreadsheets" in sheet_target:
                try:
                    self.spreadsheet = self.client.open_by_url(sheet_target)
                except Exception as ex:
                    return False, f"Could not open sheet by URL. Please check if shared with '{self.get_service_account_email()}': {ex}"
            else:
                try:
                    self.spreadsheet = self.client.open(sheet_target)
                except gspread.exceptions.SpreadsheetNotFound:
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

            # Update saved sheet URL
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
            log_sheet.update(range_name="A1:I1", values=[EXPENSES_HEADERS])
            # Format header row: Dark Slate background (#1E293B), white bold text
            try:
                log_sheet.format("A1:I1", {
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
            ["Average Spend / Txn", "=IFERROR(AVERAGE(Expenses_Log!E2:E), 0)", "This Month Spend", "=IFERROR(SUMIF(Expenses_Log!H2:H, TEXT(TODAY(), \"yyyy-mm\"), Expenses_Log!E2:E), 0)"],
            ["", "", "", ""],
            ["Month (YYYY-MM)", "Total Spent", "Transactions", "Avg Spend / Txn"],
            # Dynamic QUERY formula that aggregates monthly data in real-time
            ["=IFERROR(QUERY(Expenses_Log!A2:I, \"SELECT H, SUM(E), COUNT(E), AVG(E) WHERE H IS NOT NULL GROUP BY H ORDER BY H DESC LABEL H 'Month', SUM(E) 'Total', COUNT(E) 'Count', AVG(E) 'Avg'\", 0), \"No expenses recorded yet\")"]
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
            ["=IFERROR(QUERY(Expenses_Log!A2:I, \"SELECT D, SUM(E), COUNT(E), AVG(E) WHERE D IS NOT NULL GROUP BY D ORDER BY SUM(E) DESC LABEL D 'Category', SUM(E) 'Total Spent', COUNT(E) 'Txn Count', AVG(E) 'Avg'\", 0), \"No data yet\")"]
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
            ["=IFERROR(QUERY(Expenses_Log!A2:I, \"SELECT F, SUM(E), COUNT(E) WHERE F IS NOT NULL GROUP BY F ORDER BY SUM(E) DESC LABEL F 'Payment Mode', SUM(E) 'Total Spent', COUNT(E) 'Count'\", 0), \"No data yet\")"]
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

    def sync_expense(self, expense: Dict[str, Any]) -> Tuple[bool, str]:
        """Sync a single expense to the Google Sheet Expenses_Log."""
        if not self.spreadsheet:
            connected, msg = self.connect()
            if not connected:
                return False, msg

        try:
            log_sheet = self.spreadsheet.worksheet("Expenses_Log")
            
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
                expense.get("created_by", "admin"),
                month_year,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ]

            log_sheet.append_row(row_data, value_input_option="USER_ENTERED")
            database.mark_expenses_as_synced([expense.get("uuid")])
            database.set_setting("last_sync_time", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return True, "Synced successfully to Google Sheets!"

        except Exception as e:
            return False, f"Failed to sync expense: {str(e)}"

    def sync_all_pending(self) -> Tuple[int, str]:
        """
        Pulls all unsynced expenses from SQLite and appends them in a single batch to Google Sheets.
        Returns: (count_synced, status_message)
        """
        pending = database.get_unsynced_expenses()
        if not pending:
            return 0, "All expenses are already up to date with Google Sheets."

        if not self.spreadsheet:
            connected, msg = self.connect()
            if not connected:
                return 0, msg

        try:
            log_sheet = self.spreadsheet.worksheet("Expenses_Log")

            # Check existing UUIDs in Google Sheet to avoid duplicate appending
            try:
                existing_uuids = set(log_sheet.col_values(2)[1:])  # column 2 is UUID
            except Exception:
                existing_uuids = set()

            rows_to_append = []
            uuids_synced = []

            for exp in pending:
                if exp["uuid"] in existing_uuids:
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
                    exp.get("amount", 0.0),
                    exp.get("payment_mode", ""),
                    full_desc,
                    exp.get("created_by", "admin"),
                    month_year,
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ])
                uuids_synced.append(exp["uuid"])

            if rows_to_append:
                log_sheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")

            # Mark all synced in DB
            database.mark_expenses_as_synced(uuids_synced)
            database.set_setting("last_sync_time", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            return len(uuids_synced), f"Successfully synced {len(uuids_synced)} expense(s) to Google Sheets!"

        except Exception as e:
            return 0, f"Sync error: {str(e)}"

    def sync_all_db_records(self) -> Tuple[int, int, str]:
        """
        Comprehensive sync: reads ALL records in the database (MySQL) and verifies
        that each one is present in Google Sheets Expenses_Log.
        If any record in the DB is missing from Google Sheets, it is immediately appended.
        Ensures 100% data consistency so all DB data can be seen in Google Sheets!
        Returns: (newly_synced_count, total_db_count, status_message)
        """
        all_expenses = database.get_expenses(limit=None)
        if not all_expenses:
            return 0, 0, "No expenses found in database to synchronize."

        if not self.spreadsheet:
            connected, msg = self.connect()
            if not connected:
                return 0, len(all_expenses), msg

        try:
            log_sheet = self.spreadsheet.worksheet("Expenses_Log")

            # Check existing UUIDs in Google Sheet
            try:
                existing_uuids = set(log_sheet.col_values(2)[1:])  # column 2 is UUID
            except Exception:
                existing_uuids = set()

            rows_to_append = []
            uuids_synced = []

            for exp in all_expenses:
                if exp["uuid"] in existing_uuids:
                    # Already in Google Sheet; ensure marked as synced in DB
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
                    exp.get("created_by", "admin"),
                    month_year,
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ])
                uuids_synced.append(exp["uuid"])

            if rows_to_append:
                log_sheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")

            if uuids_synced:
                database.mark_expenses_as_synced(uuids_synced)

            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            database.set_setting("last_sync_time", now_str)

            total_db = len(all_expenses)
            new_count = len(rows_to_append)
            if new_count > 0:
                return new_count, total_db, f"Synced {new_count} new DB expense(s) to Google Sheets! (Total in DB: {total_db})"
            return 0, total_db, f"Google Sheets is fully up-to-date with DB! All {total_db} expenses verified."

        except Exception as e:
            return 0, len(all_expenses), f"Sync error: {str(e)}"


    def test_connection(self) -> Dict[str, Any]:
        """Detailed connection test returning diagnostic info."""
        email = self.get_service_account_email()
        if not email:
            return {
                "success": False,
                "email": None,
                "message": "credentials.json file not found. Please place your service account credentials file in the project folder.",
                "url": None
            }

        connected, msg = self.connect()
        return {
            "success": connected,
            "email": email,
            "message": msg,
            "url": self.spreadsheet.url if self.spreadsheet else database.get_setting("sheet_url", "")
        }
