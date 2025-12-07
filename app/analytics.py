"""
FILE: app/analytics.py
DESCRIPTION:
    This file contains the business logic and data analysis algorithms. 
    It processes raw data from the database to provide insights for stakeholders.

TEAM TASKS:
    1. Import pandas for data manipulation.
    2. Implement 'check_at_risk_students()': Logic to find students with high stress (e.g., > 4).
       - This is for the Wellbeing Officer.
    3. Implement 'calculate_attendance_vs_grades()': Join attendance and submission data.
       - This is for the Course Director.
    4. Provide functions that return Pandas DataFrames for easy plotting.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import date

# Supports relative imports within packages and direct execution of scripts
try:
    from .db_manager import DatabaseManager
except ImportError:
    from db_manager import DatabaseManager

# Initialize DBManager
db_manager = DatabaseManager()


# ------------------------------------------
# 1. Wellbeing Analysis
# ------------------------------------------
from typing import Optional

def check_at_risk_students(stress_threshold: int = 4, visualize: bool = True, on_date: Optional[str] = None, latest_only: bool = False) -> pd.DataFrame:
    """
    Identify high-risk students based on stress_level >= threshold.
    Returns a sorted DataFrame with most recent entries first.
    """
    survey_data = db_manager.get_raw_survey_data()
    survey_df = pd.DataFrame(survey_data)

    if survey_df.empty:
        return pd.DataFrame(columns=['student_id', 'stress_level', 'sleep_hours', 'date', 'Is_At_Risk'])

    # Standardize field types to prevent deduplication failures due to inconsistent types
    survey_df['student_id'] = survey_df['student_id'].astype(str).str.strip()
    survey_df['stress_level'] = pd.to_numeric(survey_df['stress_level'], errors='coerce')
    survey_df['sleep_hours'] = pd.to_numeric(survey_df['sleep_hours'], errors='coerce')

    survey_df['Is_At_Risk'] = survey_df['stress_level'] >= stress_threshold
    survey_df['date'] = pd.to_datetime(survey_df['date'])

    # Date/Duplicate Filter
    if on_date:
        try:
            target_date = pd.to_datetime(on_date).date()
            survey_df = survey_df[survey_df['date'].dt.date == target_date]
        except Exception:
            # If the date cannot be parsed, do not filter
            pass
    elif latest_only:
        survey_df = survey_df.sort_values(['student_id', 'date']).drop_duplicates('student_id', keep='last')

    # Visualization: stress_level distribution
    if visualize:
        plt.figure(figsize=(6, 4))
        sns.countplot(data=survey_df, x='stress_level', hue='Is_At_Risk', palette='Reds')
        plt.title("Stress Level Distribution (Red = At Risk)")
        plt.xlabel("Stress Level")
        plt.ylabel("Count")
        plt.legend(title="At Risk")
        plt.tight_layout()
        plt.show()
        plt.close()

    # Final deduplication: Ensure each student appears only once (take the latest record from the student's filter set)
    at_risk_df = survey_df[survey_df['Is_At_Risk']]
    if not at_risk_df.empty:
        at_risk_df = (
            at_risk_df.sort_values(['student_id', 'date'])
                      .drop_duplicates('student_id', keep='last')
                      .sort_values(by='date', ascending=False)
        )
    return at_risk_df


# ------------------------------------------
# 2. Attendance vs Grades Analysis
# ------------------------------------------
def calculate_attendance_vs_grades(visualize: bool = True) -> dict:
    """
    Calculates:
        - Global correlation between average attendance & average score
        - Per-course correlation
    Handles Many-to-Many structure via Enrollment table.
    """
    att_data, grade_data = db_manager.get_analytics_data()
    att_df = pd.DataFrame(att_data)
    grade_df = pd.DataFrame(grade_data)

    if att_df.empty or grade_df.empty:
        return {"Global_Correlation_R": None, "Per_Course_Correlation": pd.DataFrame()}

    # Attendance State Quantization
    att_df['attendance_numeric'] = att_df['status'].apply(lambda x: 1 if x == 'Present' else 0)

    # Get the Enrollment table
    conn = db_manager.get_connection()
    enrollment_df = pd.DataFrame(conn.execute("SELECT student_id, course_id FROM Enrollment").fetchall(),
                                 columns=['student_id', 'course_id'])
    courses_df = pd.DataFrame(conn.execute("SELECT id, name FROM Courses").fetchall(),
                              columns=['course_id', 'course_name'])
    conn.close()

    # Corresponding courses for Attendance and Enrollment
    att_df = pd.merge(att_df, enrollment_df, on='student_id', how='inner')

    # Match Submissions with Enrollment courses
    grade_df = pd.merge(grade_df, enrollment_df, on='student_id', how='inner')

    # --- Global Analysis ---
    global_att = att_df.groupby('student_id')['attendance_numeric'].mean().reset_index(name='avg_attendance_rate')
    global_grade = grade_df.groupby('student_id')['score'].mean().reset_index(name='avg_score')
    global_df = pd.merge(global_att, global_grade, on='student_id', how='inner')
    global_correlation = global_df['avg_attendance_rate'].corr(global_df['avg_score']) if len(global_df) >= 2 else None

    # Visualization: Global Relationships
    if visualize and not global_df.empty:
        plt.figure(figsize=(6, 4))
        sns.scatterplot(data=global_df, x='avg_attendance_rate', y='avg_score')
        plt.title(f"Global Attendance vs Grades (R={global_correlation:.2f})")
        plt.xlabel("Average Attendance Rate")
        plt.ylabel("Average Score")
        plt.tight_layout()
        plt.show()
        plt.close()

    # --- Analysis by Course ---
    course_corr_list = []
    for course_id in enrollment_df['course_id'].unique():
        course_att = att_df[att_df['course_id'] == course_id].groupby('student_id')['attendance_numeric'].mean()
        course_grade = grade_df[grade_df['course_id'] == course_id].groupby('student_id')['score'].mean()
        course_df = pd.merge(course_att.reset_index(), course_grade.reset_index(), on='student_id', how='inner')
        if len(course_df) >= 2:
            r = course_df['attendance_numeric'].corr(course_df['score'])
        else:
            r = None
        course_name = courses_df.loc[courses_df['course_id'] == course_id, 'course_name'].values[0]
        course_corr_list.append({'course_id': course_id, 'course_name': course_name, 'Correlation_R': r})

        # Visualization: Relationships between courses
        if visualize and not course_df.empty:
            plt.figure(figsize=(5, 4))
            sns.scatterplot(data=course_df, x='attendance_numeric', y='score')
            plt.title(f"{course_name}: Attendance vs Grades")
            plt.xlabel("Average Attendance Rate")
            plt.ylabel("Average Score")
            plt.tight_layout()
            plt.show()
            plt.close()

    course_corr_df = pd.DataFrame(course_corr_list)
    return {"Global_Correlation_R": global_correlation, "Per_Course_Correlation": course_corr_df}


# ------------------------------------------
# 3. Main Execution (for VSCode Run)
# ------------------------------------------
if __name__ == '__main__':
    print("--- Wellbeing Analysis ---")
    risk_df = check_at_risk_students()
    print(f"High-risk students: {len(risk_df['student_id'].unique())}")
    if not risk_df.empty:
        try:
            print(risk_df.head().to_markdown(index=False))
        except ImportError:
            print(risk_df.head())

    print("\n--- Attendance vs Grades ---")
    corr_results = calculate_attendance_vs_grades()
    if corr_results['Global_Correlation_R'] is not None:
        print(f"Global correlation (attendance vs score): {corr_results['Global_Correlation_R']:.4f}")
    else:
        print("Global correlation: Not enough data.")

    per_course_df = corr_results['Per_Course_Correlation']
    if not per_course_df.empty:
        try:
            print(per_course_df.to_markdown(index=False))
        except ImportError:
            print(per_course_df)
    else:
        print("Per-course correlation: Not enough data.")