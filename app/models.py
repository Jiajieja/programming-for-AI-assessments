"""
FILE: app/models.py
DESCRIPTION: 
    Defines Python classes (Data Models) using standard OOP syntax.
"""

# ==========================================
# 1. User & Role Models
# ==========================================

class User:
    def __init__(self, id, username, role_id, role_name=None):
        self.id = id
        self.username = username
        self.role_id = role_id
        self.role_name = role_name

    def __repr__(self):
        return f"<User {self.username}>"

class Role:
    def __init__(self, id, name):
        self.id = id
        self.name = name

# ==========================================
# 2. Academic Entities
# ==========================================

class Course: 
    def __init__(self, id, name):
        self.id = id
        self.name = name

# class Student:
#     def __init__(self, id, course_id, graduation_date, status):
#         self.id = id
#         self.course_id = course_id
#         self.graduation_date = graduation_date
#         self.status = status

#     def is_active(self):
#         return self.status == 'Active'
# app/models.py (Partial Update)

class Student:
    # 删掉了 course_id，因为它现在在 Enrollment 表里
    def __init__(self, id, graduation_date, status):
        self.id = id
        self.graduation_date = graduation_date
        self.status = status

    def is_active(self):
        return self.status == 'Active'
    
    def __repr__(self):
        return f"<Student {self.id}>"

# ==========================================
# 3. Assessment & Performance Models
# ==========================================

class Assessment: 
    def __init__(self, id, title, course_id, deadline, max_score):
        self.id = id
        self.title = title
        self.course_id = course_id
        self.deadline = deadline
        self.max_score = max_score

class Submission:
    def __init__(self, id, assessment_id, student_id, submission_date, score):
        self.id = id
        self.assessment_id = assessment_id
        self.student_id = student_id
        self.submission_date = submission_date
        self.score = score

# ==========================================
# 4. Wellbeing Models
# ==========================================

class WellbeingResponse:
    def __init__(self, id, survey_id, student_id, stress_level, sleep_hours):
        self.id = id
        self.survey_id = survey_id
        self.student_id = student_id
        self.stress_level = stress_level
        self.sleep_hours = sleep_hours

    def is_high_risk(self, threshold=4):
        return self.stress_level >= threshold