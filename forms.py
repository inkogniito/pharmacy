from flask_wtf import FlaskForm
from wtforms import FloatField,  StringField, PasswordField, SelectField, SubmitField, IntegerField, FileField, TextAreaField
from wtforms.validators import DataRequired, Length, Regexp, NumberRange


class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(),
        Length(min=5, max=100),
        Regexp(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$',
               message="Некорректный адрес электронной почты.")
    ])

    password = PasswordField('Пароль', validators=[
        DataRequired(),
        Length(min=8, max=128),
        Regexp(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?!.*\s)[A-Za-z\d~!?@#$%^&*_\-+()[\]{}><\\/|"\'.,:;]+$',
               message="Пароль должен содержать хотя бы одну заглавную букву, одну строчную букву и одну цифру.")
    ])

    name = StringField('Имя', validators=[DataRequired()])
    
    phone = StringField('Номер телефона', validators=[
        DataRequired(),
        Length(min=10, max=15),
        Regexp(r'^\+?[0-9]*$', message="Номер телефона должен содержать только цифры и, возможно, знак '+' в начале.")
    ])
    
    role_id = 3  # SelectField('Роль', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Зарегистрироваться')

class DrugForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    description = TextAreaField('Описание', validators=[DataRequired()])
    price = FloatField('Цена', validators=[DataRequired(), NumberRange(min=0, message="Цена должна быть положительной.")])
    stock = IntegerField('Количество на складе', validators=[DataRequired(), NumberRange(min=0, message="Количество должно быть неотрицательным.")])
    category_id = SelectField('Категория', coerce=int, validators=[DataRequired()])
    images = FileField('Изображение препарата', validators=[DataRequired()])
    submit = SubmitField('Сохранить')


class EditDrugForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    description = TextAreaField('Описание', validators=[DataRequired()])
    price = FloatField('Цена', validators=[DataRequired(), NumberRange(min=0, message="Цена должна быть положительной.")])
    stock = IntegerField('Количество на складе', validators=[DataRequired(), NumberRange(min=0, message="Количество должно быть неотрицательным.")])
    category_id = SelectField('Категория', coerce=int, validators=[DataRequired()])
    images = FileField('Изображение препарата')
    submit = SubmitField('Сохранить')




