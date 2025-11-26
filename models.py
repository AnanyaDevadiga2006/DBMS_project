from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# -------------------------------
# STUDENT TABLE
# -------------------------------
class Student(db.Model):
    __tablename__ = "student"

    student_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_name = db.Column(db.String, nullable=False)
    usn = db.Column(db.String, unique=True, nullable=False)
    sem = db.Column(db.Integer)
    section = db.Column(db.String)


# -------------------------------
# TEACHER TABLE
# -------------------------------
class Teacher(db.Model):
    __tablename__ = "teacher"

    teacher_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    teacher_name = db.Column(db.String, nullable=False)
    course_code = db.Column(db.String, nullable=False)
    credit = db.Column(db.Integer)


# -------------------------------
# MARKS TABLE
# -------------------------------
class Marks(db.Model):
    __tablename__ = "marks"

    mark_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student.student_id", ondelete="CASCADE"),
        nullable=False
    )

    course_code = db.Column(db.String, nullable=False)

    ia1 = db.Column(db.Integer, default=0)
    ia2 = db.Column(db.Integer, default=0)
    ia3 = db.Column(db.Integer, default=0)
    assignment = db.Column(db.Integer, default=0)

    # These will be filled by SQLite triggers
    total_score = db.Column(db.Integer)
    category = db.Column(db.String)


# -------------------------------
# SUPPLEMENTARY TABLE
# -------------------------------
class Supplementary(db.Model):
    __tablename__ = "supplementary"

    supp_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student.student_id", ondelete="CASCADE"),
        nullable=False
    )

    course_code = db.Column(db.String, nullable=False)

    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("teacher.teacher_id", ondelete="CASCADE")
    )

    reason = db.Column(db.String)
