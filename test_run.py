"""
FILE: test_run.py
DESCRIPTION: Manual test script updated for the new Many-to-Many Enrollment schema.
"""
from app.db_manager import DatabaseManager

def main():
    print("🚀 Starting System Test (Enrollment Update Version)...\n")
    
    # 1. Initialize Database Manager
    db = DatabaseManager()
    
    # ==========================================
    # Test 1: Login Functionality
    # ==========================================
    print("--- 1. Testing Login ---")
    user = db.verify_login("will_b", "test123")
    
    if user:
        print(f"✅ Login Successful! User: {user.username}, Role: {user.role_name}")
    else:
        print("❌ Login Failed (Unexpected)")

    # ==========================================
    # Test 2: Get Static Data (Courses)
    # ==========================================
    print("\n--- 2. Testing Get Course List ---")
    courses = db.get_all_courses()
    for c in courses:
        print(f"   Course: {c.name} (ID: {c.id})")
    
    if len(courses) > 0:
        print("✅ Successfully retrieved course list")

    # ==========================================
    # Test 3: Student CRUD (Add Student & Enroll)
    # ==========================================
    print("\n--- 3. Testing Add Student & Enrollment ---")
    
    new_student_id = 88888
    target_course_id = 1  # Assuming Course ID 1 exists (e.g., 'Applied Statistics')
    
    # Step A: Add Student AND Enroll them in one go
    # (The updated db_manager.py handles the two-step insert automatically)
    print(f"   > Attempting to add Student {new_student_id} and enroll in Course {target_course_id}...")
    
    success, msg = db.add_student(new_student_id, target_course_id, '2027-01-01')
    
    if success:
        print(f"✅ {msg}")
    else:
        print(f"⚠️ {msg}")

    # Step B: Verify Student Exists
    all_students = db.get_all_students()
    found_student = False
    for s in all_students:
        if s.id == new_student_id:
            found_student = True
            # Note: s.course_id no longer exists on the Student object, so we don't check it here
            break
    
    if found_student:
        print(f"✅ Verified: Student {new_student_id} exists in 'Students' table.")

    # Step C: Verify Enrollment (New Test!)
    # We call the helper method to see if this student shows up in the course list
    print(f"   > Verifying enrollment in Course {target_course_id}...")
    enrolled_students = db.get_students_by_course(target_course_id)
    
    found_enrollment = False
    for s in enrolled_students:
        if s.id == new_student_id:
            found_enrollment = True
            break
            
    if found_enrollment:
        print(f"✅ Verified: Student {new_student_id} is correctly linked to Course {target_course_id}.")
    else:
        print(f"❌ Error: Student created but NOT found in Course {target_course_id} list.")

    # ==========================================
    # Test 4: Log Survey (Survey Logic)
    # ==========================================
    print("\n--- 4. Testing Log Survey ---")
    success, msg = db.log_survey_response(student_id=new_student_id, stress_level=3, sleep_hours=7.0)
    print(f"   Log Result: {success} - {msg}")

    # ==========================================
    # Test 5: Analytics Data Fetch
    # ==========================================
    print("\n--- 5. Testing Analytics Data Fetch ---")
    raw_survey = db.get_raw_survey_data()
    print(f"   [Wellbeing] Retrieved {len(raw_survey)} survey records")
    
    att_data, grade_data = db.get_analytics_data()
    print(f"   [Course Director] Retrieved {len(att_data)} attendance records")
    print(f"   [Course Director] Retrieved {len(grade_data)} submission records")
    
    print("\n🎉 Test Complete!")

if __name__ == "__main__":
    main()