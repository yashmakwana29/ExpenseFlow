"""
Standalone CLI setup and verification tool for Google Sheets.
Run this script to test your credentials.json and initialize the Google Sheets dashboard.
Usage: python setup_google_sheets.py
"""
import sys
import os
import json
import sheets_service
import database

def main():
    print("=" * 60)
    print("ExpenseFlow - Google Sheets Connection & Report Setup")
    print("=" * 60)

    database.init_db()
    mgr = sheets_service.GoogleSheetsManager()
    
    email = mgr.get_service_account_email()
    if not email:
        print("\n[!] 'credentials.json' was NOT found in the current directory.")
        print("\nSteps to fix:")
        print("1. Go to Google Cloud Console (https://console.cloud.google.com/)")
        print("2. Create a project and enable 'Google Sheets API' & 'Google Drive API'")
        print("3. Create a Service Account and download the JSON key as 'credentials.json'")
        print("4. Place 'credentials.json' in this folder: " + os.path.abspath("."))
        print("\nSee 'android_build_guide.md' for full step-by-step instructions with screenshots.")
        return

    print(f"\n[+] Found credentials for Service Account:")
    print(f"    Email: {email}")
    print("\n[*] IMPORTANT: If you already have a Google Sheet created, share it with the email above with 'Editor' permissions.")
    print("    Otherwise, this script will automatically create a new sheet for you.")

    # Check if a custom sheet name or URL was passed as argument
    if len(sys.argv) > 1 and sys.argv[1].strip():
        custom_target = sys.argv[1].strip()
        database.set_setting("sheet_name", custom_target)
        mgr = sheets_service.GoogleSheetsManager(sheet_name=custom_target)

    sheet_name = database.get_setting("sheet_name", "ExpenseFlow Tracker & Reports")
    print(f"\n[*] Connecting to Google Sheets with spreadsheet: '{sheet_name}'...")
    
    success, msg = mgr.connect()
    if success:
        print(f"\n[SUCCESS] {msg}")
        if mgr.spreadsheet:
            print(f"\nSpreadsheet URL: {mgr.spreadsheet.url}")
            print("\nSheets & Automated Reports configured:")
            print("  1. 'Expenses_Log'       -> Live transaction register")
            print("  2. 'Monthly_Summary'    -> Automated monthly spend KPI cards & summary table")
            print("  3. 'Category_Analysis'  -> Live QUERY-powered category totals & count")
            print("  4. 'Payment_Methods'    -> Live payment mode distribution")
    else:
        print(f"\n[ERROR] Connection failed: {msg}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
