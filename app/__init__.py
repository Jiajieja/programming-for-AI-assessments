# -*- coding: utf-8 -*-
"""
Flask application entry point (app package)
- It provides a simple front-end interface and back-end routing to form a runnable visual program
- Compatible with macOS/Windows, and will minimize Chinese/English character encoding issues
"""
import os
import sys
import io
import base64
from datetime import date

# Ensure drawing is possible even without a graphical interface (server/command line)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response

# relative import within a package
try:
    from .db_manager import DatabaseManager
    from .analytics import check_at_risk_students
    from .analytic_data import (
        calculate_attendance_vs_grades,
        build_global_scatter_figure,
        build_per_course_correlation_bar_figure,
        build_per_course_avg_scatter_figure,
        build_stress_histogram_figure,
        build_student_stress_timeseries_figure,
        build_student_sleep_timeseries_figure,
    )
except ImportError:  # Allow script-based execution
    from db_manager import DatabaseManager
    from analytics import check_at_risk_students
    from analytic_data import (
        calculate_attendance_vs_grades,
        build_global_scatter_figure,
        build_per_course_correlation_bar_figure,
        build_per_course_avg_scatter_figure,
        build_stress_histogram_figure,
        build_student_stress_timeseries_figure,
        build_student_sleep_timeseries_figure,
    )


