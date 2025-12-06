"""
FILE: app/dashboard.py
DESCRIPTION:
    The main entry point for the treSamlit web application. 
    It creates the user interface (UI) and visualises the data.

TEAM TASKS:
    1. Create a Sidebar Menu to switch between:
       - 'Student Entry' (Forms for input).
       - 'Wellbeing Dashboard' (For the Officer).
       - 'Course Director Analytics' (For the Director).
    2. Use st.form() to collect input and call 'database_manager' to save it.
    3. Use st.line_chart() or st.scatter_chart() to display data from 'analytics.py'.

"""
# -*- coding: utf-8 -*-

import os
import sys
import io
import base64
from datetime import date
from functools import wraps

# 确保无图形界面环境下也能绘图（服务器/命令行）
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, session

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
except ImportError:
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

    # 用于 flash 消息 == For flash messages
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    # 确保 JSON 中文不转义 == Ensure that the JSON content is not escaped.
    app.config["JSON_AS_ASCII"] = False
    
    # =====================================================
    # 权限检查装饰器 == Permission Check Decorators
    # =====================================================
    
    def login_required(f):
        """检查用户是否已登陆 == Check if user is logged in"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please log in first.", "warning")
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    
    def roles_required(*role_codes):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if 'user_id' not in session:
                    flash("Please log in first.", "warning")
                    return redirect(url_for('login'))
                if session.get('role_code') not in role_codes:
                    flash("You do not have the permission to access this page.", "danger")
                    return redirect(url_for('index'))
                return f(*args, **kwargs)
            return decorated_function
        return decorator

    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    # 所有文本响应强制 UTF-8 == All text responses are mandatory in UTF-8 format.
    @app.after_request
    def _force_utf8(response):
        ctype = response.headers.get("Content-Type", "")
        if "text/" in ctype and "charset" not in ctype:
            response.headers["Content-Type"] = f"{ctype}; charset=utf-8"
        return response

    db = DatabaseManager()

    # -----------------------------
    # 绘制学生出席表函数 == Tool: build_global_attendance_grade DataFrame（for plot）
    # -----------------------------
    def _build_global_attendance_grade_df():
        att_data, grade_data = db.get_analytics_data()
        att_df = pd.DataFrame(att_data)
        grade_df = pd.DataFrame(grade_data)
        if att_df.empty or grade_df.empty:
            return pd.DataFrame(columns=["avg_attendance_rate", "avg_score"])
        att_df["attendance_numeric"] = att_df["status"].apply(lambda x: 1 if x == "Present" else 0)
        global_att = att_df.groupby("student_id")["attendance_numeric"].mean().reset_index(name="avg_attendance_rate")
        global_grade = grade_df.groupby("student_id")["score"].mean().reset_index(name="avg_score")
        global_df = pd.merge(global_att, global_grade, on="student_id", how="inner")
        return global_df

    def _get_survey_df():
        data = db.get_raw_survey_data()
        df = pd.DataFrame(data)
        if df.empty:
            return pd.DataFrame(columns=["student_id", "stress_level", "sleep_hours", "date", "Is_At_Risk"])
        df["Is_At_Risk"] = df["stress_level"] >= 4
        return df

    # =====================================================
    # 路由：登陆与认证 == Route: Login & Authentication
    # =====================================================
    
    @app.route("/login", methods=["GET", "POST"])
    def login():
        """登陆页面和验证逻辑 == Login page and verification logic"""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            
            if not username or not password:
                flash("The username and password cannot be left blank.", "danger")
                return redirect(url_for("login"))
            
            # 验证用户凭证 == Verify user credentials
            user = db.verify_login(username, password)
            if user:
                # 将用户信息存储在 session 中 == Store user information in the session.
                session['user_id'] = user.id
                session['username'] = user.username
                session['role_id'] = user.role_id
                session['role_name'] = user.role_name
                # 规范化角色代码，避免因角色名微调导致判断失效
                # Standardize the role codes to prevent the failure of judgment
                # due to minor adjustments in role names.
                rn = (user.role_name or '').lower()
                if 'wellbeing' in rn:
                    session['role_code'] = 'wellbeing'
                elif 'director' in rn:
                    session['role_code'] = 'director'
                else:
                    session['role_code'] = 'unknown'
                flash(f"Welcome! {user.username}！", "success")
                return redirect(url_for("index"))
            else:
                flash("Username or password is incorrect.", "danger")
                return redirect(url_for("login"))
        
        # GET 请求：检查是否已登陆，如果已登陆则重定向到首页 ==
        # GET request: Check if the user is logged in.
        # If so, redirect to the home page.
        if 'user_id' in session:
            return redirect(url_for("index"))
        
        return render_template("login.html")
    
    @app.route("/logout")
    def logout():
        """登出 == Logout"""
        session.clear()
        flash("Logged out", "success")
        return redirect(url_for("login"))
    
    @app.route("/register", methods=["GET", "POST"])
    def register():
        """注册页面和验证逻辑 == Register page and verification logic"""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            confirm_password = request.form.get("confirm_password", "").strip()
            role_code = request.form.get("role_code", "").strip()
            
            # 验证输入
            if not username or not password or not confirm_password or not role_code:
                flash("All fields are mandatory.", "danger")
                return redirect(url_for("register"))
            
            if password != confirm_password:
                flash("The two entered passwords are not the same.", "danger")
                return redirect(url_for("register"))
            
            # 将 role_code 映射为数据库中的 role_id
            role_id = db.get_role_id_by_code(role_code)
            if role_id is None:
                flash("Invalid role selection", "danger")
                return redirect(url_for("register"))
            
            # 注册用户 == Registered user
            success, msg = db.register_user(username, password, role_id)
            if success:
                flash(msg, "success")
                flash("Please log in using the new account.", "info")
                return redirect(url_for("login"))
            else:
                flash(msg, "danger")
                return redirect(url_for("register"))
        
        # GET
        if 'user_id' in session:
            return redirect(url_for("index"))
        
        return render_template("register.html")

    # -----------------------------
    # 路由：主页 == Route: Home Page & Index
    # -----------------------------
    @app.route("/")
    @login_required
    def index():
        # 获取当前用户的角色信息
        role_name = session.get('role_name')
        role_code = session.get('role_code')
        return render_template("index.html", role_name=role_name, role_code=role_code)

    # -----------------------------
    # 路由：学生列表（查）== Route: Student List (Select)
    # -----------------------------
    @app.route("/students")
    @login_required
    @roles_required('director')
    def students_list():
        include_inactive = request.args.get("all") == "1"
        students = db.get_all_students(include_inactive=include_inactive)
        # courses_map
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
    # 路由：编辑学生（改）== Route: Edit Students (Modify)
    # -----------------------------
    @app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
    @login_required
    @roles_required('director')
    def students_edit(student_id):
        student = db.get_student(student_id)
        if not student:
            flash("Students do not exist.", "warning")
            return redirect(url_for("students_list"))
        if request.method == "POST":
            new_status = request.form.get("status")
            graduation_date = request.form.get("graduation_date")
            if new_status:
                db.update_student_status(student_id, new_status)
            if graduation_date:
                db.update_student_graduation(student_id, graduation_date)
            flash("Changes saved", "success")
            return redirect(url_for("students_edit", student_id=student_id))
        # GET 渲染 == GET Rendering
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
    # 路由：删除学生（删）== Route: Delete Student (Delete)
    # -----------------------------
    @app.route("/students/<int:student_id>/delete", methods=["POST"])
    @login_required
    @roles_required('director')
    def students_delete(student_id):
        ok, msg = db.delete_student(student_id)
        flash(("Success：" if ok else "Fail：") + msg, "success" if ok else "warning")
        return redirect(url_for("students_list"))

    # -----------------------------
    # 路由：选课管理（增&删）== Route: Course Selection Management (Add & Delete)
    # -----------------------------
    @app.route("/students/<int:student_id>/enroll", methods=["POST"])
    @login_required
    @roles_required('director')
    def students_enroll(student_id):
        course_id = request.form.get("course_id")
        try:
            cid = int(course_id)
        except Exception:
            flash("The course selection was incorrect.", "warning")
            return redirect(url_for("students_edit", student_id=student_id))
        ok, msg = db.enroll_student(student_id, cid)
        flash(("Success：" if ok else "Fail：") + msg, "success" if ok else "warning")
        return redirect(url_for("students_edit", student_id=student_id))

    @app.route("/students/<int:student_id>/unenroll", methods=["POST"])
    @login_required
    @roles_required('director')
    def students_unenroll(student_id):
        course_id = request.form.get("course_id")
        try:
            cid = int(course_id)
        except Exception:
            flash("Parameter is incorrect.", "warning")
            return redirect(url_for("students_edit", student_id=student_id))
        ok, msg = db.remove_enrollment(student_id, cid)
        flash(("Success：" if ok else "Fail：") + msg, "success" if ok else "warning")
        return redirect(url_for("students_edit", student_id=student_id))

    # -----------------------------
    # 路由：学生入学 + 选课 == Route: Student enrollment + Course selection
    # -----------------------------
    @app.route("/students/add", methods=["GET", "POST"])
    @login_required
    @roles_required('director')
    def add_student():
        courses = db.get_all_courses()
        if request.method == "POST":
            try:
                student_id = int(request.form.get("student_id", "").strip())
                course_id = int(request.form.get("course_id"))
                graduation_date = request.form.get("graduation_date") or date.today().isoformat()
            except Exception:
                flash("The input is incorrect. Please check.", "danger")
                return render_template("students_add.html", courses=courses)

            ok, msg = db.add_student(student_id, course_id, graduation_date)
            if ok:
                flash("Students created and successfully enrolled in courses：" + msg, "success")
                return redirect(url_for("add_student"))
            else:
                flash("Operation failed:" + msg, "warning")
        return render_template("students_add.html", courses=courses)

    # -----------------------------
    # 路由：提交健康问卷 == Route: Submit the health questionnaire
    # 仅限健康管理员 == Only for Wellbeing Officer
    # -----------------------------
    @app.route("/wellbeing/survey", methods=["GET", "POST"])
    @login_required
    @roles_required('wellbeing')
    def wellbeing_survey():
        if request.method == "POST":
            try:
                student_id = int(request.form.get("student_id", "").strip())
                stress_level = int(request.form.get("stress_level"))
                sleep_hours = float(request.form.get("sleep_hours"))
            except Exception:
                flash("The input is incorrect. Please check.", "danger")
                return render_template("wellbeing_survey.html")

            passed_date = request.form.get("passed_date") or None
            ok, msg = db.log_survey_response(student_id, stress_level, sleep_hours, passed_date=passed_date)
            flash(("Success：" if ok else "Warning：") + msg, "success" if ok else "warning")
            return redirect(url_for("wellbeing_survey"))
        return render_template("wellbeing_survey.html")

    # -----------------------------
    # 路由：查看高风险学生 == Route: Review high-risk students
    # 仅限健康管理员 == Only for Wellbeing Officer
    # -----------------------------
    @app.route("/wellbeing/at-risk")
    @login_required
    def at_risk():
        # 支持日期筛选。若提供 date=YYYY-MM-DD 则按该日期筛查；否则按每位学生最新一次记录去重 ==
        # Support date filtering. If the parameter ?date=YYYY-MM-DD is provided,
        # the screening will be conducted based on that date;
        # otherwise, the records of each student will be deduplicated based on their latest entry.
        selected_date = request.args.get("date") or None
        if selected_date:
            df = check_at_risk_students(visualize=False, on_date=selected_date, latest_only=False)
        else:
            df = check_at_risk_students(visualize=False, on_date=None, latest_only=True)
        html_table = df.to_html(classes=["table", "table-striped", "table-sm"], index=False, border=0) if not df.empty else None
        count = len(df["student_id"].unique()) if not df.empty else 0
        return render_template("at_risk.html", table_html=html_table, count=count, selected_date=selected_date)

    # -----------------------------
    # 路由：课程主任分析（出勤 vs 成绩）== Route: Course Director Analysis (Attendance vs. Grades)
    # 仅限课程主任 == Only for Course Director
    # -----------------------------
    @app.route("/analytics")
    @login_required
    def analytics_page():
        # 读取可选学生ID参数，用于在同一页面展示个体时序图 ==
        # Read the optional student ID parameter,
        # which is used to display individual timelines on the same page.
        sid = request.args.get("student_id")
        student_id = int(sid) if sid and sid.isdigit() else None
        results = calculate_attendance_vs_grades(visualize=False)
        global_r = results.get("Global_Correlation_R")
        per_course_df = results.get("Per_Course_Correlation")
        table_html = per_course_df.to_html(classes=["table", "table-bordered", "table-sm"], index=False, border=0) if per_course_df is not None and not per_course_df.empty else None
        return render_template("analytics.html", global_r=global_r, table_html=table_html, student_id=student_id)

    # 学生个体时序图（嵌入课程主任分析页面）
    # Student Individual Timeline (Embedded in the Course Director Analysis Page)
    @app.route("/analytics/student/<int:student_id>/stress.png")
    @login_required
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
    @login_required
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

    # 动态生成全局散点图（PNG）== Generate dynamic global scatter plot (PNG)
    @app.route("/analytics/global_plot.png")
    @login_required
    def global_plot():
        fig = build_global_scatter_figure()
        buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        resp = make_response(buf.read())
        resp.headers["Content-Type"] = "image/png"
        return resp

    # 按课程相关性柱状图 == According to the course relevance bar chart
    # (this chart has been deleted as it is no longer needed)
    @app.route("/analytics/per_course_bar.png")
    @login_required
    def per_course_bar():
        fig = build_per_course_correlation_bar_figure()
        buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        resp = make_response(buf.read())
        resp.headers["Content-Type"] = "image/png"
        return resp

    # # (this chart has been deleted as it is no longer needed, too)
    @app.route("/analytics/stress_hist.png")
    @login_required
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

    # 压力分布图 == Pressure distribution map
    @app.route("/wellbeing/stress_distribution.png")
    @login_required
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

    # 按课程的平均出勤 vs 平均成绩（每门课一个点）
    # Based on the average attendance rate of the courses vs. the average grades
    # (one point per course)
    @app.route("/analytics/per_course_avg_scatter.png")
    @login_required
    def per_course_avg_scatter():
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
    # 路由：作业管理 == Route: Assignment Management
    # 仅限课程主任 == Only for Course Director
    # -----------------------------
    @app.route("/assessments", methods=["GET", "POST"])
    @login_required
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
                    raise ValueError("Title is Empty")
                db.add_assessment(title, cid, deadline, max_s)
                flash("The assignment has been created.", "success")
            except Exception as e:
                flash(f"Creation failed：{e}", "warning")
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
    # 路由：成绩/提交管理 == Route: Grades/Submit Management
    # 仅限课程主任 == Only for Course Director
    # -----------------------------
    @app.route("/grades", methods=["GET"])
    @login_required
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
            # 获取作业信息 == Obtain homework information
            a = db.get_assessment(aid)
            if a:
                max_score = a.max_score
                deadline = a.deadline
            # 课程选课学生 == Course selection students
            students = db.get_students_by_course(cid)
            # 该作业已提交记录 == Record of submission of this assignment
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
    @login_required
    def grades_upsert():
        course_id = request.form.get("course_id")
        assessment_id = request.form.get("assessment_id")
        try:
            cid = int(course_id)
            aid = int(assessment_id)
        except Exception:
            flash("Parameter is incorrect.", "warning")
            return redirect(url_for("grades_page"))
        a = db.get_assessment(aid)
        if not a:
            flash("The assignment does not exist.", "warning")
            return redirect(url_for("grades_page", course_id=cid))
        # 遍历课程学生，读取表单中的日期与分数 ==
        # Traverse the students of the course and read the dates and scores in the form.
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
                    raise ValueError("The score is outside the range.")
                db.upsert_submission(aid, s.id, sub_date or None, score_f if score_f is not None else None)
                saved += 1
            except Exception as e:
                flash(f"Student {s.id} Save failed：{e}", "warning")
        flash(f"{saved} records have been saved.", "success")
        return redirect(url_for("grades_page", course_id=cid, assessment_id=aid))

    # -----------------------------
    # 路由：出勤管理 == Route: Attendance Management
    # 仅限课程主任 == Only for Course Director
    # -----------------------------
    @app.route("/attendance", methods=["GET"])
    @login_required
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
    @login_required
    def attendance_save():
        course_id = request.form.get("course_id")
        lecture_date = request.form.get("lecture_date")
        try:
            cid = int(course_id)
        except Exception:
            flash("Parameter is incorrect.", "warning")
            return redirect(url_for("attendance_page"))
        students = db.get_students_by_course(cid)
        saved = 0
        for s in students:
            status = request.form.get(f"status_{s.id}")
            if status in ("Present", "Absent", "Late"):
                db.upsert_attendance(s.id, cid, lecture_date, status)
                saved += 1
        flash(f"{saved} records have been saved.", "success")
        return redirect(url_for("attendance_page", course_id=cid, lecture_date=lecture_date))

    # 健康检查 Health check-up
    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


if __name__ == "__main__":
    app = create_app()
    # host=0.0.0.0 便于本机/局域网访问；use_reloader=False 避免端口被重复绑定 ==
    # host=0.0.0.0 for local machine / local network access;
    # use_reloader=False to prevent the port from being bound repeatedly
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
