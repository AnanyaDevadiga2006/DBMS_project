from flask import (
    Flask, render_template, request, redirect,
    url_for, abort, session, flash
)
from models import db, Student, Teacher, Marks, Supplementary
from sqlalchemy import func, text, and_, or_
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dpms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'
db.init_app(app)


# ---------------------------------------------------
# INITIALIZE DB + TRIGGERS
# ---------------------------------------------------
with app.app_context():
    db.create_all()

    trig_path = os.path.join(os.path.dirname(__file__), "triggers.sql")
    if os.path.exists(trig_path):
        sql = open(trig_path, "r", encoding="utf-8").read()
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                try:
                    db.session.execute(text(stmt))
                except Exception as e:
                    print("Trigger Warning:", e)
        db.session.commit()


# ---------------------------------------------------
# LOGIN
# ---------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("teacher_name"):
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("teacher_name", "").strip()

        teacher = Teacher.query.filter(
            func.lower(Teacher.teacher_name) == name.lower()
        ).first()

        if not teacher:
            flash("Teacher not found", "error")
            return redirect("/login")

        session["teacher_name"] = teacher.teacher_name
        return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------------------------------------------------
# DASHBOARD (Figma-style)
# ---------------------------------------------------
@app.route("/")
def index():
    if not session.get("teacher_name"):
        return redirect("/login")

    total_students = Student.query.count()
    total_teachers = Teacher.query.count()

    avg_score = db.session.query(func.avg(Marks.total_score)).scalar() or 0
    avg_score = round(avg_score, 2)

    band_counts = {
        "green": Marks.query.filter_by(category="green").count(),
        "yellow": Marks.query.filter_by(category="yellow").count(),
        "red": Marks.query.filter_by(category="red").count()
    }

    supp_count = Supplementary.query.count()

    # Teachers per course
    dept_labels = []
    dept_counts = []

    courses = (
        db.session.query(Teacher.course_code, func.count(Teacher.teacher_id))
        .group_by(Teacher.course_code)
        .all()
    )

    for course, count in courses:
        dept_labels.append(course)
        dept_counts.append(count)

    # --- TOP STUDENTS (computed in Python, not in template)
    top_students = (
        db.session.query(Student.student_name, Marks.total_score)
        .join(Marks, Student.student_id == Marks.student_id)
        .order_by(Marks.total_score.desc())
        .limit(3)
        .all()
    )

    # --- AT-RISK (red band) list (name, usn, total_score)
    at_risk = (
        db.session.query(Student.student_name, Student.usn, Marks.total_score)
        .join(Marks, Student.student_id == Marks.student_id)
        .filter(Marks.category == "red")
        .order_by(Marks.total_score.asc())
        .limit(10)
        .all()
    )

    return render_template(
        "index.html",
        teacher_name=session.get("teacher_name"),

        total_students=total_students,
        total_teachers=total_teachers,
        avg_score=avg_score,
        supp_count=supp_count,

        band_counts=band_counts,
        dept_labels=dept_labels,
        dept_counts=dept_counts,

        top_students=top_students,
        at_risk=at_risk
    )


# ---------------------------------------------------
# STUDENTS
# ---------------------------------------------------
@app.route("/students")
def students():
    return render_template("students.html", students=Student.query.all())


@app.route("/add-student-page")
def add_student_page():
    return render_template("add_student.html")


@app.route("/add-student", methods=["POST"])
def add_student():
    data = request.form

    s = Student(
        student_name=data.get("name"),
        usn=data.get("usn"),
        sem=int(data.get("sem") or 0),
        section=data.get("section")
    )

    db.session.add(s)
    db.session.commit()
    return redirect("/students")


# ---------------------------------------------------
# TEACHERS
# ---------------------------------------------------
@app.route("/teachers")
def teachers():
    return render_template("teachers.html", teachers=Teacher.query.all())


@app.route("/add-teacher-page")
def add_teacher_page():
    return render_template("add_teacher.html")


@app.route("/add-teacher", methods=["POST"])
def add_teacher():
    data = request.form
    t = Teacher(
        teacher_name=data.get("name"),
        course_code=data.get("course"),
        credit=int(data.get("credit") or 0)
    )
    db.session.add(t)
    db.session.commit()
    return redirect("/teachers")


# ---------------------------------------------------
# MARKS
# ---------------------------------------------------
@app.route("/add-marks-page")
def add_marks_page():
    return render_template(
        "add_marks.html",
        students=Student.query.all(),
        teachers=Teacher.query.all()
    )


@app.route("/add-marks", methods=["POST"])
def add_marks():
    data = request.form
    usn = data.get("usn")
    student = Student.query.filter_by(usn=usn).first()

    if not student:
        return "USN not found", 400

    m = Marks(
        student_id=student.student_id,
        course_code=data.get("course"),
        ia1=int(data.get("ia1") or 0),
        ia2=int(data.get("ia2") or 0),
        ia3=int(data.get("ia3") or 0),
        assignment=int(data.get("assignment") or 0)
    )

    db.session.add(m)
    db.session.commit()
    return redirect("/monitor")


@app.route("/supplementary")
def supplementary():
    records = (
        db.session.query(
            Student.student_name,
            Student.usn,
            Supplementary.course_code,
            Teacher.teacher_name.label("assigned_teacher")
        )
        .join(Supplementary, Student.student_id == Supplementary.student_id)
        .join(Teacher, Teacher.teacher_id == Supplementary.teacher_id)
        .order_by(Student.student_name)
        .all()
    )

    return render_template("supplementary.html", records=records)

# ---------------------------------------------------
# MONITOR
# ---------------------------------------------------
@app.route("/monitor")
def monitor():
    rows = (
        db.session.query(
            Student.student_name,
            Student.usn,
            Marks.course_code,
            Marks.total_score,
            Marks.category,
            Teacher.teacher_name.label("supp_teacher_name")
        )
        .join(Marks, Student.student_id == Marks.student_id, isouter=True)
        .join(
            Supplementary,
            (Supplementary.student_id == Student.student_id) &
            (Supplementary.course_code == Marks.course_code),
            isouter=True
        )
        .join(Teacher, Teacher.teacher_id == Supplementary.teacher_id, isouter=True)
        .all()
    )

    return render_template("monitor.html", rows=rows)

@app.route("/band-analysis")
def band_analysis():
    # Calculate band counts
    green = Marks.query.filter_by(category="green").count()
    yellow = Marks.query.filter_by(category="yellow").count()
    red = Marks.query.filter_by(category="red").count()

    labels = ["Green", "Yellow", "Red"]
    data = [green, yellow, red]

    return render_template(
        "band_analysis.html",
        labels=labels,
        data=data
    )

# ---------------------------------------------------
# START SERVER
# ---------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
