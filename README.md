# 📱 ExpenseFlow - Android Mobile Expense Tracker (Python)

An Android mobile application for tracking daily expenses built with **Python & Flet (Flutter UI engine)**, featuring **automatic synchronization with Google Sheets** and **automated reporting dashboards** both in Google Sheets and directly inside the mobile application.

---

## ✨ Key Features

### 1. 📲 Mobile Application Features
- **Modern Material Design 3 Mobile Interface**: Dark mode, cards, vibrant category badges, and smooth bottom navigation.
- **Hero Budget & Spend Card**: Real-time spending progress bar against monthly budget, daily average, and highest expense.
- **Quick Actions**: Add expense with 1 tap, quick chips for common amounts (`+₹50`, `+₹100`, `+₹200`, `+₹500`, `+₹1000`).
- **Comprehensive Categories**: Food & Dining, Groceries, Transport & Fuel, Shopping, Utilities & Bills, Entertainment, Health, Education, Travel, Investments, etc.
- **Payment Modes**: UPI (Google Pay / PhonePe / Paytm), Cash, Credit Card, Debit Card, and Net Banking.
- **In-App Visual Reports**:
  - Timeframe selector (Month-by-month, All-time).
  - Multi-color spending proportion bars.
  - Detailed category breakdown with percentages and transaction counts.
  - Payment mode distribution.
- **Transactions History & Search**: Full search by description, filters by category and payment mode, tap-to-edit, and delete.
- **Offline-First & Local Storage**: Powered by SQLite (`expenses.db`), works without internet. Data is queued and automatically synced when online.

---

### 2. 📊 Google Sheets Automated Reports
Whenever you record an expense, the app automatically writes the data to Google Sheets and updates 4 automated sheets:

1. **`Expenses_Log`**:
   - Master ledger recording: `[ID, UUID, Date, Category, Amount, Payment Mode, Description, Month-Year, Synced At]`.
   - Dark indigo header, formatted currency column, frozen header row.
2. **`Monthly_Summary`**:
   - Live KPI cards: Total All-Time Spend, Total Transactions, Average Spend, Current Month Spend.
   - Dynamic `=QUERY()` table summarizing month-by-month expenses and counts.
3. **`Category_Analysis`**:
   - Dynamic `=QUERY()` category report calculating total spending, transaction count, and average per category.
4. **`Payment_Methods`**:
   - Dynamic `=QUERY()` report detailing spending across UPI, Cash, Cards, and Net Banking.

---

## 🛠️ Project Structure

```
Expense App Project/
├── main.py                     # App entry point, mobile router & bottom nav
├── database.py                 # SQLite local database (expenses, settings, offline queue)
├── sheets_service.py           # Google Sheets API (gspread) sync engine & automated reports
├── config.py                   # Category tokens, payment modes, colors, icons, settings
├── setup_google_sheets.py      # Standalone verification CLI tool for Google Sheets
├── requirements.txt            # Python dependencies (flet, gspread, google-auth)
├── android_build_guide.md      # Step-by-step Android build & installation guide
├── credentials_template.json   # Sample template for Google Service Account credentials
├── views/
│   ├── dashboard_view.py       # Home dashboard screen (Hero card, quick actions, recent txns)
│   ├── add_expense_view.py     # Add / Edit expense screen (Amount, category chips, date picker)
│   ├── reports_view.py         # In-App Visual Analytics & reports screen
│   ├── transactions_view.py    # Search, filter, and history screen
│   └── settings_view.py        # Settings, credentials status, budget target, demo data
└── .github/workflows/
    └── build_apk.yml           # GitHub Actions automated cloud APK builder
```

---

## 🚀 Quick Start

### 1. Install Requirements
```bash
pip install -r requirements.txt
```

### 2. Run the App
```bash
python main.py
```
*The app will launch in a simulated mobile device window (412 x 840 px).*

---

## 📱 Running or Building for Android

See [android_build_guide.md](android_build_guide.md) for complete instructions:
1. **Live Test on Phone (No build needed)**: Run `flet run --ip` and open the free **Flet** app on your Android phone.
2. **Build Standalone APK**:
   - Via GitHub Actions: Push code to GitHub and download the compiled APK from the Actions tab.
   - Locally: `flet build apk --project-name "ExpenseFlow" --org "com.expenseflow.app"`

---

## 🔑 Setting up Google Sheets Synchronization

1. Create a Google Cloud project at [console.cloud.google.com](https://console.cloud.google.com/).
2. Enable **Google Sheets API** and **Google Drive API**.
3. Create a **Service Account**, generate a JSON key, rename it to `credentials.json`, and place it in the project root.
4. Run `python setup_google_sheets.py` to test the connection and create your Google Sheets dashboard!
