from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash
)
from models import db, Student, Teacher, Course, Teaches, Marks, Supplementary
from sqlalchemy import func

# ---------------------------------------------------
# APP + DB SETUP
# ---------------------------------------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///DPMS.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'

db.init_app(app)

with app.app_context():
    db.create_all()


# ---------------------------------------------------
# LOGIN GUARD
# ---------------------------------------------------
@app.before_request
def require_login():
    # endpoints that are allowed without being logged in
    allowed = {"login", "static"}
    # if you want to allow creating first teacher without login, add:
    # allowed.update({"add_teacher_page", "add_teacher"})
    if request.endpoint not in allowed and not session.get("teacher_name"):
        return redirect("/login")


# ---------------------------------------------------
# LOGIN
# ---------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("teacher_name"):
        return redirect(url_for("index"))

    if request.method == "POST":
        name = (request.form.get("teacher_name") or "").strip()

        teacher = Teacher.query.filter(
            func.lower(Teacher.teacher_name) == name.lower()
        ).first()

        if not teacher:
            flash("Teacher not found", "error")
            return redirect("/login")

        session["teacher_name"] = teacher.teacher_name
        session["tid"] = teacher.tid
        return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------------------------------------------------
# DASHBOARD
# ---------------------------------------------------
@app.route("/")
def index():
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

    return render_template(
        "index.html",
        teacher_name=session.get("teacher_name"),
        total_students=total_students,
        total_teachers=total_teachers,
        avg_score=avg_score,
        supp_count=supp_count,
        band_counts=band_counts
    )


# ---------------------------------------------------
# STUDENTS
# ---------------------------------------------------
@app.route("/students")
def students():
    all_students = Student.query.all()
    return render_template("students.html", students=all_students)


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
    flash("Student added", "success")
    return redirect("/students")


@app.route("/edit-student/<usn>", methods=["GET", "POST"])
def edit_student(usn):
    student = Student.query.get_or_404(usn)

    if request.method == "POST":
        data = request.form
        student.student_name = data.get("name", student.student_name)

        if data.get("sem"):
            student.sem = int(data.get("sem"))
        student.section = data.get("section", student.section)

        db.session.commit()
        flash("Student updated", "success")
        return redirect("/students")

    return render_template("edit_student.html", student=student)


# ---------------------------------------------------
# TEACHERS
# ---------------------------------------------------
@app.route("/teachers")
def teachers():
    all_teachers = Teacher.query.all()
    return render_template("teachers.html", teachers=all_teachers)


@app.route("/add-teacher-page")
def add_teacher_page():
    return render_template("add_teacher.html")


@app.route("/add-teacher", methods=["POST"])
def add_teacher():
    data = request.form

    tid = (data.get("tid") or "").strip()
    name = (data.get("name") or "").strip()

    if not tid or not name:
        flash("Teacher ID and name are required", "error")
        return redirect("/add-teacher-page")

    if Teacher.query.get(tid):
        flash("Teacher ID already exists", "error")
        return redirect("/add-teacher-page")

    t = Teacher(tid=tid, teacher_name=name)
    db.session.add(t)
    db.session.commit()
    flash("Teacher added", "success")
    return redirect("/teachers")


@app.route("/edit-teacher/<tid>", methods=["GET", "POST"])
def edit_teacher(tid):
    teacher = Teacher.query.get_or_404(tid)

    if request.method == "POST":
        data = request.form
        teacher.teacher_name = data.get("name", teacher.teacher_name)
        db.session.commit()
        flash("Teacher updated", "success")
        return redirect("/teachers")

    return render_template("edit_teacher.html", teacher=teacher)


@app.route("/delete-teacher/<tid>", methods=["POST"])
def delete_teacher(tid):
    teacher = Teacher.query.get_or_404(tid)

    # remove teaches mappings first
    Teaches.query.filter_by(tid=tid).delete()
    # supplementary has FK with ON DELETE CASCADE (if defined in schema)
    db.session.delete(teacher)
    db.session.commit()
    flash("Teacher deleted", "success")
    return redirect("/teachers")


# ---------------------------------------------------
# COURSES  (ONLY Course table)
# ---------------------------------------------------
@app.route("/courses")
def courses():
    all_courses = Course.query.all()
    return render_template("courses.html", courses=all_courses)


@app.route("/add-course-page")
def add_course_page():
    return render_template("add_course.html")


