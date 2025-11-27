from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Student(db.Model):
    __tablename__ = "student"

    usn = db.Column(db.String, primary_key=True)
    student_name = db.Column(db.String, nullable=False)
    sem = db.Column(db.Integer)          # you already have CHECK in raw SQL
    section = db.Column(db.String)       # same here


class Teacher(db.Model):
    __tablename__ = "teacher"

    tid = db.Column(db.String, primary_key=True)  # TEXT PK
    teacher_name = db.Column(db.String, nullable=False)


class Course(db.Model):
    __tablename__ = "course"

    course_code = db.Column(db.String, primary_key=True)
    credit = db.Column(db.Integer)


class Teaches(db.Model):
    __tablename__ = "teaches"

    tid = db.Column(
        db.String,
        db.ForeignKey("teacher.tid"),
        primary_key=True,
        nullable=False
    )
    course_code = db.Column(
        db.String,
        db.ForeignKey("course.course_code"),
        primary_key=True,
        nullable=False
    )
    sem = db.Column(db.Integer)
    section = db.Column(db.String)

    teacher = db.relationship("Teacher", backref="courses_taught")
    course = db.relationship("Course", backref="teachers")


class Marks(db.Model):
    __tablename__ = "marks"
    usn = db.Column(db.String, db.ForeignKey("student.usn"), primary_key=True)
    course_code = db.Column(db.String, db.ForeignKey("course.course_code"), primary_key=True)

    ia1 = db.Column(db.Integer, default=0)
    ia2 = db.Column(db.Integer, default=0)
    ia3 = db.Column(db.Integer, default=0)
    assignment = db.Column(db.Integer, default=0)

    total_score = db.Column(db.Integer)
    category = db.Column(db.String)


class Supplementary(db.Model):
    __tablename__ = "supplementary"

    usn = db.Column(
        db.String,
        db.ForeignKey("student.usn", ondelete="CASCADE"),
        primary_key=True
    )
    course_code = db.Column(
        db.String,
        db.ForeignKey("course.course_code", ondelete="CASCADE"),
        primary_key=True
    )
    teacher_id = db.Column(
        db.String,
        db.ForeignKey("teacher.tid", ondelete="CASCADE"),
        primary_key=True
    )

    student = db.relationship("Student", backref="supplementaries")
    course = db.relationship("Course", backref="supplementaries")
    teacher = db.relationship("Teacher", backref="supplementaries")
