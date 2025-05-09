from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, IntegerField
from wtforms.fields.choices import RadioField
from wtforms.fields.simple import PasswordField
from wtforms.validators import DataRequired, Length


class RegisterForm(FlaskForm):
    surname = StringField("Surname", validators=[DataRequired()])
    first_name = StringField("First Name", validators=[DataRequired()])
    branch = SelectField("Church branch", choices=["", "Abuja", "Ajipowo", "Ikere Ekiti", "Lagos", "Igoba", "Headquaters", "Ado"], validate_choice=True)
    user_type = SelectField("Users", choices=[("Student", "Student"), ("Instructor", "Instructor"), ("Admin", "Admin")], validate_choice=True)
    submit = SubmitField("Submit")


class ExamQuestionsForm(FlaskForm):
   questions = StringField("Question", validators=[DataRequired()])
   correct_answer = StringField("Enter Correct Option", validators=[DataRequired()])
   wrong_answer1 = StringField("Enter Wrong Option", validators=[DataRequired()])
   wrong_answer2 = StringField("Enter Wrong Option")
   wrong_answer3 = StringField("Enter Wrong Option")
   wrong_answer4 = StringField("Enter Wrong Option")
   submit = SubmitField("Upload Questions")


class CoursesForm(FlaskForm):
    course_code = StringField("Course Code", validators=[DataRequired()])
    course_title = StringField("Course Title", validators=[DataRequired()])
    course_description = StringField("Course Description")
    instructor_username = StringField("Enter Instructor Username")
    submit = SubmitField("Submit")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    passcode = PasswordField("Passcode", validators=[DataRequired(), Length(min=6, max=6, message="Your Passcode must be 6 digit")])
    submit = SubmitField("Submit")


class ResetStudentScoreForm(FlaskForm):
    score_id = IntegerField("Score ID", validators=[DataRequired()])
    submit = SubmitField("Reset")

