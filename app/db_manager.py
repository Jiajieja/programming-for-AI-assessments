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
from .models import User, Student, Course, Assessment, Submission, WellbeingResponse

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

    def get_all_students(self):
        """READ: Get all active students (Without course_id)."""
        conn = self.get_connection()
        # 注意：这里取出的列必须和 schema.sql 对应，不再包含 course_id
        rows = conn.execute("SELECT * FROM Students WHERE status = 'Active'").fetchall()
        conn.close()
        # 适配新的 Student 模型 (id, graduation_date, status)
        return [Student(row['id'], row['graduation_date'], row['status']) for row in rows]
    
    def get_students_by_course(self, course_id):
        """
        READ: Get all students enrolled in a specific course.
        Used to verify Enrollment.
        """
        conn = self.get_connection()
        # 这里使用了 JOIN 查询：连接 Students 和 Enrollment 表
        sql = """
            SELECT s.id, s.graduation_date, s.status 
            FROM Students s
            JOIN Enrollment e ON s.id = e.student_id
            WHERE e.course_id = ? AND s.status = 'Active'
        """
        rows = conn.execute(sql, (course_id,)).fetchall()
        conn.close()
        
        # 返回 Student 对象列表 (注意：Student 类已经不再需要 course_id 了)
        return [Student(row['id'], row['graduation_date'], row['status']) for row in rows]

    def add_student(self, student_id, course_id, graduation_date):
        """
        CREATE: Add a new student AND enroll them in a course.
        Logic: 
        1. Insert/Check Student in 'Students' table.
        2. Insert record in 'Enrollment' table.
        """
        conn = self.get_connection()
        try:
            # 第一步：插入学生基础信息
            # 使用 INSERT OR IGNORE，如果学生 ID 575001 已经存在（比如他之前选过别的课），
            # 这里就不会报错，直接进行下一步选课。
            sql_student = "INSERT OR IGNORE INTO Students (id, graduation_date, status) VALUES (?, ?, 'Active')"
            conn.execute(sql_student, (student_id, graduation_date))
            
            # 第二步：插入选课记录 (连接表)
            # 这才是真正把学生和课程关联起来的地方
            sql_enroll = "INSERT INTO Enrollment (student_id, course_id) VALUES (?, ?)"
            conn.execute(sql_enroll, (student_id, course_id))
            
            conn.commit()
            return True, "Success: Student enrolled."
        except sqlite3.IntegrityError as e:
            # 比如重复选了同一门课 (联合主键冲突)
            return False, f"Error: {e}"
        finally:
            conn.close()

    def delete_student(self, student_id):
        """
        DELETE: Remove a student and their enrollment records.
        """
        conn = self.get_connection()
        try:
            # 1. 先删除选课记录 (Child table)
            conn.execute("DELETE FROM Enrollment WHERE student_id = ?", (student_id,))
            # 2. 再删除学生本体 (Parent table)
            conn.execute("DELETE FROM Students WHERE id = ?", (student_id,))
            
            conn.commit()
            return True, "Student and records deleted."
        except sqlite3.IntegrityError:
            return False, "Cannot delete: Student has other related records (e.g. Grades)."
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