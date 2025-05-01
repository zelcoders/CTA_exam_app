from datetime import datetime
import random

from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Float
from werkzeug.security import generate_password_hash, check_password_hash

import requests
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required

from forms import LoginForm, RegisterForm, CoursesForm, ExamQuestionsForm
from smtplib import SMTP_SSL
import os
# from dotenv import load_dotenv
from functools import wraps

'''
Red underlines? Install the required packages first: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from requirements.txt for this project.
'''

app = Flask(__name__)
# load_dotenv(".env")
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')
# os.environ("", "")
zelcoders_password = os.environ.get('ZEL_PASS')
Bootstrap5(app)


login_manager = LoginManager()
login_manager.init_app(app=app)

this_year = datetime.today().year


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

# CREATE DB
class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///exam.db")

db = SQLAlchemy(model_class=Base)

db.init_app(app)


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
    correct_option: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    course_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("courses.id"))

    results = relationship("Results", back_populates="question")
    course = relationship("Courses", back_populates="question")


class Courses(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_code: Mapped[str] = mapped_column(String(200), nullable=False)
    course_title: Mapped[str] = mapped_column(String(500), nullable=False)
    course_description: Mapped[str] = mapped_column(String(1000), unique=True, nullable=True)
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


class Scores(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("user.id"))
    course_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("courses.id"))
    year: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    remark: Mapped[str] = mapped_column(String(50), nullable=False)

    user = relationship("User", back_populates="score")
    course = relationship("Courses", back_populates="score")

with app.app_context():
    db.create_all()


# Create an admin-only decorator
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin = db.session.execute(db.select(User).where(User.user_type == "Admin")).scalar()

        if not admin and f.__name__ == "register":
            return f(*args, **kwargs)
        if not current_user.is_authenticated:
            flash("Your session has timed out. Kindly re-enter your details to login!")
            return redirect(url_for("home"))
        elif current_user.user_type != "Admin":
            return abort(401)
        # Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function


def instructor_only(f):
    @wraps(f)
    def new_decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Your session has timed out. Kindly re-enter your details to login!")
            return redirect(url_for("home"))
        elif current_user.user_type != "Admin":
            if current_user.user_type != "Instructor":
                return abort(401)
        # Otherwise continue with the route function
        return f(*args, **kwargs)
    return new_decorated_function


@app.route("/CTA/", methods=["GET", "POST"])
def home():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.lower()
        passcode = form.passcode.data
        user = db.session.execute(db.select(User).where(User.username == username)).scalar()
        if not user:
            flash("Incorrect Username. Please try again")
            return redirect(url_for("home"))
        elif not check_password_hash(user.passcode, passcode):
            flash("Wrong Passcode. Please enter the correct Passcode")
            return redirect(url_for("home"))
        else:
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template("index.html", form=form, title="Login", description="Please enter your login details.", year=this_year)


# Create register route
@app.route("/CTA/register", methods=["GET", "POST"])
@admin_only
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        surname = form.surname.data.title()
        first_name = form.first_name.data.title()
        username = f"{first_name[0]}{surname}"
        users = db.session.execute(db.select(User).where(User.username.startswith(username))).scalars().all()
        if users:
            username += f"{len(users)}"
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


    return render_template("index.html", form=form, title="Register User", year=this_year)

# make dashboard route require login

@app.route("/CTA/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    # let it load courses to set exams for if the user is an instructor and load courses to write exam if user is a student
    courses = db.session.execute(db.select(Courses)).scalars().all()
    user = db.session.execute(db.select(User).where(User.id == current_user.id)).scalar()

    is_instructor = False
    for course in courses:
        if user.id == course.instructor_id:
            is_instructor = True
            courses = db.session.execute(db.select(Courses).where(course.instructor_id == user.id)).scalars().all()

    return render_template("dashboard.html", courses=courses, user=user, title="Courses", is_instructor=is_instructor, year=this_year)


@app.route("/CTA/add_course", methods=["GET", "POST"])
@admin_only
def add_course():
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


    return render_template("index.html", form=form, title="Register New Course", year=this_year)

# create a route for setting exam questions loading the question form
@app.route("/CTA/set_exam_questions", methods=["GET", "POST"])
@instructor_only
def set_exam():
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

        return redirect(url_for("set_exam"))

    return render_template("index.html", form=form, year=this_year, title=f"{course.course_title} Exam", course=course)


# create a route for loading exam questions for a selected course
@app.route("/CTA/exam", methods=["GET", "POST"])
@login_required
def exam():
    course_code = request.args.get("course_code")
    course = db.session.execute(db.select(Courses).where(Courses.course_code == course_code)).scalar()

    score = db.session.execute(db.select(Scores).where(Scores.course_id == course.id, Scores.user_id == current_user.id, Scores.remark == "Pass")).scalar()

    if score:
        return redirect(url_for('check_result', course_code=course_code))

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

        if results:
            for result in results:
                db.session.delete(result)
                db.session.commit()
            old_score = db.session.execute(db.select(Scores).where(Scores.user_id == user_id, Scores.course_id == course_id)).scalar()
            if old_score:
                db.session.delete(old_score)
                db.session.commit()

        for i in range(len(exam_dict)):
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

        new_score = Scores()
        new_score.user_id = user_id
        new_score.course_id = course_id
        new_score.year = str(this_year)
        new_score.score = student_score
        if student_score > len(exam_questions)/2:
            new_score.remark = "Pass"
        else:
            new_score.remark = "Retake"

        db.session.add(new_score)
        db.session.commit()

        return redirect(url_for('check_result', course_code=course_code))

    return render_template("exams.html", questions=exam_dict, year=this_year, title=f"{course.course_title} Exam", course=course)


@app.route("/CTA/result")
@login_required
def check_result():
    course_code = request.args.get("course_code")
    course = db.session.execute(db.select(Courses).where(Courses.course_code == course_code)).scalar()

    results = db.session.execute(db.select(Results).where(Results.course_id == course.id, Results.user_id == current_user.id)).scalars().all()

    exam_questions = db.session.execute(db.select(Questions).where(Questions.course_id == course.id)).scalars().all()
    score = db.session.execute(db.select(Scores).where(Scores.course_id == course.id, Scores.user_id == current_user.id)).scalar()
    score_percent = round((score.score/len(exam_questions))*100)
    if score_percent > 50:
        remark = "Congratulations! You have passed this course"
    else:
        remark = "Sorry! You scored below the pass mark for this course and you need to rewrite this exam."

    return render_template("result.html", title=f"{course.course_title} Results", results=results, score=score_percent, remark=remark)


@app.route("/CTA/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
