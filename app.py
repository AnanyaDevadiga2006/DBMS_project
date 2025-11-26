# app.py — Final version (Flask 3.x + SQLAlchemy + SQLite triggers)
from flask import Flask, render_template, request, redirect, url_for, abort
from models import db, Student, Teacher, Marks, Supplementary
from sqlalchemy import and_
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dpms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


# ---- Initialize DB and apply triggers.sql if present ----
with app.app_context():
    # create tables
    db.create_all()

    # if triggers.sql exists, execute it once (safe to re-run CREATE TRIGGER; if triggers exist you'll get an error)
    # so we try/except to ignore "already exists" errors but still surface others.
    trig_path = os.path.join(os.path.dirname(__file__), "triggers.sql")
    if os.path.exists(trig_path):
        sql = open(trig_path, "r", encoding="utf-8").read()
        try:
            db.session.execute(sql)
            db.session.commit()
        except Exception as e:
            # Likely triggers already exist or minor issue — print for debugging but continue
            # You can remove the print in production; it's useful for local debugging.
            print("Warning while applying triggers (may already exist):", e)
            db.session.rollback()


# ---------------------------
# HOME
# ---------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------
# STUDENT: pages + action
# ---------------------------
@app.route("/add-student-page")
def add_student_page():
    return render_template("add_student.html")


@app.route("/add-student", methods=["POST"])
def add_student():
    data = request.form
    name = data.get("name")
    usn = data.get("usn")
    sem = data.get("sem")
    section = data.get("section")

    if not name or not usn:
        abort(400, "Name and USN are required")

    try:
        sem_val = int(sem) if sem not in (None, "") else None
    except ValueError:
        abort(400, "Semester must be an integer")

    s = Student(student_name=name, usn=usn, sem=sem_val, section=section)
    db.session.add(s)
    db.session.commit()
    return redirect(url_for("index"))


# ---------------------------
# TEACHER: pages + action
# ---------------------------
@app.route("/add-teacher-page")
def add_teacher_page():
    return render_template("add_teacher.html")


@app.route("/add-teacher", methods=["POST"])
def add_teacher():
    data = request.form
    name = data.get("name")
    course = data.get("course")
    credit = data.get("credit")

    if not name or not course:
        abort(400, "Teacher name and course code are required")

    try:
        credit_val = int(credit) if credit not in (None, "") else None
    except ValueError:
        abort(400, "Credit must be an integer")

    t = Teacher(teacher_name=name, course_code=course, credit=credit_val)
    db.session.add(t)
    db.session.commit()
    return redirect(url_for("index"))


# ---------------------------
# MARKS: pages + action
# ---------------------------
@app.route("/add-marks-page")
def add_marks_page():
    # Provide students and teachers for dropdowns (prevents null student_id)
    students = Student.query.order_by(Student.student_name).all()
    teachers = Teacher.query.order_by(Teacher.course_code).all()
    return render_template("add_marks.html", students=students, teachers=teachers)

@app.route('/add-marks', methods=['POST'])
def add_marks():
    data = request.form
    usn = data.get("usn")

    # Find student by USN
    student = Student.query.filter_by(usn=usn).first()

    if not student:
        return "Error: USN not found in database", 400

    # Create marks record using student_id from DB
    m = Marks(
        student_id=student.student_id,
        course_code=data.get("course"),
        ia1=data.get("ia1"),
        ia2=data.get("ia2"),
        ia3=data.get("ia3"),
        assignment=data.get("assignment")
    )

    db.session.add(m)
    db.session.commit()

    return redirect('/monitor')



# ---------------------------
# MONITOR page
# ---------------------------
@app.route("/monitor")
def monitor():
    # Build a result that shows: student, usn, course, total_score, category, supplementary teacher (if any)
    # We use left/outer joins so students without marks still appear (if desired).
    rows = db.session.query(
        Student.student_name,
        Student.usn,
        Marks.course_code,
        Marks.total_score,
        Marks.category,
        Teacher.teacher_name.label("supp_teacher")
    ).join(
        Marks, Student.student_id == Marks.student_id, isouter=True
    ).join(
        Supplementary,
        and_(Supplementary.student_id == Student.student_id,
             Supplementary.course_code == Marks.course_code),
        isouter=True
    ).join(
        Teacher,
        Teacher.teacher_id == Supplementary.teacher_id,
        isouter=True
    ).all()

    return render_template("monitor.html", rows=rows)


# ---------------------------
# Helper: simple health check
# ---------------------------
@app.route("/health")
def health():
    return {"status": "ok"}


# ---------------------------
# START APP
# ---------------------------
if __name__ == "__main__":
    # Run in debug for development; remove debug=True for production
    app.run(debug=True)
