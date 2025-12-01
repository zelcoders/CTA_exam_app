from datetime import datetime
import random
import pandas as pd
import re

from flask import Flask, render_template, redirect, url_for, request, flash, abort, send_from_directory
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Float, Text
from werkzeug.security import generate_password_hash, check_password_hash

from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required

from forms import LoginForm, RegisterForm, CoursesForm, ExamQuestionsForm, ResetStudentScoreForm, GcreeForm, \
    TerminalExamForm
from smtplib import SMTP_SSL
import os
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')
# os.environ("", "")
zelcoders_password = os.environ.get('ZEL_PASS')
Bootstrap5(app)


login_manager = LoginManager()
login_manager.init_app(app=app)

this_year = datetime.today().year


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(ZelUser, user_id)

# CREATE DB
class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///exam.db")
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# Create an admin-only decorator
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Your session has timed out. Kindly re-enter your details to login!")
            return redirect(url_for("cta_home"))
        elif current_user.user_type != "Admin":
            flash("You are not authorized to access this page. Kindly re-enter your details to login!")
            return redirect(url_for("cta_home"))
        # Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function


def sosiec_admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Your session has timed out. Kindly re-enter your details to login!")
            return redirect(url_for("sosiec_home"))
        elif current_user.user_type != "Admin" or current_user.user_type != "SOS - Admin":
            flash("You are not authorized to access this page. Kindly re-enter your details to login!")
            return redirect(url_for("sosiec_home"))
        # Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function


def instructor_only(f):
    @wraps(f)
    def new_decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Your session has timed out. Kindly re-enter your details to login!")
            return redirect(url_for("cta_home"))
        elif current_user.user_type != "Admin":
            if current_user.user_type != "Instructor":
                flash("You are not authorized to access this page. Kindly re-enter your details to login!")
                return redirect(url_for("cta_home"))
        # Otherwise continue with the route function
        return f(*args, **kwargs)
    return new_decorated_function


def my_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Your session has timed out. Kindly re-enter your details to login!")
            return redirect(url_for("cta_home"))
        return f(*args, **kwargs)
    return decorated_function


def get_current_session():
    load_records = db.session.execute(db.select(ZelTermDefine).where(ZelTermDefine.school_id == current_user.school_id)).scalars().all()
    if not load_records:
        return ""
    for rec in load_records:
        start_date = datetime.strptime(rec.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(rec.end_date, '%Y-%m-%d').date()
        today = datetime.now().date()
        if start_date <= today <= end_date:
            current_session = rec.session
            return current_session

    return load_records[-1].session


def get_current_term():
    load_records = db.session.execute(
        db.select(ZelTermDefine).where(ZelTermDefine.school_id == current_user.school_id)).scalars().all()
    if not load_records:
        return ""
    for rec in load_records:
        start_date = datetime.strptime(rec.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(rec.end_date, '%Y-%m-%d').date()
        today = datetime.now().date()
        if start_date <= today <= end_date:
            current_term = rec.term
            return current_term

    return load_records[-1].term


# CREATE TABLE

class User(UserMixin, db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    surname: Mapped[str] = mapped_column(String(50), nullable=False)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    passcode: Mapped[str] = mapped_column(String(500), nullable=False)
    branch: Mapped[str] = mapped_column(String(50), nullable=False)
    user_type: Mapped[str] = mapped_column(String(50), nullable=False)

    results = relationship("Results", back_populates="user")
    course = relationship("Courses", back_populates="instructor")
    score = relationship("Scores", back_populates="user")


class Questions(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question: Mapped[str] = mapped_column(String(1000), nullable=False)
    options: Mapped[str] = mapped_column(String(500), nullable=False)
    correct_option: Mapped[str] = mapped_column(String(500), nullable=False)
    course_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("courses.id"))

    results = relationship("Results", back_populates="question")
    course = relationship("Courses", back_populates="question")


class Courses(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_code: Mapped[str] = mapped_column(String(200), nullable=False)
    course_title: Mapped[str] = mapped_column(String(500), nullable=False)
    course_description: Mapped[str] = mapped_column(String(1000), nullable=True)
    instructor_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("user.id"))

    results = relationship("Results", back_populates="course")
    question = relationship("Questions", back_populates="course")
    instructor = relationship("User", back_populates="course")
    score = relationship("Scores", back_populates="course")


class Results(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("user.id"))
    course_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("courses.id"))
    question_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("questions.id"))
    selected_answer: Mapped[str] = mapped_column(String(1000), nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(1000), nullable=False)

    user = relationship("User", back_populates="results")
    course = relationship("Courses", back_populates="results")
    question = relationship("Questions", back_populates="results")


class ZelObjResults(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), db.ForeignKey("zel_user.id"))
    subject_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("zel_subject.id"))
    question_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("question_pool_obj.id"))
    selected_answer: Mapped[str] = mapped_column(String(1000), nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(1000), nullable=False)
    term: Mapped[str] = mapped_column(String(50), nullable=False)
    session: Mapped[str] = mapped_column(String(50), nullable=False)
    classroom_id: Mapped[int] = mapped_column(Integer, nullable=False)

    user = relationship("ZelUser", back_populates="obj_results")
    subject = relationship("ZelSubject", back_populates="obj_results")
    question = relationship("QuestionPoolObj", back_populates="obj_results")


class Scores(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("user.id"))
    course_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("courses.id"))
    year: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    remark: Mapped[str] = mapped_column(String(50), nullable=False)

    user = relationship("User", back_populates="score")
    course = relationship("Courses", back_populates="score")


class ZelSchool(db.Model):
    __tablename__ = "zel_school"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(1000), nullable=True)
    email: Mapped[str] = mapped_column(String(100), nullable=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    logo: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)

    students = relationship("ZelUser", back_populates="school")
    classrooms = relationship("ZelClassroom", back_populates="school")
    fees = relationship("ZelFees", back_populates="school")
    bank_accounts = relationship("ZelBankAccounts", back_populates="school")
    obj_question = relationship("ZelObjQuestions", back_populates="school")


class ZelTerm(db.Model):
    __tablename__ = "zel_term"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term: Mapped[str] = mapped_column(String(100), nullable=False)
    is_current: Mapped[str] = mapped_column(String(100), nullable=True)


class ZelSession(db.Model):
    __tablename__ = "zel_session"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session: Mapped[str] = mapped_column(String(100), nullable=False)
    is_current: Mapped[str] = mapped_column(String(100), nullable=True)


