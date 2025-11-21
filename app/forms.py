from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField

class NameForm(FlaskForm):
    name = StringField('Enter your name')
    submit = SubmitField('Submit')