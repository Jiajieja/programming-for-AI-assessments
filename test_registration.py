"""
FILE: test_registration.py
DESCRIPTION: Test script for the registration functionality.
"""
from app.db_manager import DatabaseManager

def test_registration():
    print("=" * 60)
    print("注册功能测试 (Registration Functionality Test)")
    print("=" * 60)
    
    db = DatabaseManager()
    
    # Test 1: Valid registration for Wellbeing Officer
    print("\n--- Test 1: Valid registration for Wellbeing Officer ---")
    success, msg = db.register_user("test_wellbeing_1", "password123", 1)
    print(f"result: {'success' if success else 'fail'}")
    print(f"information: {msg}")
    
    # Test 2: Valid registration for Course Director
    print("\n--- Test 2: Valid registration for Course Director ---")
    success, msg = db.register_user("test_director_1", "password456", 2)
    print(f"result: {'success' if success else 'fail'}")
    print(f"information: {msg}")
    
    # Test 3: Duplicate username
    print("\n--- Test 3: Duplicate username ---")
    success, msg = db.register_user("test_wellbeing_1", "password789", 1)
    print(f"result: {'Correctly rejected' if not success else 'Should not have succeeded'}")
    print(f"information: {msg}")
    
    # Test 4: Username too short
    print("\n--- Test 4: Username too short ---")
    success, msg = db.register_user("ab", "password123", 1)
    print(f"result: {'Correctly rejected' if not success else 'Should not have succeeded'}")
    print(f"information: {msg}")
    
    # Test 5: Username too long
    print("\n--- Test 5: Username too long (max is 50 symbols) ---")
    long_username = "a" * 51
    success, msg = db.register_user(long_username, "password123", 1)
    print(f"result: {'Correctly rejected' if not success else 'Should not have succeeded'}")
    print(f"information: {msg}")
    
    # Test 6: Password too short
    print("\n--- # Test 6: Password too short ---")
    success, msg = db.register_user("test_user_short_pwd", "12345", 1)
    print(f"result: {'Correctly rejected' if not success else 'Should not have succeeded'}")
    print(f"information: {msg}")
    
    # Test 7: Invalid role ID
    print("\n--- Test 7: Invalid role ID ---")
    success, msg = db.register_user("test_user_invalid_role", "password123", 3)
    print(f"result: {'Correctly rejected' if not success else 'Should not have succeeded'}")
    print(f"information: {msg}")
    
    # Test 8: Login with newly registered account
    print("\n--- Test 8: Login with newly registered account ---")
    user = db.verify_login("test_wellbeing_1", "password123")
    if user:
        print(f"Login successful")
        print(f"username: {user.username}")
        print(f"role: {user.role_name}")
        print(f"role ID: {user.role_id}")
    else:
        print(f"Login failed")
    
    # Test 9: Login with wrong password
    print("\n--- Test 9: Login with wrong password ---")
    user = db.verify_login("test_wellbeing_1", "wrongpassword")
    if user is None:
        print(f"Correctly rejected: Incorrect password")
    else:
        print(f"Should not have succeeded: Login with an incorrect password")
    
    # Test 10: Empty username
    print("\n--- Test 10: Empty username ---")
    success, msg = db.register_user("", "password123", 1)
    print(f"result: {'Correctly rejected' if not success else 'Should not have succeeded'}")
    print(f"information: {msg}")
    
    # Test 11: Empty password
    print("\n--- Test 11: Empty password ---")
    success, msg = db.register_user("test_user_empty_pwd", "", 1)
    print(f"result: {'Correctly rejected' if not success else 'Should not have succeeded'}")
    print(f"information: {msg}")
    
    print("\n" + "=" * 60)
    print("测试完成 (Test Complete)")
    print("=" * 60)

if __name__ == "__main__":
    test_registration()

