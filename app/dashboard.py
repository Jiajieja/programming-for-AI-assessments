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
    
    *Requirement: Provide simple analytics and visualise changes over time[cite: 72, 86].*
"""
# -*- coding: utf-8 -*-

import os
import sys
import io
import base64
from datetime import date

# 确保无图形界面环境下也能绘图（服务器/命令行）
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response

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

    # 用于 flash 消息
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    # 确保 JSON 中文不转义
    app.config["JSON_AS_ASCII"] = False

    # 控制台输出尽量使用 UTF-8，避免 Windows 控制台乱码
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    # 所有文本响应强制 UTF-8
    @app.after_request
    def _force_utf8(response):
        ctype = response.headers.get("Content-Type", "")
        if "text/" in ctype and "charset" not in ctype:
            response.headers["Content-Type"] = f"{ctype}; charset=utf-8"
        return response

    db = DatabaseManager()

    # -----------------------------
    # 工具：构造全局出勤-成绩 DataFrame（绘图用）
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
    # 路由：主页
    # -----------------------------
    @app.route("/")
    def index():
        return render_template("index.html")

    # -----------------------------
    # 路由：学生列表（查）
    # -----------------------------
    @app.route("/students")
    def students_list():
        include_inactive = request.args.get("all") == "1"
        students = db.get_all_students(include_inactive=include_inactive)
        # 课程名称映射
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
    # 路由：编辑学生（改）
    # -----------------------------
    @app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
    def students_edit(student_id):
        student = db.get_student(student_id)
        if not student:
            flash("学生不存在", "warning")
            return redirect(url_for("students_list"))
        if request.method == "POST":
            new_status = request.form.get("status")
            graduation_date = request.form.get("graduation_date")
            if new_status:
                db.update_student_status(student_id, new_status)
            if graduation_date:
                db.update_student_graduation(student_id, graduation_date)
            flash("已保存修改", "success")
            return redirect(url_for("students_edit", student_id=student_id))
        # GET 渲染
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
    # 路由：删除学生（删）
    # -----------------------------
    @app.route("/students/<int:student_id>/delete", methods=["POST"])
    def students_delete(student_id):
        ok, msg = db.delete_student(student_id)
        flash(("成功：" if ok else "失败：") + msg, "success" if ok else "warning")
        return redirect(url_for("students_list"))

    # -----------------------------
    # 路由：选课管理（增删关系）
    # -----------------------------
    @app.route("/students/<int:student_id>/enroll", methods=["POST"])
    def students_enroll(student_id):
        course_id = request.form.get("course_id")
        try:
            cid = int(course_id)
        except Exception:
            flash("课程选择有误", "warning")
            return redirect(url_for("students_edit", student_id=student_id))
        ok, msg = db.enroll_student(student_id, cid)
        flash(("成功：" if ok else "失败：") + msg, "success" if ok else "warning")
        return redirect(url_for("students_edit", student_id=student_id))

    @app.route("/students/<int:student_id>/unenroll", methods=["POST"])
    def students_unenroll(student_id):
        course_id = request.form.get("course_id")
        try:
            cid = int(course_id)
        except Exception:
            flash("参数有误", "warning")
            return redirect(url_for("students_edit", student_id=student_id))
        ok, msg = db.remove_enrollment(student_id, cid)
        flash(("成功：" if ok else "失败：") + msg, "success" if ok else "warning")
        return redirect(url_for("students_edit", student_id=student_id))

    # -----------------------------
    # 路由：学生入学 + 选课
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
                flash("输入有误，请检查。", "danger")
                return render_template("students_add.html", courses=courses)

            ok, msg = db.add_student(student_id, course_id, graduation_date)
            if ok:
                flash("学生创建并成功选课：" + msg, "success")
                return redirect(url_for("add_student"))
            else:
                flash("操作失败：" + msg, "warning")
        return render_template("students_add.html", courses=courses)

    # -----------------------------
    # 路由：提交健康问卷
    # -----------------------------
    @app.route("/wellbeing/survey", methods=["GET", "POST"])
    def wellbeing_survey():
        if request.method == "POST":
            try:
                student_id = int(request.form.get("student_id", "").strip())
                stress_level = int(request.form.get("stress_level"))
                sleep_hours = float(request.form.get("sleep_hours"))
            except Exception:
                flash("输入有误，请检查。", "danger")
                return render_template("wellbeing_survey.html")

            passed_date = request.form.get("passed_date") or None
            ok, msg = db.log_survey_response(student_id, stress_level, sleep_hours, passed_date=passed_date)
            flash(("成功：" if ok else "警告：") + msg, "success" if ok else "warning")
            return redirect(url_for("wellbeing_survey"))
        return render_template("wellbeing_survey.html")

    # -----------------------------
    # 路由：查看高风险学生
    # -----------------------------
    @app.route("/wellbeing/at-risk")
    def at_risk():
        # 支持日期筛选。若提供 ?date=YYYY-MM-DD 则按该日期筛查；否则按每位学生最新一次记录去重
        selected_date = request.args.get("date") or None
        if selected_date:
            df = check_at_risk_students(visualize=False, on_date=selected_date, latest_only=False)
        else:
            df = check_at_risk_students(visualize=False, on_date=None, latest_only=True)
        html_table = df.to_html(classes=["table", "table-striped", "table-sm"], index=False, border=0) if not df.empty else None
        count = len(df["student_id"].unique()) if not df.empty else 0
        return render_template("at_risk.html", table_html=html_table, count=count, selected_date=selected_date)

    # -----------------------------
    # 路由：课程主任分析（出勤 vs 成绩）
    # -----------------------------
    @app.route("/analytics")
    def analytics_page():
        # 读取可选学生ID参数，用于在同一页面展示个体时序图
        sid = request.args.get("student_id")
        student_id = int(sid) if sid and sid.isdigit() else None
        results = calculate_attendance_vs_grades(visualize=False)
        global_r = results.get("Global_Correlation_R")
        per_course_df = results.get("Per_Course_Correlation")
        table_html = per_course_df.to_html(classes=["table", "table-bordered", "table-sm"], index=False, border=0) if per_course_df is not None and not per_course_df.empty else None
        return render_template("analytics.html", global_r=global_r, table_html=table_html, student_id=student_id)

    # 学生个体时序图（仅图片端点，嵌入课程主任分析页面）
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

    # 动态生成全局散点图（PNG）
    @app.route("/analytics/global_plot.png")
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

    # 动态生成：按课程相关性柱状图
    @app.route("/analytics/per_course_bar.png")
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

    # 动态生成：压力水平分布直方图（学生数量）
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

    # 动态生成：压力分布图（健康）
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

    # 动态生成：按课程的平均出勤 vs 平均成绩（每门课一个点）
    @app.route("/analytics/per_course_avg_scatter.png")
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
    # 路由：作业管理
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
                    raise ValueError("标题为空")
                db.add_assessment(title, cid, deadline, max_s)
                flash("作业已创建", "success")
            except Exception as e:
                flash(f"创建失败：{e}", "warning")
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
    # 路由：成绩/提交管理
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
            # 获取作业信息
            a = db.get_assessment(aid)
            if a:
                max_score = a.max_score
                deadline = a.deadline
            # 课程选课学生
            students = db.get_students_by_course(cid)
            # 该作业已提交记录
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
            flash("参数有误", "warning")
            return redirect(url_for("grades_page"))
        a = db.get_assessment(aid)
        if not a:
            flash("作业不存在", "warning")
            return redirect(url_for("grades_page", course_id=cid))
        # 遍历课程学生，读取表单中的日期与分数
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
                    raise ValueError("分数超出范围")
                db.upsert_submission(aid, s.id, sub_date or None, score_f if score_f is not None else None)
                saved += 1
            except Exception as e:
                flash(f"学生 {s.id} 保存失败：{e}", "warning")
        flash(f"已保存 {saved} 条记录", "success")
        return redirect(url_for("grades_page", course_id=cid, assessment_id=aid))

    # -----------------------------
    # 路由：出勤管理
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
            flash("参数有误", "warning")
            return redirect(url_for("attendance_page"))
        students = db.get_students_by_course(cid)
        saved = 0
        for s in students:
            status = request.form.get(f"status_{s.id}")
            if status in ("Present", "Absent", "Late"):
                db.upsert_attendance(s.id, cid, lecture_date, status)
                saved += 1
        flash(f"已保存 {saved} 条出勤记录", "success")
        return redirect(url_for("attendance_page", course_id=cid, lecture_date=lecture_date))

    # 健康检查
    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


# 允许直接 python -m app 运行
if __name__ == "__main__":
    app = create_app()
    # host=0.0.0.0 便于本机/局域网访问；use_reloader=False 避免端口被重复绑定
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
