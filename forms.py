from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
            
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class TemplateSelectionForm(FlaskForm):
    template = SelectField('Select Form Template', 
                           choices=[('Biodata', 'Biodata'), 
                                   ('Admission', 'Admission Form'), 
                                   ('Bank Account', 'Bank Account Opening Form')],
                           validators=[DataRequired()])
    submit = SubmitField('Next')

class FormUploadForm(FlaskForm):
    form_file = FileField('Upload Handwritten Form', 
                          validators=[
                              FileRequired(),
                              FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Images and PDF only!')
                          ])
    submit = SubmitField('Upload and Extract')
