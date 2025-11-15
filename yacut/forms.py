from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileRequired, MultipleFileField
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class URLForm(FlaskForm):
    original_link = StringField(
        'Поле для длинной исходной ссылки',
        validators=[DataRequired(message='Обязательное поле')]
    )
    custom_id = StringField(
        'Поле для короткой ссылки',
        validators=[
            Length(
                max=16, message='ссылка не должна превышать 16 символов'
            ),
            Optional()
        ]
    )
    submit = SubmitField('Создать')


class FileLoad(FlaskForm):
    files = MultipleFileField(
        'Выберите файлы',
        validators=[
            FileRequired(message='Выберите файл'),
            FileAllowed(['jpg', 'png', 'pdf', 'doc', 'docx'])
        ]
    )
    submit = SubmitField('Отправить')
