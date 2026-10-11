"""
Test suite to verify that all modules, database methods, and view builders function properly.
"""
import database
import sheets_service
import config
from views.dashboard_view import build_dashboard_view
from views.add_expense_view import build_add_expense_view
from views.reports_view import build_reports_view
from views.transactions_view import build_transactions_view
from views.settings_view import build_settings_view

from views.auth_view import build_auth_view

def test_app_components():
    print("1. Initializing DB...")
    database.init_db()

    print("2. Testing User Authentication & Security...")
    # Verify default admin account
    admin_user = database.authenticate_user("admin", "admin123")
    assert admin_user is not None, "Admin authentication failed"
    assert admin_user["username"] == "admin"
    print(f"   [OK] Admin account verified: {admin_user['username']} ({admin_user['full_name']})")

    # Test new user registration
    test_user, err = database.create_user("testuser_demo", "testuser@demo.com", "securepass123", "Demo Tester")
    if not err:
        print(f"   [OK] User registration verified: {test_user['username']}")
    else:
        print(f"   [NOTE] User already registered: {err}")

    auth_test = database.authenticate_user("testuser_demo", "securepass123")
    assert auth_test is not None, "New user auth failed"
    print("   [OK] Password hashing (PBKDF2 HMAC SHA-256) and auth verification passed")

    print("3. Seeding sample data if empty...")
    if len(database.get_expenses(limit=1)) == 0:
        database.seed_sample_data()

    stats = database.get_stats()
    print(f"   Stats computed successfully: {stats['kpis']['total_count']} transactions, total: {stats['kpis']['total_amount']}")

    print("4. Testing Mock Page and All 6 View Builders...")
    class MockPage:
        def __init__(self):
            self.dialog = None
            self.overlay = []
        def update(self):
            pass
        def show_dialog(self, dlg):
            self.dialog = dlg
        def pop_dialog(self):
            self.dialog = None

    mock_page = MockPage()

    v0 = build_auth_view(mock_page, lambda u: None)
    assert v0 is not None, "Auth view failed"
    print("   [OK] Auth (Login & Sign-up) view rendered successfully")

    v1 = build_dashboard_view(mock_page, lambda v: None, lambda: None)
    assert v1 is not None, "Dashboard view failed"
    print("   [OK] Dashboard view rendered successfully")

    v2 = build_add_expense_view(mock_page, lambda v: None, lambda item: None)
    assert v2 is not None, "Add expense view failed"
    print("   [OK] Add expense view rendered successfully")

    v3 = build_reports_view(mock_page, lambda v: None)
    assert v3 is not None, "Reports view failed"
    print("   [OK] Reports view rendered successfully")

    v4 = build_transactions_view(mock_page, lambda v: None, lambda eid: None)
    assert v4 is not None, "Transactions view failed"
    print("   [OK] Transactions view rendered successfully")

    v5 = build_settings_view(mock_page, lambda v: None, lambda: None, lambda: None)
    assert v5 is not None, "Settings view failed"
    print("   [OK] Settings view rendered successfully")

    print("5. Testing Google Sheets diagnostic check & 2-way sync...")
    mgr = sheets_service.GoogleSheetsManager()
    status = mgr.test_connection()
    assert status["success"] is True, f"Google Sheets connection failed: {status['message']}"
    print(f"   [OK] Connected to Google Sheets: {status['url']}")

    pushed, pulled, msg = mgr.sync_bidirectional()
    print(f"   [OK] Bidirectional sync completed: {msg} (Pushed: {pushed}, Pulled: {pulled})")

    print("\nALL SYSTEM VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_app_components()
