# Android Mobile App Build & Google Sheets Integration Guide

This guide explains how to run, test, and build the **ExpenseFlow** Android Mobile Application written in Python using **Flet**, and how to link it with your Google Sheets account for automated syncing and live reports.

---

## 🚀 Part 1: How to Test the App Locally on Windows

You can run the app immediately on your computer. It simulates a mobile smartphone viewport (412 x 840 px) with dark theme and bottom navigation:

```bash
# In the project directory:
python main.py
```
or with Flet CLI (for hot reload while editing code):
```bash
flet run
```

---

## 📱 Part 2: Instant Testing on Your Real Android Phone (Zero Compilation Required!)

If you want to use the application on your physical Android phone right now without having to install Android SDK or compile an APK:

1. **Install the Flet App on Android**:
   - Open **Google Play Store** on your Android phone.
   - Search for **"Flet"** and install it (free official Flutter runner by Flet.dev).

2. **Run the app on your computer exposing the local network**:
   ```bash
   flet run --ip
   ```

3. **Open on your phone**:
   - Ensure your phone and PC are connected to the same Wi-Fi.
   - Open the Flet app on your phone, scan the QR code printed in your computer's terminal, or type the URL (e.g. `http://192.168.1.5:8550`).
   - The entire app runs natively on your Android device!

---

## 📦 Part 3: Building a Standalone Android APK File

### Method A: Automated Cloud Build using GitHub Actions (Recommended!)
No need to install 15 GB of Android Studio and Android NDK on your PC! We have pre-configured a GitHub Actions workflow in `.github/workflows/build_apk.yml`.

1. Create a GitHub repository and push your project code:
   ```bash
   git init
   git add .
   git commit -m "ExpenseFlow Android App"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/ExpenseFlow.git
   git push -u origin main
   ```
2. In your GitHub repository, click the **"Actions"** tab.
3. The **"Build Android APK"** workflow runs automatically on Ubuntu with Flutter and Android SDK pre-installed.
4. When finished (usually ~4-6 minutes), click on the build run and download **`ExpenseFlow-Android-APK.zip`**.
5. Transfer the `.apk` file to your Android phone and tap **Install**!

---

### Method B: Build APK Locally on Windows using Flet CLI
If you have Android Studio & Java JDK 17 installed locally:

```bash
flet build apk --project expenseflow --product "ExpenseFlow" --org "com.expenseflow.app"
```

The compiled release `.apk` file will be generated in `build/apk/`.

---

## 📊 Part 4: Setting Up Google Sheets Automatic Sync & Reports

Whenever you record an expense in the app, it automatically writes the record to Google Sheets and updates 4 live report worksheets.

### Step 1: Create a Google Cloud Service Account
1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Click **Create Project** (e.g. name it `ExpenseFlow-Tracker`).
3. In the search bar at the top, search for and enable these two APIs:
   - **Google Sheets API** (click *Enable*)
   - **Google Drive API** (click *Enable*)
4. Navigate to **IAM & Admin** ➔ **Service Accounts**.
5. Click **Create Service Account**:
   - Service account name: `expense-tracker-bot`
   - Role: `Editor`
   - Click *Done*.
6. Click on the newly created service account ➔ open the **Keys** tab.
7. Click **Add Key** ➔ **Create new key** ➔ select **JSON** ➔ click **Create**.
8. A JSON file will download to your computer.

### Step 2: Add `credentials.json` to the App
1. Rename the downloaded JSON file to `credentials.json`.
2. Move `credentials.json` into the root directory of this project:
   `e:\Expense App Project\credentials.json`

### Step 3: Run the Setup Verification Script
Open your terminal and run:
```bash
python setup_google_sheets.py
```
This script will:
- Read your service account email (e.g. `expense-tracker-bot@project.iam.gserviceaccount.com`).
- Automatically create a new Google Spreadsheet titled **"ExpenseFlow Tracker & Reports"**.
- Automatically initialize the 4 structured sheets and dynamic reports:
  1. `Expenses_Log`: Full transaction ledger with date, category, amount, payment mode, notes, and sync timestamps.
  2. `Monthly_Summary`: Dynamic KPI cards (Total Spend, Avg Spend, Txn Count) and monthly summary table.
  3. `Category_Analysis`: Dynamic `=QUERY()` reporting total spent, transaction count, and average per category.
  4. `Payment_Methods`: Breakdown by UPI, Cash, Cards, and Net Banking.

---

## 🔒 Security Best Practice
- Never commit your private `credentials.json` file to a public GitHub repository.
- A `.gitignore` has been included to keep your credentials and local SQLite database secure.
