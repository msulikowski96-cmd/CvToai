from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, TextAreaField, FileField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from flask_wtf.file import FileAllowed, FileRequired
from models import User

class LoginForm(FlaskForm):
    username_or_email = StringField('Nick lub Email', validators=[DataRequired()])
    password = PasswordField('Hasło', validators=[DataRequired()])
    remember_me = BooleanField('Zapamiętaj mnie')
    submit = SubmitField('Zaloguj się')

class RegisterForm(FlaskForm):
    first_name = StringField('Imię', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Nazwisko', validators=[DataRequired(), Length(min=2, max=50)])
    username = StringField('Nick', validators=[DataRequired(), Length(min=3, max=20)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Hasło', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Potwierdź hasło', validators=[
        DataRequired(), EqualTo('password', message='Hasła muszą być identyczne')
    ])
    submit = SubmitField('Zarejestruj się')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Ten nick jest już zajęty. Wybierz inny.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Ten email jest już zarejestrowany. Użyj innego.')

class CVUploadForm(FlaskForm):
    job_title = StringField('Nazwa stanowiska', validators=[DataRequired(), Length(min=2, max=200)])
    job_description = TextAreaField('Opis stanowiska / Ogłoszenie')
    cv_file = FileField('Plik CV (PDF)', validators=[
        FileRequired(), 
        FileAllowed(['pdf'], 'Dozwolone tylko pliki PDF!')
    ])
    submit = SubmitField('Zoptymalizuj CV')

class ProfileForm(FlaskForm):
    first_name = StringField('Imię', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Nazwisko', validators=[Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    username = StringField('Nazwa użytkownika', validators=[DataRequired(), Length(min=3, max=20)])
    current_password = PasswordField('Obecne hasło')
    new_password = PasswordField('Nowe hasło', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Potwierdź hasło', validators=[
        EqualTo('new_password', message='Hasła muszą być identyczne')
    ])
    submit = SubmitField('Zapisz zmiany')