class ZelUser(UserMixin, db.Model):
    __tablename__ = "zel_user"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    user_type: Mapped[str] = mapped_column(String(100), nullable=False)
    surname: Mapped[str] = mapped_column(String(100), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[str] = mapped_column(String(100), nullable=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(250), nullable=True)
    password_reset: Mapped[str] = mapped_column(String(250), nullable=True)
    date_of_birth: Mapped[str] = mapped_column(String(100), nullable=True)
    sex: Mapped[str] = mapped_column(String(100), nullable=True)
    address: Mapped[str] = mapped_column(String(1000), nullable=True)
    phone: Mapped[str] = mapped_column(String(100), nullable=True)
    religion: Mapped[str] = mapped_column(String(100), nullable=True)
    passport_photo: Mapped[str] = mapped_column(String(100), nullable=True)
    admission_date_or_employment_date: Mapped[str] = mapped_column(String(100), nullable=True)
    next_of_kin1: Mapped[str] = mapped_column(String(100), nullable=True)
    next_of_kin1_contact: Mapped[str] = mapped_column(String(100), nullable=True)
    next_of_kin2: Mapped[str] = mapped_column(String(100), nullable=True)
    next_of_kin2_contact: Mapped[str] = mapped_column(String(100), nullable=True)
    parent_occupation: Mapped[str] = mapped_column(String(100), nullable=True)
    referee1: Mapped[str] = mapped_column(String(100), nullable=True)
    referee1_contact: Mapped[str] = mapped_column(String(100), nullable=True)
    referee2: Mapped[str] = mapped_column(String(100), nullable=True)
    referee2_contact: Mapped[str] = mapped_column(String(100), nullable=True)
    allergy: Mapped[str] = mapped_column(String(250), nullable=True)
    blood_group: Mapped[str] = mapped_column(String(50), nullable=True)
    genotype: Mapped[str] = mapped_column(String(50), nullable=True)
    previous_school_or_previous_employment: Mapped[str] = mapped_column(String(1000), nullable=True)
    talent_or_interest: Mapped[str] = mapped_column(String(250), nullable=True)
    pickup_person: Mapped[str] = mapped_column(String(100), nullable=True)
    school_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("zel_school.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    class_variant: Mapped[str] = mapped_column(String(50), nullable=True)
    classroom_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("zel_classroom.id"), nullable=True)

    school = relationship("ZelSchool", back_populates="students")
    subjects = relationship("ZelUserSubject", back_populates="users")
    posted_by = relationship("ZelPayment", back_populates="posted_by")
    results = relationship("ZelResult", back_populates="student")
    class_teacher = relationship("ZelAttendance", back_populates="teacher")
    log = relationship("ZelLog", back_populates="user")
    classroom = relationship("ZelClassroom", back_populates="user")
    obj_results = relationship("ZelObjResults", back_populates="user")


class ZelClassroom(db.Model):
    __tablename__ = "zel_classroom"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_name: Mapped[str] = mapped_column(String(100), nullable=False)
    section: Mapped[str] = mapped_column(String(100), nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    school_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("zel_school.id"), nullable=True)

    school = relationship("ZelSchool", back_populates="classrooms")
    user = relationship("ZelUser", back_populates="classroom")
    class_subjects = relationship("ZelClassSubjects", back_populates="classroom")


class ZelSubject(db.Model):
    __tablename__ = "zel_subject"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    subject_code: Mapped[str] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)

    obj_question = relationship("ZelObjQuestions", back_populates="subject")
    obj_results = relationship("ZelObjResults", back_populates="subject")


class ZelUserClassroom(db.Model):
    __tablename__ = "zel_user_classroom"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    current_classroom_name: Mapped[int] = mapped_column(Integer, nullable=True)
    classroom2_name: Mapped[int] = mapped_column(Integer, nullable=True)
    classroom3_name: Mapped[int] = mapped_column(Integer, nullable=True)
    classroom4_name: Mapped[int] = mapped_column(Integer, nullable=True)
    classroom5_name: Mapped[int] = mapped_column(Integer, nullable=True)
    classroom6_name: Mapped[int] = mapped_column(Integer, nullable=True)
    classroom7_name: Mapped[int] = mapped_column(Integer, nullable=True)
    classroom8_name: Mapped[int] = mapped_column(Integer, nullable=True)


class ZelUserSubject(db.Model):
    __tablename__ = "zel_user_subject"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), db.ForeignKey("zel_user.id"), nullable=False)
    term: Mapped[str] = mapped_column(String(100), nullable=False)
    session: Mapped[str] = mapped_column(String(100), nullable=False)
    subject_list: Mapped[str] = mapped_column(String(1000), nullable=True)

    users = relationship("ZelUser", back_populates="subjects")


class ZelFees(db.Model):
    __tablename__ = "zel_fees"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fee_type: Mapped[str] = mapped_column(String(100), nullable=False)
    school_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("zel_school.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    term: Mapped[str] = mapped_column(String(100), nullable=False)
    session: Mapped[str] = mapped_column(String(100), nullable=False)

    school = relationship("ZelSchool", back_populates="fees")


class ZelBankAccounts(db.Model):
    __tablename__ = "zel_bank_accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("zel_school.id"))
    bank_name: Mapped[str] = mapped_column(String(100))
    account_name: Mapped[str] = mapped_column(String(250))
    account_number: Mapped[str] = mapped_column(String(50))

    school = relationship("ZelSchool", back_populates="bank_accounts")


class ZelPayment(db.Model):
    __tablename__ = "zel_payment"
    receipt_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_date: Mapped[str] = mapped_column(String(100), nullable=False)
    payer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    payer_name: Mapped[str] = mapped_column(String(250), nullable=False)
    payer_class: Mapped[str] = mapped_column(String(250), nullable=True)
    payment_date: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    discount: Mapped[float] = mapped_column(Float, nullable=False)
    fee_type: Mapped[str] = mapped_column(String(100), nullable=False)
    session: Mapped[str] = mapped_column(String(100), nullable=False)
    term: Mapped[str] = mapped_column(String(100), nullable=False)
    payment_means: Mapped[str] = mapped_column(String(250), nullable=False)
    receiving_bank: Mapped[str] = mapped_column(String(250), nullable=False)
    receiving_account: Mapped[str] = mapped_column(String(50))
    school_id: Mapped[int] = mapped_column(Integer, nullable=False)
    posted_by_id: Mapped[str] = mapped_column(String(100), db.ForeignKey("zel_user.id"))

    posted_by = relationship("ZelUser", back_populates="posted_by")


class ZelResult(db.Model):
    __tablename__ = "zel_result"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[str] = mapped_column(String(100), db.ForeignKey("zel_user.id"))
    subject_id: Mapped[int] = mapped_column(Integer)
    ca1: Mapped[float] = mapped_column(Float, nullable=True)
    ca2: Mapped[float] = mapped_column(Float, nullable=True)
    ca3: Mapped[float] = mapped_column(Float, nullable=True)
    exam_obj_score: Mapped[float] = mapped_column(Float, nullable=True)
    adjusted_exam_obj_score: Mapped[float] = mapped_column(Float, nullable=True)
    practical_score: Mapped[float] = mapped_column(Float, nullable=True)
    exam_theory_score: Mapped[float] = mapped_column(Float, nullable=True)
    total_exam_score: Mapped[float] = mapped_column(Float, nullable=True)
    total_score: Mapped[int] = mapped_column(Integer, nullable=True)
    grade: Mapped[str] = mapped_column(String(2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=True)
    remarks: Mapped[str] = mapped_column(String(100), nullable=True)
    classroom: Mapped[str] = mapped_column(String(100))
    term: Mapped[str] = mapped_column(String(100))
    session: Mapped[str] = mapped_column(String(100))

    student = relationship("ZelUser", back_populates="results")


class ZelAttendance(db.Model):
    __tablename__ = "zel_attendance"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[str] = mapped_column(String(100))
    date: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    teacher_id: Mapped[str] = mapped_column(String(100), db.ForeignKey("zel_user.id"))
    classroom: Mapped[str] = mapped_column(String(100))

    teacher = relationship("ZelUser", back_populates="class_teacher")


class ZelAttendanceNew(db.Model):
    __tablename__ = "zel_attendance_new"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[str] = mapped_column(String(100))
    date: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    teacher_id: Mapped[str] = mapped_column(String(100), nullable=False)
    classroom_id: Mapped[int] = mapped_column(Integer)
    term: Mapped[str] = mapped_column(String(100))
    session: Mapped[str] = mapped_column(String(100))
    time_captured: Mapped[int] = mapped_column(Integer, nullable=True)


class ZelIssues(db.Model):
    __tablename__ = "zel_issues"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[str] = mapped_column(String(100), db.ForeignKey("zel_user.id"))
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    details: Mapped[str] = mapped_column(String(2000), nullable=False)
    date_entered: Mapped[str] = mapped_column(String(100), nullable=False)
    is_resolved: Mapped[str] = mapped_column(String(100), nullable=True)
    date_resolved: Mapped[str] = mapped_column(String(100), nullable=True)
    date_reopened: Mapped[str] = mapped_column(String(100), nullable=True)
    date_resolved_2: Mapped[str] = mapped_column(String(100), nullable=True)
    assigned_to: Mapped[str] = mapped_column(String(100), db.ForeignKey("zel_user.id"), nullable=True)


class ZelTimetable(db.Model):
    __tablename__ = "zel_timetable"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    classroom_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("zel_classroom.id"))
    subject: Mapped[int] = mapped_column(Integer, db.ForeignKey("zel_subject.id"))
    date: Mapped[str] = mapped_column(String(100), nullable=False)
    time: Mapped[str] = mapped_column(String(100), nullable=True)
    term: Mapped[str] = mapped_column(String(100), nullable=True)
    session: Mapped[str] = mapped_column(String(100), nullable=True)


class ZelLog(db.Model):
    __tablename__ = "zel_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), db.ForeignKey("zel_user.id"))
    current_page: Mapped[str] = mapped_column(String(50), nullable=False)
    date: Mapped[str] = mapped_column(String(50), nullable=False)
    time: Mapped[str] = mapped_column(String(50), nullable=False)
    activity: Mapped[str] = mapped_column(String(500), nullable=True)

    user = relationship("ZelUser", back_populates="log")


class ZelObjQuestions(db.Model):
    __tablename__ = "zel_obj_questions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question: Mapped[str] = mapped_column(String(1000), nullable=False)
    options: Mapped[str] = mapped_column(String(1000), nullable=False)
    correct_option: Mapped[str] = mapped_column(String(500), nullable=False)
    session: Mapped[str] = mapped_column(String(50), nullable=False)
    term: Mapped[str] = mapped_column(String(50), nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("zel_subject.id"))
    school_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("zel_school.id"))
    grade: Mapped[int] = mapped_column(Integer, nullable=True)

    subject = relationship("ZelSubject", back_populates="obj_question")
    school = relationship("ZelSchool", back_populates="obj_question")


