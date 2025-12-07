"""
FILE: app/analytic_data.py
DESCRIPTION:
    A collection of analysis and plotting functions for Flask visualization.
    - Course director analysis: global scatter plot, by course correlation, course mean scatter plot, stress level histogram
    - Individual student time series: stress/sleep over time
    - Returns a Matplotlib Figure (server outputs PNG), no plt.show() here
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# In-package/script-based import compatibility
try:
    from .db_manager import DatabaseManager
except ImportError:
    from db_manager import DatabaseManager

# Global DB Manager
db_manager = DatabaseManager()

# ------------------------------
# Basic data acquisition
# ------------------------------

def _get_attendance_grade():
    att_data, grade_data = db_manager.get_analytics_data()
    return pd.DataFrame(att_data), pd.DataFrame(grade_data)


def _get_survey_df():
    data = db_manager.get_raw_survey_data()
    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame(columns=["student_id","stress_level","sleep_hours","date"])
    df["date"] = pd.to_datetime(df["date"]) 
    return df


# ------------------------------
# Attendance vs. Performance (Data and Visualization)
# ------------------------------

def calculate_attendance_vs_grades(visualize: bool = False) -> dict:
    att_df, grade_df = _get_attendance_grade()
    if att_df.empty or grade_df.empty:
        return {"Global_Correlation_R": None, "Per_Course_Correlation": pd.DataFrame()}

    att_df['attendance_numeric'] = att_df['status'].apply(lambda x: 1 if x == 'Present' else 0)

    conn = db_manager.get_connection()
    enrollment_df = pd.DataFrame(conn.execute("SELECT student_id, course_id FROM Enrollment").fetchall(),
                                 columns=['student_id', 'course_id'])
    courses_df = pd.DataFrame(conn.execute("SELECT id, name FROM Courses").fetchall(),
                              columns=['course_id', 'course_name'])
    conn.close()

    att_df = pd.merge(att_df, enrollment_df, on='student_id', how='inner')
    grade_df = pd.merge(grade_df, enrollment_df, on='student_id', how='inner')

    global_att = att_df.groupby('student_id')['attendance_numeric'].mean().reset_index(name='avg_attendance_rate')
    global_grade = grade_df.groupby('student_id')['score'].mean().reset_index(name='avg_score')
    global_df = pd.merge(global_att, global_grade, on='student_id', how='inner')
    global_correlation = global_df['avg_attendance_rate'].corr(global_df['avg_score']) if len(global_df) >= 2 else None

    course_corr_list = []
    for course_id in enrollment_df['course_id'].unique():
        course_att = att_df[att_df['course_id'] == course_id].groupby('student_id')['attendance_numeric'].mean()
        course_grade = grade_df[grade_df['course_id'] == course_id].groupby('student_id')['score'].mean()
        course_df = pd.merge(course_att.reset_index(), course_grade.reset_index(), on='student_id', how='inner')
        r = course_df['attendance_numeric'].corr(course_df['score']) if len(course_df) >= 2 else None
        cname = courses_df.loc[courses_df['course_id'] == course_id, 'course_name'].values[0]
        course_corr_list.append({'course_id': course_id, 'course_name': cname, 'Correlation_R': r})

    return {"Global_Correlation_R": global_correlation, "Per_Course_Correlation": pd.DataFrame(course_corr_list)}


def build_global_scatter_figure() -> plt.Figure:
    att_df, grade_df = _get_attendance_grade()
    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=150)
    if att_df.empty or grade_df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=12)
        ax.set_axis_off()
        return fig

    att_df['attendance_numeric'] = att_df['status'].apply(lambda x: 1 if x == 'Present' else 0)
    global_att = att_df.groupby('student_id')['attendance_numeric'].mean().reset_index(name='avg_attendance_rate')
    global_grade = grade_df.groupby('student_id')['score'].mean().reset_index(name='avg_score')
    global_df = pd.merge(global_att, global_grade, on='student_id', how='inner')

    if global_df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=12)
        ax.set_axis_off()
        return fig

    sns.scatterplot(data=global_df, x="avg_attendance_rate", y="avg_score", ax=ax)
    ax.set_title("Global Attendance vs Grades", fontname="Arial")
    ax.set_xlabel("Average Attendance Rate", fontname="Arial")
    ax.set_ylabel("Average Score", fontname="Arial")
    ax.grid(True, alpha=0.3)
    return fig


def build_per_course_correlation_bar_figure() -> plt.Figure:
    results = calculate_attendance_vs_grades(visualize=False)
    per_course_df = results.get("Per_Course_Correlation")
    fig, ax = plt.subplots(figsize=(6.5, 3.5), dpi=150)
    if per_course_df is None or per_course_df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.set_axis_off()
        return fig

    plot_df = per_course_df.dropna(subset=["Correlation_R"]).copy()
    if plot_df.empty:
        ax.text(0.5, 0.5, "No correlation data", ha="center", va="center")
        ax.set_axis_off()
        return fig

    sns.barplot(data=plot_df, x="course_name", y="Correlation_R", ax=ax, color="#4e79a7")
    ax.set_title("Per-Course Correlation (R)", fontname="Arial")
    ax.set_xlabel("Course", fontname="Arial")
    ax.set_ylabel("R", fontname="Arial")
    ax.tick_params(axis='x', rotation=30)
    ax.grid(True, axis='y', alpha=0.3)
    return fig


def build_per_course_avg_scatter_figure() -> plt.Figure:
    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=150)
    att_df, grade_df = _get_attendance_grade()
    if att_df.empty or grade_df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.set_axis_off()
        return fig

    att_df['attendance_numeric'] = att_df['status'].apply(lambda x: 1 if x == 'Present' else 0)
    conn = db_manager.get_connection()
    enrollment_df = pd.DataFrame(conn.execute("SELECT student_id, course_id FROM Enrollment").fetchall(),
                                 columns=["student_id", "course_id"])  # Courses - Students
    courses_df = pd.DataFrame(conn.execute("SELECT id, name FROM Courses").fetchall(),
                              columns=["course_id", "course_name"])  # Course Name
    conn.close()

    att_df = pd.merge(att_df, enrollment_df, on="student_id", how="inner")
    grade_df = pd.merge(grade_df, enrollment_df, on="student_id", how="inner")

    course_att = att_df.groupby("course_id")["attendance_numeric"].mean().reset_index(name="course_avg_att")
    course_grade = grade_df.groupby("course_id")["score"].mean().reset_index(name="course_avg_score")
    course_df = pd.merge(course_att, course_grade, on="course_id", how="inner")
    course_df = pd.merge(course_df, courses_df, on="course_id", how="left")

    if course_df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.set_axis_off()
        return fig

    sns.scatterplot(data=course_df, x="course_avg_att", y="course_avg_score", ax=ax)
    for _, r in course_df.iterrows():
        ax.annotate(str(r.get("course_name", r["course_id"])),
                    (r["course_avg_att"], r["course_avg_score"]),
                    textcoords="offset points", xytext=(4, 4), fontsize=8)
    ax.set_title("Per-Course Avg Attendance vs Avg Score", fontname="Arial")
    ax.set_xlabel("Course Avg Attendance Rate", fontname="Arial")
    ax.set_ylabel("Course Avg Score", fontname="Arial")
    ax.grid(True, alpha=0.3)
    return fig


# ------------------------------
# Stress level histogram (number of students)
# ------------------------------

def build_stress_histogram_figure(recent_only: bool = True) -> plt.Figure:
    """Draw a histogram of student numbers under different stress levels.
    `recent_only=True` means that only the most recent questionnaire record is used for each student in the statistics.
    """
    df = _get_survey_df()
    fig, ax = plt.subplots(figsize=(6.5, 3.5), dpi=150)
    if df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.set_axis_off()
        return fig

    if recent_only:
        # Each student should keep one record for the latest date
        df = df.sort_values(["student_id", "date"]).drop_duplicates("student_id", keep="last")

    # Statistical quantity
    count_df = df.groupby("stress_level")["student_id"].nunique().reset_index(name="count")
    # Adding stress levels 1-5
    all_levels = pd.DataFrame({"stress_level": [1,2,3,4,5]})
    count_df = all_levels.merge(count_df, on="stress_level", how="left").fillna({"count": 0})

    sns.barplot(data=count_df, x="stress_level", y="count", ax=ax, color="#e15759")
    ax.set_title("Students by Stress Level (latest)", fontname="Arial")
    ax.set_xlabel("Stress Level", fontname="Arial")
    ax.set_ylabel("Students Count", fontname="Arial")
    ax.grid(True, axis='y', alpha=0.3)
    return fig


# ------------------------------
# Student Individual Time Series
# ------------------------------

def _get_student_survey_df(student_id: int) -> pd.DataFrame:
    df = _get_survey_df()
    if df.empty:
        return pd.DataFrame(columns=['student_id','date','stress_level','sleep_hours'])
    df = df[df['student_id'] == int(student_id)].sort_values('date')
    return df[['student_id','date','stress_level','sleep_hours']]


ess_col = '#59a14f'

def build_student_stress_timeseries_figure(student_id: int) -> plt.Figure:
    df = _get_student_survey_df(student_id)
    fig, ax = plt.subplots(figsize=(6, 3.2), dpi=150)
    if df.empty:
        ax.text(0.5, 0.5, f"No stress data for {student_id}", ha='center', va='center')
        ax.set_axis_off()
        return fig
    sns.lineplot(data=df, x='date', y='stress_level', marker='o', ax=ax)
    ax.set_title(f"Student {student_id} - Stress Level Over Time", fontname='Arial')
    ax.set_xlabel('Date', fontname='Arial')
    ax.set_ylabel('Stress Level', fontname='Arial')
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    return fig


def build_student_sleep_timeseries_figure(student_id: int) -> plt.Figure:
    df = _get_student_survey_df(student_id)
    fig, ax = plt.subplots(figsize=(6, 3.2), dpi=150)
    if df.empty:
        ax.text(0.5, 0.5, f"No sleep data for {student_id}", ha='center', va='center')
        ax.set_axis_off()
        return fig
    sns.lineplot(data=df, x='date', y='sleep_hours', marker='o', ax=ax, color=ess_col)
    ax.set_title(f"Student {student_id} - Sleep Hours Over Time", fontname='Arial')
    ax.set_xlabel('Date', fontname='Arial')
    ax.set_ylabel('Sleep Hours', fontname='Arial')
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    return fig
