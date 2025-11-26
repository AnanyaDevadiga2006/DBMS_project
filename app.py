# app.py — Flask 3.x + SQLAlchemy + SQLite triggers + Teacher login

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    abort,
    session,
    flash,
)
from models import db, Student, Teacher, Marks, Supplementary
from sqlalchemy import and_, or_, func, text
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dpms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'change-this-to-something-random'  # for sessions
db.init_app(app)


# ---- Initialize DB and apply triggers.sql if present ----
with app.app_context():
    db.create_all()

    trig_path = os.path.join(os.path.dirname(__file__), "triggers.sql")
    if os.path.exists(trig_path):
        with open(trig_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        # Split on ";" and execute each non-empty statement
        for stmt in sql_script.split(";"):
            stmt = stmt.strip()
            if not stmt:
                continue  # skip empty chunks

            try:
                db.session.execute(text(stmt))
            except Exception as e:
                # For debugging; in production you might want to log this
                print("Warning while applying trigger statement:", e)

        db.session.commit()


# ---------------------------
# HOME
# ---------------------------
@app.route("/")
def index():
    if not session.get("teacher_name"):
        return redirect(url_for("login"))  # force login
    return render_template("index.html", teacher_name=session.get("teacher_name"))


@app.route("/home")
def home():
    # just redirect /home -> /
    return redirect(url_for("index"))


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

    # one teacher can appear multiple times with different course_code
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
# TEACHER LOGIN (no password)
# ---------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    # already logged in? straight to home
    if session.get("teacher_name"):
        return redirect(url_for("index"))

    if request.method == "POST":
        raw_name = request.form.get("teacher_name", "")
        teacher_name = raw_name.strip()

        if not teacher_name:
            flash("Please enter your name.", "error")
            return redirect(url_for("login"))

        # Case-insensitive + trimmed match against DB
        teacher = Teacher.query.filter(
            func.lower(func.trim(Teacher.teacher_name)) == teacher_name.lower()
        ).first()

        if not teacher:
            flash("Teacher not found. Check spelling.", "error")
            # Debug in console
            all_teachers = [t.teacher_name for t in Teacher.query.all()]
            print("DEBUG: Teacher not found for input:", repr(teacher_name))
            print("DEBUG: Existing teachers:", all_teachers)
            return redirect(url_for("login"))

        # save NORMALIZED name in session (exact from DB)
        session["teacher_name"] = teacher.teacher_name
        return redirect(url_for("index"))

    # GET: simple typed login page (template does not need teacher_names)
    return render_template("login.html")


@app.route("/red-report")
def red_report():
    # Require login: only logged-in teachers can see this
    teacher_name = session.get("teacher_name")
    if not teacher_name:
        return redirect(url_for("login"))

    # Find all courses this teacher handles
    teacher_rows = Teacher.query.filter_by(teacher_name=teacher_name).all()
    if not teacher_rows:
        # no courses for this teacher -> empty report
        summary = []
        details = []
        return render_template(
            "red_report.html",
            summary=summary,
            details=details,
            teacher_name=teacher_name
        )

    course_codes = [t.course_code for t in teacher_rows]
    lower_course_codes = [c.lower() for c in course_codes]


    # SUMMARY: how many red-band students per course (for this teacher)
    summary_query = db.session.query(
        Marks.course_code,
        func.count(Marks.mark_id).label("red_count")
    ).filter(
        Marks.category == "red",
        func.lower(Marks.course_code).in_(lower_course_codes)
    ).group_by(
        Marks.course_code
    )

    summary = summary_query.all()

    # DETAILS: which students are red in which course
    # make all course codes lowercase once
    
    details_query = db.session.query(
        Student.student_name,
        Student.usn,
        Marks.course_code,
        Marks.total_score
    ).join(
        Marks, Student.student_id == Marks.student_id
    ).filter(
        Marks.category == "red",
        func.lower(Marks.course_code).in_(lower_course_codes)
    ).order_by(
        Marks.course_code,
        Student.student_name
    )


    details = details_query.all()

    return render_template(
        "red_report.html",
        summary=summary,
        details=details,
        teacher_name=teacher_name
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------
# MONITOR page (dashboard)
# ---------------------------
@app.route("/monitor")
def monitor():
    # if a teacher is logged in, restrict view
    teacher_name = session.get("teacher_name")

    # base query: students + marks + supplementary teacher name
    base_query = db.session.query(
        Student.student_name,
        Student.usn,
        Marks.course_code,
        Marks.total_score,
        Marks.category,
        Teacher.teacher_name.label("supp_teacher_name")
    ).join(
        Marks, Student.student_id == Marks.student_id, isouter=True
    ).join(
        Supplementary,
        and_(
            Supplementary.student_id == Student.student_id,
            Supplementary.course_code == Marks.course_code
        ),
        isouter=True
    ).join(
        Teacher,
        Teacher.teacher_id == Supplementary.teacher_id,
        isouter=True
    )

    if teacher_name:
        # all teacher rows (courses) for this name
        teacher_rows = Teacher.query.filter_by(teacher_name=teacher_name).all()

        if not teacher_rows:
            rows = []
        else:
            course_codes = [t.course_code for t in teacher_rows]
            teacher_ids = [t.teacher_id for t in teacher_rows]

            # show:
            # - marks in courses this teacher teaches
            # OR
            # - students where this teacher is the supplementary teacher
            rows = base_query.filter(
                or_(
                    Marks.course_code.in_(course_codes),
                    Supplementary.teacher_id.in_(teacher_ids)
                )
            ).all()
    else:
        # admin view: show everything
        rows = base_query.all()

    return render_template("monitor.html", rows=rows, teacher_name=teacher_name)


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
