"""
FILE: app/database_manager.py
DESCRIPTION: 
    The core engine for SQL interactions.
    - STATIC Tables (Roles, Courses): Read-only helpers.
    - DYNAMIC Tables (Students, Surveys, etc.): Full CRUD support.
"""
import sqlite3
import os
from datetime import date
try:
    from .models import User, Student, Course, Assessment, Submission, WellbeingResponse
except ImportError:
    from models import User, Student, Course, Assessment, Submission, WellbeingResponse

class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            # 自动定位到 data/university.db
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(base_dir, 'data', 'university.db')
        else:
            self.db_path = db_path

    def get_connection(self):
        """Standard connection helper with Row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row # Allows row['column_name']
        conn.execute("PRAGMA foreign_keys = ON") # Vital for data integrity
        return conn

    # =====================================================
    # 1. AUTHENTICATION (登录模块)
    # =====================================================
    
    def verify_login(self, username, password):
        """
        Check credentials. Returns a User object if valid, else None.
        """
        conn = self.get_connection()
        # Join with Roles to get the role name immediately
        sql = """
            SELECT u.id, u.username, u.role_id, r.name as role_name 
            FROM Users u
            JOIN Roles r ON u.role_id = r.id
            WHERE u.username = ? AND u.password = ?
        """
        row = conn.execute(sql, (username, password)).fetchone()
        conn.close()
        
        if row:
            return User(row['id'], row['username'], row['role_id'], row['role_name'])
        return None

    # =====================================================
    # 2. STATIC DATA HELPERS (用于前端下拉菜单)
    # =====================================================

    def get_all_courses(self):
        """
        READ-ONLY: Get list of all courses.
        Frontend uses this for the 'Select Course' dropdown.
        """
        conn = self.get_connection()
        rows = conn.execute("SELECT * FROM Courses").fetchall()
        conn.close()
        # Return objects, or simple dicts if you haven't made a Course model
        # Assuming you made a Course class in models.py:
        return [Course(row['id'], row['name']) for row in rows]

    # =====================================================
    # 3. STUDENT MANAGEMENT (CRUD: 增删改查)
    # =====================================================

    # def get_all_students(self):
    #     """READ: Get all active students."""
    #     conn = self.get_connection()
    #     rows = conn.execute("SELECT * FROM Students WHERE status = 'Active'").fetchall()
    #     conn.close()
    #     return [Student(row['id'], row['graduation_date'], row['status']) for row in rows]
    
    # def add_student(self, student_id, graduation_date):
    #     """
    #     CREATE: Add a new student. 
    #     """
    #     conn = self.get_connection() 
    #     try:
    #         sql = "INSERT INTO Students (id, graduation_date, status) VALUES (?, ?, ?, 'Active')"
    #         conn.execute(sql, (student_id, graduation_date))
    #         conn.commit()
    #         return True, "Success"
    #     except sqlite3.IntegrityError as e:
    #         # 即使报错，这里也不需要做特殊的关闭操作，因为会走 finally
    #         return False, f"Error: Student ID {student_id} already exists."
    #     finally:
    #         # 无论 try 成功还是 except 报错，这里永远会执行
    #         conn.close()

    # # def add_student(self, student_id, course_id, graduation_date):
    # #     """
    # #     CREATE: Add a new student. 
    # #     'course_id' comes from the dropdown (Static Data).
    # #     """
    # #     try:
    # #         conn = self.get_connection()
    # #         sql = "INSERT INTO Students (id, course_id, graduation_date, status) VALUES (?, ?, ?, 'Active')"
    # #         conn.execute(sql, (student_id, course_id, graduation_date))
    # #         conn.commit()
    # #         conn.close()
    # #         return True, "Success"
    # #     except sqlite3.IntegrityError as e:
    # #         return False, f"Error: Student ID {student_id} already exists."

    # def update_student_status(self, student_id, new_status):
    #     """
    #     UPDATE: Change status (e.g., 'Active' -> 'Inactive').
    #     """
    #     conn = self.get_connection()
    #     sql = "UPDATE Students SET status = ? WHERE id = ?"
    #     conn.execute(sql, (new_status, student_id))
    #     conn.commit()
    #     conn.close()
    #     return True

    # def delete_student(self, student_id):
    #     conn = self.get_connection()
    #     try:
    #         conn.execute("DELETE FROM Students WHERE id = ?", (student_id,))
    #         conn.commit()
    #         return True, "Student deleted."
    #     except sqlite3.IntegrityError:
    #         return False, "Cannot delete: Student has related records."
    #     finally:
    #         conn.close() 

    # def delete_student(self, student_id):
    #     """
    #     DELETE: Remove a student.
    #     Note: Because of Foreign Keys, this might fail if they have Attendance records.
    #     """
    #     try:
    #         conn = self.get_connection()
    #         conn.execute("DELETE FROM Students WHERE id = ?", (student_id,))
    #         conn.commit()
    #         conn.close()
    #         return True, "Student deleted."
    #     except sqlite3.IntegrityError:
    #         return False, "Cannot delete: Student has related records (Grades/Attendance)."

    # =====================================================
    # 3. STUDENT MANAGEMENT (Updated for Enrollment Table)
    # =====================================================

    def get_all_students(self, include_inactive: bool = False):
        """READ: 列出学生（默认仅 Active）。"""
        conn = self.get_connection()
        if include_inactive:
            rows = conn.execute("SELECT * FROM Students").fetchall()
        else:
            rows = conn.execute("SELECT * FROM Students WHERE status = 'Active'").fetchall()
        conn.close()
        return [Student(row['id'], row['graduation_date'], row['status']) for row in rows]

    def get_student(self, student_id):
        """READ: 根据 ID 获取单个学生。"""
        conn = self.get_connection()
        row = conn.execute("SELECT * FROM Students WHERE id = ?", (student_id,)).fetchone()
        conn.close()
        if not row:
            return None
        return Student(row['id'], row['graduation_date'], row['status'])

    def get_courses_by_student(self, student_id):
        """READ: 获取某学生所选课程列表。返回 [Course]。"""
        conn = self.get_connection()
        sql = """
            SELECT c.id, c.name
            FROM Courses c
            JOIN Enrollment e ON c.id = e.course_id
            WHERE e.student_id = ?
            ORDER BY c.id
        """
        rows = conn.execute(sql, (student_id,)).fetchall()
        conn.close()
        return [Course(row['id'], row['name']) for row in rows]
    
    def get_students_by_course(self, course_id):
        """
        READ: 获取某课程下的学生（Active）。
        """
        conn = self.get_connection()
        sql = """
            SELECT s.id, s.graduation_date, s.status 
            FROM Students s
            JOIN Enrollment e ON s.id = e.student_id
            WHERE e.course_id = ? AND s.status = 'Active'
        """
        rows = conn.execute(sql, (course_id,)).fetchall()
        conn.close()
        return [Student(row['id'], row['graduation_date'], row['status']) for row in rows]

    def add_student(self, student_id, course_id, graduation_date):
        """
        CREATE: 新建学生并选课。
        1) 插入 Students（如果已存在则忽略）
        2) 插入 Enrollment（建立关联）
        """
        conn = self.get_connection()
        try:
            sql_student = "INSERT OR IGNORE INTO Students (id, graduation_date, status) VALUES (?, ?, 'Active')"
            conn.execute(sql_student, (student_id, graduation_date))
            sql_enroll = "INSERT INTO Enrollment (student_id, course_id) VALUES (?, ?)"
            conn.execute(sql_enroll, (student_id, course_id))
            conn.commit()
            return True, "Success: Student enrolled."
        except sqlite3.IntegrityError as e:
            return False, f"Error: {e}"
        finally:
            conn.close()

    def enroll_student(self, student_id, course_id):
        """CREATE: 仅添加选课关联。"""
        conn = self.get_connection()
        try:
            conn.execute("INSERT INTO Enrollment (student_id, course_id) VALUES (?, ?)", (student_id, course_id))
            conn.commit()
            return True, "Enrolled."
        except sqlite3.IntegrityError as e:
            return False, f"Error: {e}"
        finally:
            conn.close()

    def remove_enrollment(self, student_id, course_id):
        """DELETE: 取消某学生对某课程的选课。"""
        conn = self.get_connection()
        conn.execute("DELETE FROM Enrollment WHERE student_id = ? AND course_id = ?", (student_id, course_id))
        conn.commit()
        conn.close()
        return True, "Enrollment removed."

    def update_student_status(self, student_id, new_status):
        """UPDATE: 修改学生状态。"""
        conn = self.get_connection()
        conn.execute("UPDATE Students SET status = ? WHERE id = ?", (new_status, student_id))
        conn.commit()
        conn.close()
        return True, "Status updated."

    def update_student_graduation(self, student_id, graduation_date):
        """UPDATE: 修改学生毕业日期。"""
        conn = self.get_connection()
        conn.execute("UPDATE Students SET graduation_date = ? WHERE id = ?", (graduation_date, student_id))
        conn.commit()
        conn.close()
        return True, "Graduation date updated."

    def delete_student(self, student_id):
        """
        DELETE: 级联删除学生相关记录（手动级联），以避免外键约束报错。
        依次删除：
          - Submissions（成绩）
          - Attendance（出勤）
          - Wellbeing_Surveys（健康问卷回答）
          - Enrollment（选课关联）
          - Students（学生本体）
        """
        conn = self.get_connection()
        try:
            # 手动级联删除子表记录
            conn.execute("DELETE FROM Submissions WHERE student_id = ?", (student_id,))
            conn.execute("DELETE FROM Attendance WHERE student_id = ?", (student_id,))
            conn.execute("DELETE FROM Wellbeing_Surveys WHERE student_id = ?", (student_id,))
            conn.execute("DELETE FROM Enrollment WHERE student_id = ?", (student_id,))
            # 最后删除学生
            conn.execute("DELETE FROM Students WHERE id = ?", (student_id,))
            conn.commit()
            return True, "Student and related records deleted."
        except sqlite3.IntegrityError as e:
            return False, f"Cannot delete due to FK constraints: {e}"
        finally:
            conn.close()
        
        

    # =====================================================
    # 4. ACADEMIC OPERATIONS (Dynamic Data)
    # =====================================================

    def add_assessment(self, title, course_id, deadline, max_score=100):
        """CREATE: Course Director adds a new assignment."""
        conn = self.get_connection()
        sql = "INSERT INTO Assessments (title, course_id, deadline, max_score) VALUES (?, ?, ?, ?)"
        conn.execute(sql, (title, course_id, deadline, max_score))
        conn.commit()
        conn.close()

    def record_submission(self, assessment_id, student_id, date, score):
        """CREATE/UPDATE: Record a grade."""
        conn = self.get_connection()
        # Uses REPLACE logic (if already exists, update it)
        sql = """
            INSERT OR REPLACE INTO Submissions (assessment_id, student_id, submission_date, score)
            VALUES (?, ?, ?, ?)
        """
        conn.execute(sql, (assessment_id, student_id, date, score))
        conn.commit()
        conn.close()

    def log_attendance(self, student_id, course_id, date, status):
        """CREATE: Log weekly attendance."""
        try:
            conn = self.get_connection()
            sql = "INSERT INTO Attendance (student_id, course_id, lecture_date, status) VALUES (?, ?, ?, ?)"
            conn.execute(sql, (student_id, course_id, date, status))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False # Duplicate entry for same day

    # =====================================================
    # 5. WELLBEING OPERATIONS (Complex Logic)
    # =====================================================

    def log_survey_response(self, student_id, stress_level, sleep_hours):
        """
        CREATE: Handles the 'Double Insert' logic for surveys.
        """
        today = date.today().isoformat()
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Check if today's Survey Definition exists
            cursor.execute("SELECT id FROM Surveys WHERE passed_date = ?", (today,))
            survey_row = cursor.fetchone()
            
            if survey_row:
                survey_id = survey_row['id']
            else:
                cursor.execute("INSERT INTO Surveys (passed_date) VALUES (?)", (today,))
                survey_id = cursor.lastrowid
            
            # 2. Insert the Student's Response
            sql = """
                INSERT INTO Wellbeing_Surveys (survey_id, student_id, stress_level, sleep_hours)
                VALUES (?, ?, ?, ?)
            """
            cursor.execute(sql, (survey_id, student_id, stress_level, sleep_hours))
            conn.commit()
            return True, "Survey logged."
        except sqlite3.IntegrityError:
            return False, "You have already submitted a survey for today."
        finally:
            conn.close()

    # =====================================================
    # 6. ANALYTICS DATA PROVIDERS (For Team B)
    # =====================================================

    def get_raw_survey_data(self):
        """
        READ: Fetch data for Wellbeing Analytics.
        Returns List[Dict] because this is for Pandas processing.
        """
        conn = self.get_connection()
        sql = """
            SELECT ws.student_id, ws.stress_level, ws.sleep_hours, s.passed_date as date
            FROM Wellbeing_Surveys ws
            JOIN Surveys s ON ws.survey_id = s.id
            ORDER BY s.passed_date DESC
        """
        data = [dict(row) for row in conn.execute(sql).fetchall()]
        conn.close()
        return data

    def get_analytics_data(self):
        """
        READ: Fetch Attendance and Grades for Correlation Analytics.
        Returns two lists of dicts.
        """
        conn = self.get_connection()
        
        att_data = [dict(r) for r in conn.execute("SELECT student_id, status FROM Attendance").fetchall()]
        grade_data = [dict(r) for r in conn.execute("SELECT student_id, score FROM Submissions").fetchall()]
        
        conn.close()
        return att_data, grade_data