@app.route("/add-course", methods=["POST"])
def add_course():
    data = request.form
    course_name = (data.get("course_name") or "").strip()
    course_code = (data.get("course_code") or "").strip()
    credit_raw = data.get("credit")
    sem_raw = data.get("sem")

    if not course_code:
        flash("Course code is required", "error")
        return redirect("/add-course-page")

    try:
        credit = int(credit_raw or 0)
    except ValueError:
        flash("Credit must be a number", "error")
        return redirect("/add-course-page")

    if Course.query.get(course_code):
        flash("Course already exists", "error")
        return redirect("/add-course-page")
    try:
        c = Course(course_code=course_code, credit=credit,course_name=course_name,sem=int(sem_raw or 0))
        db.session.add(c)
        db.session.commit()
    except ValueError:
        flash("Semester must be a number", "error")
        return redirect("/add-course-page")

    flash("Course added successfully", "success")
    return redirect("/courses")


@app.route("/edit-course/<course_code>", methods=["GET", "POST"])
def edit_course(course_code):
    course = Course.query.get_or_404(course_code)

    if request.method == "POST":
        data = request.form
        try:
            course.course_name = data.get("course_name") or course.course_name
            course.sem = int(data.get("sem") or course.sem or 0)
            course.credit = int(data.get("credit") or course.credit or 0)
        except ValueError:
            flash("Credit must be a number", "error")
            return redirect(url_for("edit_course", course_code=course_code))

        db.session.commit()
        flash("Course updated successfully", "success")
        return redirect("/courses")

    return render_template("edit_course.html", course=course)


# ---------------------------------------------------
# TEACHES (Teacher ↔ Course mapping)
# ---------------------------------------------------
@app.route("/assign-course-page")
def assign_course_page():
    teachers = Teacher.query.all()
    courses = Course.query.all()
    return render_template(
        "assign_course.html",
        teachers=teachers,
        courses=courses
    )


@app.route("/assign-course", methods=["POST"])
def assign_course():
    data = request.form
    tid = data.get("tid")
    course_code = data.get("course_code")

    if not tid or not course_code:
        flash("Teacher and course are required", "error")
        return redirect("/assign-course-page")

    # ensure teacher and course exist
    if not Teacher.query.get(tid):
        flash("Selected teacher does not exist", "error")
        return redirect("/assign-course-page")

    if not Course.query.get(course_code):
        flash("Selected course does not exist", "error")
        return redirect("/assign-course-page")

    # avoid duplicate mapping
    if Teaches.query.filter_by(tid=tid, course_code=course_code).first():
        flash("This teacher is already assigned to that course", "error")
        return redirect("/assign-course-page")

    tmap = Teaches(tid=tid, course_code=course_code)
    db.session.add(tmap)
    db.session.commit()
    flash("Course assigned to teacher", "success")
    return redirect("/assign-course-page")


# ---------------------------------------------------
# MARKS
# ---------------------------------------------------
@app.route("/add-marks-page")
def add_marks_page():
    students = Student.query.all()
    courses = Course.query.all()
    return render_template(
        "add_marks.html",
        students=students,
        courses=courses
    )


@app.route("/add-marks", methods=["POST"])
def add_marks():
    data = request.form
    usn = data.get("usn")
    course_code = data.get("course_code") or data.get("course")

    # check student exists
    student = Student.query.filter_by(usn=usn).first()
    if not student:
        flash("USN not found", "error")
        return redirect("/add-marks-page")

    # check course exists
    course = Course.query.filter_by(course_code=course_code).first()
    if not course:
        flash(f"Course code {course_code} not found", "error")
        return redirect("/add-marks-page")

    # prevent duplicate for same (usn, course_code)
    existing = Marks.query.filter_by(usn=usn, course_code=course_code).first()
    if existing:
        flash("Marks already exist for this student + course. Edit instead.", "error")
        return redirect("/monitor")

    m = Marks(
        usn=usn,
        course_code=course_code,
        ia1=int(data.get("ia1") or 0),
        ia2=int(data.get("ia2") or 0),
        ia3=int(data.get("ia3") or 0),
        assignment=int(data.get("assignment") or 0)
    )

    db.session.add(m)
    db.session.commit()  # DB trigger calc_category will set total_score & category
    flash("Marks added", "success")
    return redirect("/monitor")


@app.route("/edit-marks/<usn>/<course_code>", methods=["GET", "POST"])
def edit_marks(usn, course_code):
    marks = Marks.query.filter_by(usn=usn, course_code=course_code).first_or_404()

    if request.method == "POST":
        data = request.form
        marks.ia1 = int(data.get("ia1") or marks.ia1 or 0)
        marks.ia2 = int(data.get("ia2") or marks.ia2 or 0)
        marks.ia3 = int(data.get("ia3") or marks.ia3 or 0)
        marks.assignment = int(data.get("assignment") or marks.assignment or 0)

        # recompute score + category to match trigger logic
        total = ((marks.ia1 + marks.ia2 + marks.ia3) / 3) + marks.assignment
        marks.total_score = total
        if total < 20:
            marks.category = "red"
        elif total < 40:
            marks.category = "yellow"
        else:
            marks.category = "green"

        db.session.commit()
        flash("Marks updated", "success")
        return redirect("/monitor")

    return render_template(
        "edit_marks.html",
        marks=marks
    )