def create_app():
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )

    # Used for flash messages
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    # Ensure that Chinese characters in JSON are not escaped
    app.config["JSON_AS_ASCII"] = False

    # Use UTF-8 for console output whenever possible to avoid garbled characters in the Windows console
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    # All text responses must be UTF-8
    @app.after_request
    def _force_utf8(response):
        ctype = response.headers.get("Content-Type", "")
        if "text/" in ctype and "charset" not in ctype:
            response.headers["Content-Type"] = f"{ctype}; charset=utf-8"
        return response

    db = DatabaseManager()

    # -----------------------------
    # Tools: Construct a global attendance-grade DataFrame (for plotting)
    # -----------------------------
    def _build_global_attendance_grade_df():
        att_data, grade_data = db.get_analytics_data()
        att_df = pd.DataFrame(att_data)
        grade_df = pd.DataFrame(grade_data)
        if att_df.empty or grade_df.empty:
            return pd.DataFrame(columns=["avg_attendance_rate", "avg_score"])  # 空表
        att_df["attendance_numeric"] = att_df["status"].apply(lambda x: 1 if x == "Present" else 0)
        global_att = att_df.groupby("student_id")["attendance_numeric"].mean().reset_index(name="avg_attendance_rate")
        global_grade = grade_df.groupby("student_id")["score"].mean().reset_index(name="avg_score")
        global_df = pd.merge(global_att, global_grade, on="student_id", how="inner")
        return global_df

    def _get_survey_df():
        data = db.get_raw_survey_data()
        df = pd.DataFrame(data)
        if df.empty:
            return pd.DataFrame(columns=["student_id", "stress_level", "sleep_hours", "date", "Is_At_Risk"])  # 空表
        df["Is_At_Risk"] = df["stress_level"] >= 4
        return df

    # -----------------------------
    # Routing: Homepage
    # -----------------------------
    @app.route("/")
    def index():
        return render_template("index.html")

    # -----------------------------
    # Routing: Student List (Search)
    # -----------------------------
    @app.route("/students")
    def students_list():
        include_inactive = request.args.get("all") == "1"
        students = db.get_all_students(include_inactive=include_inactive)
        # Course Name Mapping
        student_courses_map = {}
        for s in students:
            courses = db.get_courses_by_student(s.id)
            student_courses_map[s.id] = [c.name for c in courses]
        return render_template(
            "students_list.html",
            students=students,
            include_inactive=include_inactive,
            student_courses_map=student_courses_map,
        )

    # -----------------------------
    # Routing: Edit Student (Modified)
    # -----------------------------
    @app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
    def students_edit(student_id):
        student = db.get_student(student_id)
        if not student:
            flash("The student does not exist.", "warning")
            return redirect(url_for("students_list"))
        if request.method == "POST":
            new_status = request.form.get("status")
            graduation_date = request.form.get("graduation_date")
            if new_status:
                db.update_student_status(student_id, new_status)
            if graduation_date:
                db.update_student_graduation(student_id, graduation_date)
            flash("Edits saved", "success")
            return redirect(url_for("students_edit", student_id=student_id))
        # GET rendering
        enrolled_courses = db.get_courses_by_student(student_id)
        all_courses = db.get_all_courses()
        enrolled_ids = set(c.id for c in enrolled_courses)
        available_courses = [c for c in all_courses if c.id not in enrolled_ids]
        return render_template(
            "students_edit.html",
            student=student,
            enrolled_courses=enrolled_courses,
            available_courses=available_courses,
        )

    # -----------------------------
    # Routing: Delete student (delete)
    # -----------------------------
    @app.route("/students/<int:student_id>/delete", methods=["POST"]) 
    def students_delete(student_id):
        ok, msg = db.delete_student(student_id)
        flash(("success: " if ok else "fail: ") + msg, "success" if ok else "warning")
        return redirect(url_for("students_list"))

    # -----------------------------
    # Routing: Course Selection Management (Add/Delete Relationships)
    # -----------------------------
    @app.route("/students/<int:student_id>/enroll", methods=["POST"]) 
    def students_enroll(student_id):
        course_id = request.form.get("course_id")
        try:
            cid = int(course_id)
        except Exception:
            flash("Wrong course selection", "warning")
            return redirect(url_for("students_edit", student_id=student_id))
        ok, msg = db.enroll_student(student_id, cid)
        flash(("success: " if ok else "fail: ") + msg, "success" if ok else "warning")
        return redirect(url_for("students_edit", student_id=student_id))

    @app.route("/students/<int:student_id>/unenroll", methods=["POST"]) 
    def students_unenroll(student_id):
        course_id = request.form.get("course_id")
        try:
            cid = int(course_id)
        except Exception:
            flash("Incorrect parameters", "warning")
            return redirect(url_for("students_edit", student_id=student_id))
        ok, msg = db.remove_enrollment(student_id, cid)
        flash(("success: " if ok else "fail: ") + msg, "success" if ok else "warning")
        return redirect(url_for("students_edit", student_id=student_id))

    # -----------------------------
    # Routing: Student Enrollment + Course Selection
    # -----------------------------
    @app.route("/students/add", methods=["GET", "POST"])
    def add_student():
        courses = db.get_all_courses()
        if request.method == "POST":
            try:
                student_id = int(request.form.get("student_id", "").strip())
                course_id = int(request.form.get("course_id"))
                graduation_date = request.form.get("graduation_date") or date.today().isoformat()
            except Exception:
                flash("There is an error in the input. Please check.", "danger")
                return render_template("students_add.html", courses=courses)

            ok, msg = db.add_student(student_id, course_id, graduation_date)
            if ok:
                flash("Student creates and successfully selects courses: " + msg, "success")
                return redirect(url_for("add_student"))
            else:
                flash("Operation failed: " + msg, "warning")
        return render_template("students_add.html", courses=courses)

    # -----------------------------
    # Routing: Submit a health questionnaire
    # -----------------------------
    @app.route("/wellbeing/survey", methods=["GET", "POST"])
    def wellbeing_survey():
        if request.method == "POST":
            try:
                student_id = int(request.form.get("student_id", "").strip())
                stress_level = int(request.form.get("stress_level"))
                sleep_hours = float(request.form.get("sleep_hours"))
            except Exception:
                flash("There is an error in the input. Please check.", "danger")
                return render_template("wellbeing_survey.html")

            passed_date = request.form.get("passed_date") or None
            ok, msg = db.log_survey_response(student_id, stress_level, sleep_hours, passed_date=passed_date)
            flash(("success: " if ok else "warn: ") + msg, "success" if ok else "warning")
            return redirect(url_for("wellbeing_survey"))
        return render_template("wellbeing_survey.html")

    # -----------------------------
    # Routing: View high-risk students
    # -----------------------------
    @app.route("/wellbeing/at-risk")
    def at_risk():
        # Date filtering is supported. If ?date=YYYY-MM-DD is provided, 
        # the filter will be based on that date; otherwise, the filter will be based on the most recent record for each student
        selected_date = request.args.get("date") or None
        if selected_date:
            df = check_at_risk_students(visualize=False, on_date=selected_date, latest_only=False)
        else:
            df = check_at_risk_students(visualize=False, on_date=None, latest_only=True)
        html_table = df.to_html(classes=["table", "table-striped", "table-sm"], index=False, border=0) if not df.empty else None
        count = len(df["student_id"].unique()) if not df.empty else 0
        return render_template("at_risk.html", table_html=html_table, count=count, selected_date=selected_date)

    # -----------------------------
    # Routing: Course Director Analysis (Attendance vs. Grades)
    # -----------------------------
    @app.route("/analytics")
    def analytics_page():
        # Read the optional student ID parameter to display individual time series diagrams on the same page
        sid = request.args.get("student_id")
        student_id = int(sid) if sid and sid.isdigit() else None
        results = calculate_attendance_vs_grades(visualize=False)
        global_r = results.get("Global_Correlation_R")
        per_course_df = results.get("Per_Course_Correlation")
        table_html = per_course_df.to_html(classes=["table", "table-bordered", "table-sm"], index=False, border=0) if per_course_df is not None and not per_course_df.empty else None
        return render_template("analytics.html", global_r=global_r, table_html=table_html, student_id=student_id)

    # Individual student time series graph (image endpoints only, embedded in the course director's analysis page)
    @app.route("/analytics/student/<int:student_id>/stress.png")
    def analytics_student_stress(student_id: int):
        fig = build_student_stress_timeseries_figure(student_id)
        buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        resp = make_response(buf.read())
        resp.headers["Content-Type"] = "image/png"
        return resp

    @app.route("/analytics/student/<int:student_id>/sleep.png")
    def analytics_student_sleep(student_id: int):
        fig = build_student_sleep_timeseries_figure(student_id)
        buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        resp = make_response(buf.read())
        resp.headers["Content-Type"] = "image/png"
        return resp

    # Dynamically generate a global scatter plot (PNG)
    @app.route("/analytics/global_plot.png")
    def global_plot():
        # Visualization functions using analytic_data
        fig = build_global_scatter_figure()
        buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        resp = make_response(buf.read())
        resp.headers["Content-Type"] = "image/png"
        return resp

    # Dynamically generated: Bar chart based on course relevance
    @app.route("/analytics/per_course_bar.png")
    def per_course_bar():
        # Visualization functions using analytic_data
        fig = build_per_course_correlation_bar_figure()
        buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        resp = make_response(buf.read())
        resp.headers["Content-Type"] = "image/png"
        return resp

    # Dynamically generated: Histogram of stress level distribution (number of students)
    @app.route("/analytics/stress_hist.png")
    def stress_hist():
        fig = build_stress_histogram_figure(recent_only=True)
        buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        resp = make_response(buf.read())
        resp.headers["Content-Type"] = "image/png"
        return resp

    # Dynamically generated: Pressure distribution map (health)
    @app.route("/wellbeing/stress_distribution.png")
    def stress_distribution():
        df = _get_survey_df()
        fig, ax = plt.subplots(figsize=(5.5, 3.5), dpi=150)
        if not df.empty:
            sns.countplot(data=df, x="stress_level", hue="Is_At_Risk", palette="Reds", ax=ax)
            ax.set_title("Stress Level Distribution (Red = At Risk)", fontname="Arial")
            ax.set_xlabel("Stress Level", fontname="Arial")
            ax.set_ylabel("Count", fontname="Arial")
            ax.legend(title="At Risk")
        else:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
            ax.set_axis_off()
        buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        resp = make_response(buf.read())
        resp.headers["Content-Type"] = "image/png"
        return resp

    # Dynamically generated: Average attendance vs. average grade (one point per course)
    @app.route("/analytics/per_course_avg_scatter.png")
    def per_course_avg_scatter():
        # Visualization functions using analytic_data
        fig = build_per_course_avg_scatter_figure()
        buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        resp = make_response(buf.read())
        resp.headers["Content-Type"] = "image/png"
        return resp

    # -----------------------------
    # Routing: Assessment Management
    # -----------------------------
    @app.route("/assessments", methods=["GET", "POST"])
    def assessments_page():
        courses = db.get_all_courses()
        if request.method == "POST":
            title = request.form.get("title")
            course_id = request.form.get("course_id")
            deadline = request.form.get("deadline")
            max_score = request.form.get("max_score")
            try:
                cid = int(course_id)
                max_s = int(max_score)
                if not title:
                    raise ValueError("The title is empty.")
                db.add_assessment(title, cid, deadline, max_s)
                flash("The assessment has been created.", "success")
            except Exception as e:
                flash(f"Creation failed: {e}", "warning")
            return redirect(url_for("assessments_page", course_id=course_id))
        # GET
        course_id = request.args.get("course_id")
        assessments = []
        try:
            cid = int(course_id) if course_id else None
            if cid:
                assessments = db.get_assessments_by_course(cid)
        except Exception:
            cid = None
        return render_template("assessments.html", courses=courses, course_id=cid, assessments=assessments)

    # -----------------------------
    # Routing: Grade/Submission Management
    # -----------------------------
    @app.route("/grades", methods=["GET"])
    def grades_page():
        courses = db.get_all_courses()
        course_id = request.args.get("course_id")
        assessment_id = request.args.get("assessment_id")
        assessments = []
        grade_rows = []
        max_score = None
        deadline = None
        try:
            cid = int(course_id) if course_id else None
        except Exception:
            cid = None
        try:
            aid = int(assessment_id) if assessment_id else None
        except Exception:
            aid = None
        if cid:
            assessments = db.get_assessments_by_course(cid)
        if cid and aid:
            # Get assessment information
            a = db.get_assessment(aid)
            if a:
                max_score = a.max_score
                deadline = a.deadline
            # Course selection students (filtering students by course)
            students = db.get_students_by_course(cid)
            # This assignment has been submitted
            subs = {row['student_id']: row for row in db.get_submissions_by_assessment(aid)}
            for s in students:
                row = subs.get(s.id, {})
                grade_rows.append({
                    'student_id': s.id,
                    'submission_date': row.get('submission_date'),
                    'score': row.get('score'),
                })
        return render_template("grades.html",
                               courses=courses,
                               course_id=cid,
                               assessments=assessments,
                               assessment_id=aid,
                               grade_rows=grade_rows,
                               max_score=max_score,
                               deadline=deadline)

    @app.route("/grades/upsert", methods=["POST"])
    def grades_upsert():
        course_id = request.form.get("course_id")
        assessment_id = request.form.get("assessment_id")
        try:
            cid = int(course_id)
            aid = int(assessment_id)
        except Exception:
            flash("Incorrect parameters", "warning")
            return redirect(url_for("grades_page"))
        a = db.get_assessment(aid)
        if not a:
            flash("The assignment does not exist", "warning")
            return redirect(url_for("grades_page", course_id=cid))
        # Iterate through the students in the course and read the dates and scores from the form
        students = db.get_students_by_course(cid)
        saved = 0
        for s in students:
            sub_date = request.form.get(f"submission_date_{s.id}")
            score_val = request.form.get(f"score_{s.id}")
            if (sub_date is None or sub_date == "") and (score_val is None or score_val == ""):
                continue
            try:
                score_f = float(score_val) if score_val not in (None, "") else None
                if score_f is not None and (score_f < 0 or (a.max_score is not None and score_f > a.max_score)):
                    raise ValueError("Score out of range")
                db.upsert_submission(aid, s.id, sub_date or None, score_f if score_f is not None else None)
                saved += 1
            except Exception as e:
                flash(f"Student {s.id} failed to save：{e}", "warning")
        flash(f"{saved} records have been saved", "success")
        return redirect(url_for("grades_page", course_id=cid, assessment_id=aid))

    # -----------------------------
    # Routing: Attendance Management
    # -----------------------------
    @app.route("/attendance", methods=["GET"])
    def attendance_page():
        courses = db.get_all_courses()
        course_id = request.args.get("course_id")
        lecture_date = request.args.get("lecture_date")
        try:
            cid = int(course_id) if course_id else None
        except Exception:
            cid = None
        students = db.get_students_by_course(cid) if cid else []
        current_status = {}
        if cid and lecture_date:
            current_status = db.get_attendance_by_course_and_date(cid, lecture_date)
        return render_template("attendance.html",
                               courses=courses,
                               course_id=cid,
                               lecture_date=lecture_date,
                               students=students,
                               current_status=current_status)

    @app.route("/attendance/save", methods=["POST"])
    def attendance_save():
        course_id = request.form.get("course_id")
        lecture_date = request.form.get("lecture_date")
        try:
            cid = int(course_id)
        except Exception:
            flash("Incorrect parameters", "warning")
            return redirect(url_for("attendance_page"))
        students = db.get_students_by_course(cid)
        saved = 0
        for s in students:
            status = request.form.get(f"status_{s.id}")
            if status in ("Present", "Absent", "Late"):
                db.upsert_attendance(s.id, cid, lecture_date, status)
                saved += 1
        flash(f"{saved} attendance records have been saved", "success")
        return redirect(url_for("attendance_page", course_id=cid, lecture_date=lecture_date))

    # Health check
    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


# Allows direct execution via python -m app
if __name__ == "__main__":
    app = create_app()
    # host=0.0.0.0 Easy access from local machine/LAN；use_reloader=False Avoid port being bound repeatedly
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