class ZelTermDefine(db.Model):
    __tablename__ = "zel_term_define"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term: Mapped[str] = mapped_column(String(100), nullable=False)
    session: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[str] = mapped_column(String(100), nullable=False)
    end_date: Mapped[str] = mapped_column(String(100), nullable=False)
    school_id: Mapped[int] = mapped_column(Integer, nullable=False)


class ZelPublicHoliday(db.Model):
    __tablename__ = "zel_public_holiday"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(100), nullable=False)


class ZelClassSubjects(db.Model):
    __tablename__ = "zel_class_subjects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(Integer, nullable=False)
    subjects_list: Mapped[str] = mapped_column(String(500), nullable=False)
    class_variant: Mapped[str] = mapped_column(String(50), nullable=True)
    classroom_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("zel_classroom.id"), nullable=True)

    classroom = relationship("ZelClassroom", back_populates="class_subjects")


class ZelPsychomotor(db.Model):
    __tablename__ = "zel_psychomotor"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[str] = mapped_column(String(100), nullable=False)
    classroom: Mapped[str] = mapped_column(String(100), nullable=False)
    term: Mapped[str] = mapped_column(String(50), nullable=False)
    session: Mapped[str] = mapped_column(String(50), nullable=False)
    class_participation: Mapped[str] = mapped_column(String(50), nullable=True)
    homework: Mapped[str] = mapped_column(String(50), nullable=True)
    project: Mapped[str] = mapped_column(String(50), nullable=True)
    leadership: Mapped[str] = mapped_column(String(50), nullable=True)
    neatness: Mapped[str] = mapped_column(String(50), nullable=True)
    politeness: Mapped[str] = mapped_column(String(50), nullable=True)
    punctuality: Mapped[str] = mapped_column(String(50), nullable=True)
    interaction: Mapped[str] = mapped_column(String(50), nullable=True)
    responsibility: Mapped[str] = mapped_column(String(50), nullable=True)
    creativity: Mapped[str] = mapped_column(String(50), nullable=True)
    christ_likeness: Mapped[str] = mapped_column(String(50), nullable=True)
    honesty: Mapped[str] = mapped_column(String(50), nullable=True)
    self_control: Mapped[str] = mapped_column(String(50), nullable=True)
    teacher_comment: Mapped[str] = mapped_column(String(500), nullable=True)


class ExamQuestionsObj(db.Model):
    __tablename__ = 'exam_questions_obj'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_grade: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, nullable=False)
    school_id: Mapped[int] = mapped_column(Integer, nullable=False)
    term: Mapped[str] = mapped_column(String(50), nullable=False)
    session: Mapped[str] = mapped_column(String(50), nullable=False)
    question_id: Mapped[str] = mapped_column(String(500), nullable=True)
    exam_date: Mapped[str] = mapped_column(String(50), nullable=False)
    exam_time: Mapped[str] = mapped_column(String(50), nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False)


class ExamQuestionsTheory(db.Model):
    __tablename__ = 'exam_questions_theory'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_grade: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, nullable=False)
    school_id: Mapped[int] = mapped_column(Integer, nullable=False)
    term: Mapped[str] = mapped_column(String(50), nullable=False)
    session: Mapped[str] = mapped_column(String(50), nullable=False)
    question_id: Mapped[str] = mapped_column(String(500), nullable=True)
    exam_date: Mapped[str] = mapped_column(String(50), nullable=False)
    exam_time: Mapped[str] = mapped_column(String(50), nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False)