# ---------------------------------------------------
# SUPPLEMENTARY
# ---------------------------------------------------
@app.route("/supplementary")
def supplementary():
    records = (
        db.session.query(
            Student.student_name,
            Student.usn,
            Supplementary.course_code,
            Teacher.teacher_name.label("assigned_teacher")
        )
        .join(Supplementary, Student.usn == Supplementary.usn)
        .join(Teacher, Teacher.tid == Supplementary.teacher_id)
        .order_by(Student.student_name)
        .all()
    )

    return render_template("supplementary.html", records=records)

from sqlalchemy import and_

# ...

@app.route("/add-supplementary-page")
def add_supplementary_page():
    teachers = Teacher.query.all()
    courses = Course.query.all()
    return render_template(
        "add_supplementary.html",
        teachers=teachers,
        courses=courses
    )


@app.route("/add-supplementary", methods=["POST"])
def add_supplementary():
    teacher_id = (request.form.get("teacher_id") or "").strip()
    course_code = (request.form.get("course_code") or "").strip()

    if not teacher_id or not course_code:
        flash("Teacher and course are required", "error")
        return redirect("/add-supplementary-page")

    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        flash("Teacher not found", "error")
        return redirect("/add-supplementary-page")

    course = Course.query.get(course_code)
    if not course:
        flash("Course not found", "error")
        return redirect("/add-supplementary-page")

    # Find all red-band students for that course
    red_rows = (
        db.session.query(Marks.usn)
        .filter(
            and_(
                Marks.course_code == course_code,
                Marks.category == "red"
            )
        )
        .all()
    )

    if not red_rows:
        flash("No red-band students found for this course", "info")
        return redirect("/add-supplementary-page")

    created = 0
    for (usn,) in red_rows:
        exists = Supplementary.query.filter_by(
            usn=usn,
            course_code=course_code,
            teacher_id=teacher_id
        ).first()
        if not exists:
            db.session.add(
                Supplementary(
                    usn=usn,
                    course_code=course_code,
                    teacher_id=teacher_id
                )
            )
            created += 1

    db.session.commit()
    flash(f"Supplementary assigned for {created} student(s).", "success")
    return redirect("/supplementary")
@app.route("/delete-supplementary/<usn>/<course_code>", methods=["POST"])
def delete_supplementary(usn, course_code):
    # delete all supplementary records for that student & course
    Supplementary.query.filter_by(usn=usn, course_code=course_code).delete()
    db.session.commit()
    flash("Supplementary record deleted", "success")
    return redirect("/supplementary")

@app.route("/edit-supplementary/<usn>/<course_code>", methods=["GET", "POST"])
def edit_supplementary(usn, course_code):
    supp = Supplementary.query.filter_by(usn=usn, course_code=course_code).first()

    if not supp:
        flash("No supplementary record for this student & course", "error")
        return redirect("/supplementary")

    if request.method == "POST":
        data = request.form
        teacher_id = (data.get("teacher_id") or "").strip()

        if teacher_id:
            teacher = Teacher.query.get(teacher_id)
            if not teacher:
                flash("Teacher not found", "error")
                return redirect(request.url)
            supp.teacher_id = teacher_id

        db.session.commit()
        flash("Supplementary updated", "success")
        return redirect("/supplementary")

    teachers = Teacher.query.all()
    return render_template(
        "edit_supplementary.html",
        supp=supp,
        teachers=teachers
    )


# ---------------------------------------------------
# MONITOR
# ---------------------------------------------------
@app.route("/monitor")
def monitor():
    filter_usn = request.args.get("usn")

    query = (
        db.session.query(
            Student.student_name,
            Student.usn,
            Marks.course_code,
            Marks.total_score,
            Marks.category,
            Teacher.teacher_name.label("supp_teacher_name")
        )
        .join(Marks, Student.usn == Marks.usn, isouter=True)
        .join(
            Supplementary,
            (Supplementary.usn == Student.usn) &
            (Supplementary.course_code == Marks.course_code),
            isouter=True
        )
        .join(Teacher, Teacher.tid == Supplementary.teacher_id, isouter=True)
    )

    if filter_usn:
        query = query.filter(Student.usn == filter_usn)

    rows = query.all()

    return render_template("monitor.html", rows=rows)


# ---------------------------------------------------
# BAND ANALYSIS
# ---------------------------------------------------
@app.route("/band-analysis")
def band_analysis():
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