class QuestionPoolObj(db.Model):
    __tablename__ = 'question_pool_obj'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(Integer, nullable=False)
    class_grade: Mapped[int] = mapped_column(Integer, nullable=False)
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    sub_topic: Mapped[str] = mapped_column(String(500), nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    correct_option: Mapped[str] = mapped_column(String(500), nullable=False)
    options: Mapped[str] = mapped_column(String(500), nullable=False)
    question_background_id: Mapped[int] = mapped_column(Integer, db.ForeignKey('question_background.id'), nullable=True)
    user_type: Mapped[str] = mapped_column(String(50), nullable=False)
    question_source: Mapped[str] = mapped_column(String(50), nullable=True)
    question_year: Mapped[int] = mapped_column(Integer, nullable=True)
    question_type: Mapped[str] = mapped_column(String(50), nullable=True)

    question_background = relationship("QuestionBackground", back_populates="child_question")
    obj_results = relationship("ZelObjResults", back_populates="question")


class QuestionPoolTheory(db.Model):
    __tablename__ = 'question_pool_theory'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(Integer, nullable=False)
    class_grade: Mapped[int] = mapped_column(Integer, nullable=False)
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    sub_topic: Mapped[str] = mapped_column(String(500), nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    user_type: Mapped[str] = mapped_column(String(50), nullable=False)
    question_source: Mapped[str] = mapped_column(String(50), nullable=True)
    question_year: Mapped[int] = mapped_column(Integer, nullable=True)
    question_type: Mapped[str] = mapped_column(String(50), nullable=True)


class QuestionBackground(db.Model):
    __tablename__ = 'question_background'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(Integer, nullable=False)
    question_background: Mapped[str] = mapped_column(Text, nullable=False)

    child_question = relationship("QuestionPoolObj", back_populates="question_background")


with app.app_context():
    db.create_all()


@app.route("/CTA/", methods=["GET", "POST"])
def cta_home():
    company_name = ""
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.lower()
        passcode = form.passcode.data
        user = db.session.execute(db.select(User).where(User.username == username)).scalar()
        if not user:
            flash("Incorrect Username. Please try again")
            return redirect(url_for("cta_home"))
        elif not check_password_hash(user.passcode, passcode):
            flash("Wrong Passcode. Please enter the correct Passcode")
            return redirect(url_for("cta_home"))
        else:
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template("login.html", form=form, title="Login",
                           description="Please enter your login details.", year=this_year, company_name=company_name,
                           filename="")


# Create register route
@app.route("/register", methods=["GET", "POST"])
@admin_only
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        surname = form.surname.data.title()
        first_name = form.first_name.data.title()
        if form.company.data == "SOSIEC":
            username = f"sosiec_{first_name[0].lower()}{surname.lower()}"
        else:
            username = f"{first_name[0].lower()}{surname.lower()}"
        users = db.session.execute(db.select(User).where(User.username.startswith(username))).scalars().all()
        if users:
            username = f"{username}{len(users)}"
        passcode = random.randint(100000, 999999)
        hashed_passcode = generate_password_hash(str(passcode), method='pbkdf2:sha256', salt_length=random.randint(8, 10))
        branch = form.branch.data
        user_type = form.user_type.data

        new_user = User()
        new_user.surname = surname
        new_user.first_name = first_name
        new_user.username = username.lower()
        new_user.passcode = hashed_passcode
        new_user.branch = branch
        new_user.user_type = user_type

        db.session.add(new_user)
        db.session.commit()

        with SMTP_SSL("smtp.gmail.com", port=465) as connection:
            connection.login(user="zelcoders@gmail.com", password=zelcoders_password)
            connection.sendmail(from_addr="zelcoders@gmail.com", to_addrs="zelcoders@gmail.com",
                                msg=f"Subject:Champions Transformation Academy New User Account\n\nA new account "
                                    f"has been created for {surname} {first_name} on Champions Transformation Academy portal with below details:\n\n"
                                    f"Username: {username}\nPasscode: {passcode}\n\nEnsure you keep your passcode safe and do not disclose to "
                                    f"anyone.\n\nRegards,\nZelcoders Team.")
        return redirect(url_for("register"))


    return render_template("login.html", form=form, title="Register User", year=this_year)

# make dashboard route require login

@app.route("/CTA/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    # let it load courses to set exams for if the user is an instructor and load courses to write exam if the user is a student
    courses = db.session.execute(db.select(Courses).order_by(Courses.course_title)).scalars().all()
    user = db.session.execute(db.select(User).where(User.id == current_user.id)).scalar()

    is_instructor = False
    for course in courses:
        if user.id == course.instructor_id:
            is_instructor = True
    if is_instructor:
        courses = db.session.execute(db.select(Courses).where(Courses.instructor_id == user.id).order_by(Courses.course_title)).scalars().all()

    is_exam = {}
    for course in courses:
        exam_questions = db.session.execute(db.select(Questions).where(Questions.course_id == course.id)).scalars().all()
        if exam_questions:
            is_exam[course.id] = True
        else:
            is_exam[course.id] = False

    return render_template("dashboard.html", courses=courses, user=user, title="Courses", is_instructor=is_instructor, year=this_year, is_exam=is_exam)


@app.route("/CTA/add_course", methods=["GET", "POST"])
@admin_only
def add_course():
    company_name = "Champions Transformation Academy"
    form = CoursesForm()
    if form.validate_on_submit():
        course_code = form.course_code.data
        course_title = form.course_title.data
        course_description = form.course_description.data
        instructor = form.instructor_username.data

        instructor_details = db.session.execute(db.select(User).where(User.username == instructor)).scalar()

        new_course = Courses()
        new_course.course_code = course_code
        new_course.course_title = course_title
        new_course.course_description = course_description
        new_course.instructor_id = instructor_details.id

        db.session.add(new_course)
        db.session.commit()

        return redirect(url_for("add_course"))


    return render_template("login.html", form=form, title="Register New Course", year=this_year,
                           company_name=company_name, filename="assets/img/cca_logo.png")

# create a route for setting exam questions loading the question form
@app.route("/CTA/set_exam_questions", methods=["GET", "POST"])
@instructor_only
def set_exam():
    company_name = "Champions Transformation Academy"
    course_code = request.args.get("course_code")
    course = db.session.execute(db.select(Courses).where(Courses.course_code == course_code)).scalar()
    form = ExamQuestionsForm()
    if form.validate_on_submit():
        question = form.questions.data
        correct_option = form.correct_answer.data
        options = ""
        options += f"{correct_option}"
        wrong_option1 = form.wrong_answer1.data
        options += f";{wrong_option1}"
        if form.wrong_answer2.data != "":
            wrong_option2 = form.wrong_answer2.data
            options += f";{wrong_option2}"
        if form.wrong_answer3.data != "":
            wrong_option3 = form.wrong_answer3.data
            options += f";{wrong_option3}"
        if form.wrong_answer4.data != "":
            wrong_option4 = form.wrong_answer4.data
            options += f";{wrong_option4}"

        new_question = Questions()
        new_question.question = question
        new_question.correct_option = correct_option
        new_question.options = options
        new_question.course_id = course.id

        db.session.add(new_question)
        db.session.commit()

        return redirect(url_for("set_exam", course_code=course_code))

    return render_template("login.html", form=form, year=this_year, title=f"{course.course_title} Exam",
                           course=course, company_name=company_name, filename="assets/img/cca_logo.png")


# create a route for loading exam questions for a selected course
@app.route("/CTA/exam", methods=["GET", "POST"])
@login_required
def exam():
    company_name = "Champions Transformation Academy"
    course_code = request.args.get("course_code")
    course = db.session.execute(db.select(Courses).where(Courses.course_code == course_code)).scalar()

    exam_questions = db.session.execute(db.select(Questions).where(Questions.course_id == course.id)).scalars().all()

    exam_dict = []
    for question in exam_questions:
        options = question.options.split(";")
        random.shuffle(options)
        new_question = {
            "question_no": exam_questions.index(question) + 1,
            "question_id": question.id,
            "question": question.question,
            "correct_option": question.correct_option,
            "options": options
        }
        exam_dict.append(new_question)


    if request.method == "POST":
        course_id = course.id
        user_id = current_user.id

        results = db.session.execute(db.select(Results).where(Results.user_id == user_id, Results.course_id == course_id)).scalars().all()
        score = db.session.execute(db.select(Scores).where(Scores.user_id == user_id, Scores.course_id == course_id)).scalar()

        if score.score > 0 and score.remark != "Retake":
            return redirect(url_for('check_result', course_code=course_code))

        if results:
            for result in results:
                db.session.delete(result)
                db.session.commit()
            old_score = db.session.execute(db.select(Scores).where(Scores.user_id == user_id, Scores.course_id == course_id)).scalar()
            if old_score:
                db.session.delete(old_score)
                db.session.commit()

        for i in range(len(exam_dict)):
            if request.form.get(f"question_{i+1}") is None:
                selected_answer = "Not answered"
            else:
                selected_answer = request.form.get(f"question_{i+1}")
            correct_option = exam_dict[i]["correct_option"]
            question_id = exam_dict[i]["question_id"]

            new_result = Results()
            new_result.user_id = user_id
            new_result.course_id = course_id
            new_result.question_id = question_id
            new_result.selected_answer = selected_answer
            new_result.correct_answer = correct_option

            db.session.add(new_result)
            db.session.commit()

        score_calc = db.session.execute(db.select(Results).where(Results.user_id == current_user.id, Results.course_id == course.id)).scalars().all()

        student_score = 0
        for result in score_calc:
            if result.selected_answer == result.correct_answer:
                student_score += 1

        exam_score = db.session.execute(db.select(Scores).where(Scores.user_id == current_user.id, Scores.course_id == course.id)).scalar()

        exam_score.score = (student_score/len(exam_dict)) * 100
        if student_score >= len(exam_questions)/2:
            exam_score.remark = "Pass"
        else:
            exam_score.remark = "Fail"

        db.session.commit()

        return redirect(url_for('check_result', course_code=course_code))

    score = db.session.execute(db.select(Scores).where(Scores.course_id == course.id, Scores.user_id == current_user.id,
                                                       Scores.remark == "Pass")).scalar()
    score_fail = db.session.execute(db.select(Scores).where(Scores.course_id == course.id, Scores.user_id == current_user.id,
                                                        Scores.remark == "Fail")).scalar()

    if score or score_fail:
        return redirect(url_for('check_result', course_code=course_code))


    new_score = Scores()
    new_score.user_id = current_user.id
    new_score.course_id = course.id
    new_score.year = str(this_year)
    new_score.score = 0
    new_score.remark = "Fail"

    db.session.add(new_score)
    db.session.commit()

    return render_template("exams.html", questions=exam_dict, year=this_year,
                           title=f"{course.course_title} Exam", course=course, company_name=company_name,
                           filename="assets/img/cca_logo.png")


@app.route("/CTA/result")
@login_required
def check_result():
    company_name = "Champions Transformation Academy"
    course_code = request.args.get("course_code")
    course = db.session.execute(db.select(Courses).where(Courses.course_code == course_code)).scalar()

    results = db.session.execute(db.select(Results).where(Results.course_id == course.id, Results.user_id == current_user.id)).scalars().all()

    score = db.session.execute(db.select(Scores).where(Scores.course_id == course.id, Scores.user_id == current_user.id).order_by(Scores.score)).scalars().all()
    score = score[-1]
    score_percent = round(score.score)
    if score_percent >= 50:
        remark = "Congratulations! You have passed this course"
    else:
        remark = "Sorry! You scored below the pass mark for this course and you need to rewrite this exam."

    return render_template("result.html", title=f"{course.course_title} Results", results=results,
                           score=score_percent, remark=remark, company_name=company_name, filename="assets/img/cca_logo.png")


@app.route("/CTA/logout")
def logout():
    logout_user()
    return redirect(url_for('cta_home'))


@app.route("/CTA/instruction")
@login_required
def instruction():
    company_name = "Champions Transformation Academy"
    course_code = request.args.get("course_code")
    course = db.session.execute(db.select(Courses).where(Courses.course_code == course_code)).scalar()
    return render_template("instruction.html", title=f"{course.course_title} Exam Instructions", course=course)


@app.route("/CTA/scores")
@admin_only
def download_scores():
    all_scores = db.session.execute(db.select(Scores)).scalars().all()
    score_id_list = []
    course_list = []
    user_id_list = []
    user_surname_list = []
    user_first_name_list = []
    year_list = []
    score_list = []
    remark_list = []
    for score in all_scores:
        score_id_list.append(score.id)
        user_id_list.append(score.user_id)
        user_surname_list.append(score.user.surname)
        user_first_name_list.append(score.user.first_name)
        year_list.append(score.year)
        course_list.append(score.course.course_title)
        score_list.append(score.score)
        remark_list.append(score.remark)
    scores_dict = {
        "Score ID": score_id_list,
        "Course": course_list,
        "User ID": user_id_list,
        "Surname": user_surname_list,
        "First Name": user_first_name_list,
        "Year": year_list,
        "Score": score_list,
        "Remark": remark_list
    }
    scores_df = pd.DataFrame(scores_dict)
    scores_df.to_csv("static/scores.csv", index=False)

    return send_from_directory('static', path="scores.csv")


@app.route("/CTA/view_questions")
@instructor_only
def view_questions():
    course_code = request.args.get("course_code")
    course = db.session.execute(db.select(Courses).where(Courses.course_code == course_code)).scalar()
    questions = db.session.execute(db.select(Questions).where(Questions.course_id == course.id)).scalars().all()

    exam_dict = []
    for question in questions:
        options = question.options.split(";")
        new_question = {
            "question_no": questions.index(question) + 1,
            "question_id": question.id,
            "question": question.question,
            "correct_option": question.correct_option,
            "options": options
        }
        exam_dict.append(new_question)
    return render_template("view_questions.html", title=f"{course.course_title} Questions", questions=exam_dict, course=course)


@app.route("/CTA/edit_question", methods=["GET", "POST"])
@instructor_only
def edit_question():
    q_id = request.args.get("q_id")
    question = db.session.execute(db.select(Questions).where(Questions.id == q_id)).scalar()
    course_code = request.args.get("course_code")
    course = db.session.execute(db.select(Courses).where(Courses.course_code == course_code)).scalar()
    options = question.options.split(";")
    form = ExamQuestionsForm(
        questions=question.question,
        correct_answer=question.correct_option,
        wrong_answer1=question.options.split(";")[1],
    )
    for i in range(len(options)):
        if i == 2:
            form.wrong_answer2.data = question.options.split(";")[2]
        elif i == 3:
            form.wrong_answer3.data = question.options.split(";")[3]
        elif i == 4:
            form.wrong_answer4.data = question.options.split(";")[4]
    form.submit.label.text = "Update Question"
    if form.validate_on_submit():
        updated_correct_option = form.correct_answer.data
        updated_options = ""
        updated_options += f"{updated_correct_option}"
        wrong_option1 = form.wrong_answer1.data
        updated_options += f";{wrong_option1}"
        if request.form.get("wrong_answer2") != "":
            wrong_option2 = request.form.get("wrong_answer2")
            updated_options += f";{wrong_option2}"
        if request.form.get("wrong_answer3") != "":
            wrong_option3 = request.form.get("wrong_answer3")
            updated_options += f";{wrong_option3}"
        if request.form.get("wrong_answer4") != "":
            wrong_option4 = request.form.get("wrong_answer4")
            updated_options += f";{wrong_option4}"

        question.question = form.questions.data
        question.correct_option = updated_correct_option
        question.options = updated_options

        db.session.commit()
        return redirect(url_for("view_questions", course_code=course_code))
    return render_template("login.html", form=form, year=this_year, title=f"{course.course_title} Exam",
                               course=course)


# create a route for loading exam questions for a selected course
@app.route("/GCR/entrance-exam", methods=["GET", "POST"])
@login_required
def exam_gcree():
    company_name = "The Golden Crest Royal Academy"
    course_code = "GCR-EE"
    course = db.session.execute(db.select(Courses).where(Courses.course_code == course_code)).scalar()

    exam_questions = db.session.execute(db.select(Questions).where(Questions.course_id == course.id)).scalars().all()

    exam_dict = []
    for question in exam_questions:
        options = question.options.split(";")
        random.shuffle(options)
        new_question = {
            "question_no": exam_questions.index(question) + 1,
            "question_id": question.id,
            "question": question.question,
            "correct_option": question.correct_option,
            "options": options
        }
        exam_dict.append(new_question)

    if request.method == "POST":
        course_id = course.id
        user_id = current_user.id

        results = db.session.execute(
            db.select(Results).where(Results.user_id == user_id, Results.course_id == course_id)).scalars().all()
        score = db.session.execute(
            db.select(Scores).where(Scores.user_id == user_id, Scores.course_id == course_id)).scalar()

        if score.score > 0 and score.remark != "Retake":
            return redirect(url_for('check_result_gcree', course_code=course_code))

        if results:
            for result in results:
                db.session.delete(result)
                db.session.commit()
            old_score = db.session.execute(
                db.select(Scores).where(Scores.user_id == user_id, Scores.course_id == course_id)).scalar()
            if old_score:
                db.session.delete(old_score)
                db.session.commit()

        for i in range(len(exam_dict)):
            if request.form.get(f"question_{i + 1}") is None:
                selected_answer = "Not answered"
            else:
                selected_answer = request.form.get(f"question_{i + 1}")
            correct_option = exam_dict[i]["correct_option"]
            question_id = exam_dict[i]["question_id"]

            new_result = Results()
            new_result.user_id = user_id
            new_result.course_id = course_id
            new_result.question_id = question_id
            new_result.selected_answer = selected_answer
            new_result.correct_answer = correct_option

            db.session.add(new_result)
            db.session.commit()

        score_calc = db.session.execute(db.select(Results).where(Results.user_id == current_user.id,
                                                                 Results.course_id == course.id)).scalars().all()

        student_score = 0
        for result in score_calc:
            if result.selected_answer == result.correct_answer:
                student_score += 1

        exam_score = db.session.execute(
            db.select(Scores).where(Scores.user_id == current_user.id, Scores.course_id == course.id)).scalar()

        exam_score.score = (student_score / len(exam_dict)) * 100
        if student_score >= len(exam_questions) / 2:
            exam_score.remark = "Pass"
        else:
            exam_score.remark = "Fail"

        db.session.commit()

        return redirect(url_for('check_result_gcree', course_code=course_code))

    score = db.session.execute(db.select(Scores).where(Scores.course_id == course.id, Scores.user_id == current_user.id,
                                                       Scores.remark == "Pass")).scalar()
    score_fail = db.session.execute(
        db.select(Scores).where(Scores.course_id == course.id, Scores.user_id == current_user.id,
                                Scores.remark == "Fail")).scalar()

    if score or score_fail:
        return redirect(url_for('check_result', course_code=course_code))

    new_score = Scores()
    new_score.user_id = current_user.id
    new_score.course_id = course.id
    new_score.year = str(this_year)
    new_score.score = 0
    new_score.remark = "Fail"

    db.session.add(new_score)
    db.session.commit()

    return render_template("exams-gcr.html", questions=exam_dict, year=this_year,
                           title=f"{course.course_title}", course=course, company_name=company_name,
                           filename="assets/img/gcra_logo2.png")


@app.route("/check_result_gcree")
@login_required
def check_result_gcree():
    company_name = "The Golden Crest Royal Academy"
    course_code = request.args.get("course_code")

    course = db.session.execute(db.select(Courses).where(Courses.course_code == course_code)).scalar()

    results = db.session.execute(
        db.select(Results).where(Results.course_id == course.id, Results.user_id == current_user.id)).scalars().all()

    score = db.session.execute(
        db.select(Scores).where(Scores.course_id == course.id, Scores.user_id == current_user.id).order_by(
            Scores.score)).scalars().all()
    score = score[-1]
    score_percent = round(score.score)
    return render_template("check_result.html", title="Entrance Exam Results", company_name=company_name,
                           results=results, score=score_percent, filename="assets/img/gcra_logo2.png")


@app.route("/gcree", methods=["GET", "POST"])
def instructions_gcree():
    company_name= "The Golden Crest Royal Academy"
    entrance_form = GcreeForm()
    if entrance_form.validate_on_submit():
        surname = entrance_form.surname.data.title()
        other_names = entrance_form.other_names.data.title()
        age = entrance_form.age.data

        username = f"gcr_{other_names[0].lower()}{surname.lower()}"

        users = db.session.execute(db.select(User).where(User.username.startswith(username))).scalars().all()
        if users:
            username = f"{username}{len(users)}"
        passcode = random.randint(100000, 999999)
        hashed_passcode = generate_password_hash(str(passcode), method='pbkdf2:sha256',
                                                 salt_length=random.randint(8, 10))
        branch = "GCR"
        user_type = "Prospective Student"

        new_user = User()
        new_user.surname = surname
        new_user.first_name = other_names
        new_user.username = username.lower()
        new_user.passcode = hashed_passcode
        new_user.branch = branch
        new_user.user_type = user_type

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        user_id = db.session.execute(db.select(User).where(User.username == username.lower())).scalar()

        with SMTP_SSL("smtp.gmail.com", port=465) as connection:
            connection.login(user="zelcoders@gmail.com", password=zelcoders_password)
            connection.sendmail(from_addr="zelcoders@gmail.com", to_addrs="zelcoders@gmail.com",
                                msg=f"Subject:Golden Crest Entrance exam New User Account\n\nA new account "
                                    f"has been created for {surname} {other_names} on Golden Crest Entrance Exam portal with below details:\n\n"
                                    f"Username: {username}\nPasscode: {passcode}\nAge: {age}\n\nEnsure you keep your passcode safe and do not disclose to "
                                    f"anyone.\n\nRegards,\nZelcoders Team.")

        return redirect(url_for("exam_gcree"))
    return render_template("instruction-gcree.html", company_name=company_name, filename="assets/img/gcra_logo2.png", title="Entrance Exam Instructions", form=entrance_form)


@app.route("/exam/<school_code>", methods=["GET", "POST"])
def instructions_gcr(school_code):
    sch_code = school_code.upper()
    school_details = db.session.execute(db.select(ZelSchool).where(ZelSchool.code == sch_code)).scalar()
    school_name = school_details.name
    pre_exam_form = TerminalExamForm()
    if pre_exam_form.validate_on_submit():
        exam_number = int(pre_exam_form.student_id.data)
        student_id = f"{sch_code}-S-{exam_number}"
        user = db.get_or_404(ZelUser, student_id)
        login_user(user)

        student_id = current_user.id
        school_code = student_id[0:3]
        school_name = current_user.school.name
        school_id = current_user.school.id
        student_classroom_id = current_user.classroom_id
        class_grade = db.session.execute(
            db.select(ZelClassroom).where(ZelClassroom.id == student_classroom_id)).scalar().grade

        today_exam = db.session.execute(db.select(ExamQuestionsObj).where(
            ExamQuestionsObj.class_grade == class_grade, ExamQuestionsObj.exam_date == datetime.strftime(datetime.now().date(), '%Y-%m-%d'),
            ExamQuestionsObj.school_id == school_id, ExamQuestionsObj.term == get_current_term(),
            ExamQuestionsObj.session == get_current_session()
        )).scalars().all()

        if not today_exam:
            flash('You have no CBT exams to write today.')
            return redirect(url_for('instructions_gcr', school_code=school_code))
        else:
            exams_list = []
            for exam_sub in today_exam:
                subj_id = exam_sub.subject_id
                subject_rec = db.get_or_404(ZelSubject, subj_id)
                subject_name = subject_rec.subject_name
                exams_list.append({'subject_id': subj_id, 'subject_name': subject_name})
            return render_template('select.html', company_name=school_name, filename="assets/img/gcra_logo2.png",
                                   exams=exams_list, title="Select Subject",)
    return render_template("instruction-gcree.html", company_name=school_name,
                           filename="assets/img/gcra_logo2.png", title="Exam Instructions", form=pre_exam_form)


@app.route("/term-exam/<subject_id>", methods=["GET", "POST"])
@login_required
def term_exam_obj(subject_id):
    if not current_user.is_authenticated:
        return abort(401)
    student_id = current_user.id
    school_code = student_id[0:3]
    school_name = current_user.school.name
    school_id = current_user.school.id
    student_classroom_id = current_user.classroom_id
    class_grade = db.session.execute(db.select(ZelClassroom).where(ZelClassroom.id == student_classroom_id)).scalar().grade

    today_exam = db.session.execute(db.select(ExamQuestionsObj).where(
        ExamQuestionsObj.class_grade == class_grade, ExamQuestionsObj.subject_id == subject_id,
        ExamQuestionsObj.school_id == school_id, ExamQuestionsObj.term == get_current_term(),
        ExamQuestionsObj.session == get_current_session()
    )).scalar()

    if datetime.strptime(today_exam.exam_date, '%Y-%m-%d').date() != datetime.now().date():
        flash("Exam is not available yet.")
        return redirect(url_for("instructions_gcr", school_code=school_code))

    questions_list = today_exam.question_id.split("`")
    exam_duration = today_exam.duration
    exam_weight = today_exam.weight

    exam_dict = []
    already_selected_q_id = []
    for q_id in questions_list:
        q_id_int = int(q_id)
        question = db.session.execute(db.select(QuestionPoolObj).where(QuestionPoolObj.id == q_id_int)).scalar()
        if question.question_background_id is not None and question.id not in already_selected_q_id:
            already_selected_q_id.append(q_id_int)
            question_background_id = question.question_background_id
            question_background = db.session.execute(db.select(QuestionBackground).where(
                QuestionBackground.id == question_background_id)).scalar()
            question_options = question.options.split("`")
            random.shuffle(question_options)
            new_question = {
                "question_no": already_selected_q_id.index(q_id_int) + 1,
                "question_id": q_id_int,
                "question": question.question,
                "correct_option": question.correct_option,
                "options": question_options,
                "question_background": question_background.question_background
            }
            exam_dict.append(new_question)

            # get all questions with the same question background
            questions_with_same_bg = db.session.execute(db.select(QuestionPoolObj).where(
                QuestionPoolObj.question_background_id == question_background_id
            )).scalars().all()
            for q in questions_with_same_bg:
                if q.id not in already_selected_q_id:
                    already_selected_q_id.append(q.id)
                    question_options = q.options.split("`")
                    random.shuffle(question_options)
                    new_question = {
                        "question_no": already_selected_q_id.index(q.id) + 1,
                        "question_id": q.id,
                        "question": q.question,
                        "correct_option": q.correct_option,
                        "options": question_options,
                        "question_background": ""
                    }
                    exam_dict.append(new_question)
        else:
            if q_id_int not in already_selected_q_id:
                already_selected_q_id.append(q_id_int)
                question_options = question.options.split("`")
                random.shuffle(question_options)
                new_question = {
                    "question_no": already_selected_q_id.index(q_id_int) + 1,
                    "question_id": q_id_int,
                    "question": question.question,
                    "correct_option": question.correct_option,
                    "options": question_options,
                    "question_background": ""
                }
                exam_dict.append(new_question)

    subject = db.session.execute(db.select(ZelSubject).where(ZelSubject.id == subject_id)).scalar()

    if request.method == "POST":
        score_calc = db.session.execute(db.select(ZelObjResults).where(
            ZelObjResults.user_id == current_user.id, ZelObjResults.subject_id == subject_id,
            ZelObjResults.term == get_current_term(), ZelObjResults.session == get_current_session()
        )).scalars().all()

        if score_calc:
            flash("You have already completed this exam. Contact admin if you haven't.")
            return redirect(url_for('check_result_gcr', subject_id=subject_id))

        student_subject_record = db.session.execute(db.select(ZelResult).where(
            ZelResult.student_id == current_user.id, ZelResult.subject_id == subject_id,
            ZelResult.term == get_current_term(), ZelResult.session == get_current_session()
        )).scalar()

        if student_subject_record.exam_obj_score:
            flash("You have already written the Objectives paper. Contact admin if you haven't written the exam.")
            return redirect(url_for('term_exam_theory', subject_id=subject_id))

        subject_id = subject.id
        user_id = current_user.id

        results = db.session.execute(
            db.select(ZelObjResults).where(ZelObjResults.user_id == user_id, ZelObjResults.subject_id == subject_id)).scalars().all()

        if results:
            for result in results:
                db.session.delete(result)
                db.session.commit()

        for i in range(len(exam_dict)):
            if request.form.get(f"question_{i + 1}") is None:
                selected_answer = "Not answered"
            else:
                selected_answer = request.form.get(f"question_{i + 1}")
            correct_option = exam_dict[i]["correct_option"]
            question_id = exam_dict[i]["question_id"]

            new_result = ZelObjResults()
            new_result.user_id = user_id
            new_result.subject_id = subject_id
            new_result.question_id = question_id
            new_result.selected_answer = selected_answer
            new_result.correct_answer = re.sub(r"<.*?>", "", correct_option)
            new_result.term = get_current_term()
            new_result.session = get_current_session()
            new_result.classroom_id = current_user.classroom_id

            db.session.add(new_result)
            db.session.commit()

        score_calc = db.session.execute(db.select(ZelObjResults).where(
            ZelObjResults.user_id == current_user.id, ZelObjResults.subject_id == subject_id,
            ZelObjResults.term == get_current_term(), ZelObjResults.session == get_current_session()
        )).scalars().all()

        student_score = 0
        for result in score_calc:
            if result.selected_answer == result.correct_answer:
                student_score += 1

        student_subject_record = db.session.execute(db.select(ZelResult).where(
            ZelResult.student_id == current_user.id, ZelResult.subject_id == subject_id,
            ZelResult.term == get_current_term(), ZelResult.session == get_current_session()
        )).scalar()

        student_subject_record.exam_obj_score = student_score

        adjusted_exam_obj_score = (student_score/len(exam_dict)) * exam_weight
        student_subject_record.adjusted_exam_obj_score = round(adjusted_exam_obj_score, 1)

        db.session.commit()

        return redirect(url_for('term_exam_theory', subject_id=subject_id))

    score_calc = db.session.execute(db.select(ZelObjResults).where(
        ZelObjResults.user_id == current_user.id, ZelObjResults.subject_id == subject_id,
        ZelObjResults.term == get_current_term(), ZelObjResults.session == get_current_session()
    )).scalars().all()

    if score_calc:
        flash("You have already completed this exam. Contact admin if you haven't.")
        return redirect(url_for('check_result_gcr', subject_id=subject_id))

    student_subject_record = db.session.execute(db.select(ZelResult).where(
        ZelResult.student_id == current_user.id, ZelResult.subject_id == subject_id,
        ZelResult.term == get_current_term(), ZelResult.session == get_current_session()
    )).scalar()

    if student_subject_record.exam_obj_score is not None:
        flash("You have already written the Objectives paper. Contact admin if you haven't written the exam.")
        return redirect(url_for('term_exam_theory', subject_id=subject_id))
    student_subject_record.exam_obj_score = 0
    db.session.commit()

    return render_template("exams-obj.html", questions=exam_dict, year=this_year, subject_id=subject_id,
                           title=f"{subject.subject_name} Objective Exam", subject=subject, company_name=school_name,
                           filename="assets/img/gcra_logo2.png", exam_duration=exam_duration, exam_weight=exam_weight)


@app.route("/term-exam-t/<subject_id>", methods=["GET", "POST"])
@login_required
def term_exam_theory(subject_id):
    if not current_user.is_authenticated:
        return abort(401)
    student_id = current_user.id
    school_code = student_id[0:3]
    school_name = current_user.school.name
    school_id = current_user.school.id
    student_classroom_id = current_user.classroom_id
    class_grade = db.session.execute(db.select(ZelClassroom).where(ZelClassroom.id == student_classroom_id)).scalar().grade

    today_exam = db.session.execute(db.select(ExamQuestionsTheory).where(
        ExamQuestionsTheory.class_grade == class_grade, ExamQuestionsTheory.subject_id == subject_id,
        ExamQuestionsTheory.school_id == school_id, ExamQuestionsTheory.term == get_current_term(),
        ExamQuestionsTheory.session == get_current_session()
    )).scalar()

    if datetime.strptime(today_exam.exam_date, '%Y-%m-%d').date() != datetime.now().date():
        flash("Exam is not available yet.")
        return redirect(url_for("instructions_gcr", school_code=school_code))

    questions_list = today_exam.question_id
    exam_duration = today_exam.duration
    exam_weight = today_exam.weight

    q_id_int = int(questions_list)
    question = db.session.execute(db.select(QuestionPoolTheory).where(QuestionPoolTheory.id == q_id_int)).scalar()

        # get all questions with the same question background

    subject = db.session.execute(db.select(ZelSubject).where(ZelSubject.id == subject_id)).scalar()

    return render_template("exams-theory.html", question=question, year=this_year, subject_id=int(subject_id),
                           title=f"{subject.subject_name} Theory Exam", subject=subject, company_name=school_name,
                           filename="assets/img/gcra_logo2.png", exam_duration=exam_duration, exam_weight=exam_weight)


@app.route("/gcree/logout")
def logout_gcree():
    logout_user()
    return redirect(url_for('instructions_gcree'))


@app.route("/gcr/logout")
def logout_gcr():
    school_code = current_user.id[0:3].lower()
    logout_user()
    return redirect(url_for('instructions_gcr', school_code=school_code))


@app.route('/gcr/check-result')
@login_required
def check_result_gcr():
    subject_id = request.args.get('subject_id')

    score_calc = db.session.execute(db.select(ZelObjResults).where(
        ZelObjResults.user_id == current_user.id, ZelObjResults.term == get_current_term(),
        ZelObjResults.subject_id == subject_id, ZelObjResults.session == get_current_session()
    )).scalars().all()

    student_score = 0
    for result in score_calc:
        if result.selected_answer == result.correct_answer:
            student_score += 1

    company_name = current_user.school.name

    return render_template("check_result.html", title="Exam Results", company_name=company_name,
                           results=score_calc, score=f'{student_score}', filename="assets/img/gcra_logo2.png")


@app.route("/CTA/delete_question")
@instructor_only
def delete_question():
    q_id = request.args.get("q_id")
    question = db.session.execute(db.select(Questions).where(Questions.id == q_id)).scalar()
    course_code = request.args.get("course_code")
    course = db.session.execute(db.select(Courses).where(Courses.course_code == course_code)).scalar()
    db.session.delete(question)
    db.session.commit()
    return redirect(url_for("view_questions", course_code=course_code))


@app.route("/CTA/reset_score", methods=["GET", "POST"])
@admin_only
def reset_score():
    form = ResetStudentScoreForm()

    if form.validate_on_submit():
        score_id = form.score_id.data
        score = db.session.execute(db.select(Scores).where(Scores.id == score_id)).scalar()
        score.remark = "Retake"
        db.session.commit()
        return redirect(url_for("dashboard"))
    return render_template("login.html", form=form, title="Reset Student Score", year=this_year)


@app.route("/CTA/edit_course", methods=["GET", "POST"])
@admin_only
def edit_course():
    course_code = request.args.get("course_code")
    course = db.session.execute(db.select(Courses).where(Courses.course_code == course_code)).scalar()
    form = CoursesForm(
        course_code=course.course_code,
        course_title=course.course_title,
        course_description=course.course_description,
        instructor_username=course.instructor.username
    )

    if form.validate_on_submit():
        course.course_code = form.course_code.data
        course.course_title = form.course_title.data
        course.course_description = form.course_description.data
        instructor_username = form.instructor_username.data
        instructor = db.session.execute(db.select(User).where(User.username == instructor_username)).scalar()
        course.instructor_id = instructor.id

        db.session.commit()
        return redirect(url_for("dashboard"))
    return render_template("login.html", form=form, title="Edit Course", year=this_year)



@app.route("/sosiec/", methods=["GET", "POST"])
def sosiec_home():
    company_name = "SOSIEC"
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.lower()
        passcode = form.passcode.data
        user = db.session.execute(db.select(User).where(User.username == username)).scalar()
        if not user:
            flash("Incorrect Username. Please try again")
            return redirect(url_for("sosiec_home"))
        elif not check_password_hash(user.passcode, passcode):
            flash("Wrong Passcode. Please enter the correct Passcode")
            return redirect(url_for("sosiec_home"))
        else:
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template("login.html", form=form, title="Login",
                           description="Please enter your login details.", year=this_year, company_name=company_name,
                           filename="assets/img/sosiec_logo.jpg")

if __name__ == '__main__':
    app.run(debug=True)
