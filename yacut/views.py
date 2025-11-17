import random
from io import BytesIO

import requests
from flask import flash, redirect, render_template, send_file, url_for

from . import app, db
from .forms import FileLoad, URLForm
from .models import URLMap
from .yandex_disk import get_download_link, upload_yandex_disk


def is_short_unique(short):
    """Проверка уникальности короткой ссылки"""
    return URLMap.query.filter_by(short=short).count() == 0


def get_by_short(short_id):
    """Получение URL по короткому идентификатору"""
    return URLMap.query.filter_by(short=short_id).first()


def get_unique_short_id():
    characters = app.config['ALLOWED_SHORT_ID_CHARS']
    max_attempts = app.config['MAX_ATTEMPS']
    length = app.config['SHORT_ID_LENGTH']

    for _ in range(max_attempts):
        short_id = ''.join(random.choices(characters, k=length))
        if not URLMap.query.filter_by(short=short_id).first():
            return short_id
    return ''.join(random.choices(characters, k=length + 2))


def is_short_available(short):
    if short == 'files':
        return False
    return not URLMap.query.filter_by(short=short).first()


@app.route('/', methods=['GET', 'POST'])
def index_view():
    form = URLForm()
    short_url = None
    if not form.validate_on_submit():
        return render_template('index.html', form=form, short_url=short_url)

    original = form.original_link.data
    custom_short = form.custom_id.data if form.custom_id.data else ''
    if custom_short != '':
        if not is_short_available(custom_short):
            flash(
                'Предложенный вариант короткой ссылки уже существует.',
                'error'
            )
            return render_template('index.html', form=form)
        short = custom_short
    else:
        short = get_unique_short_id()
    urlmap = URLMap(
        original=original,
        short=short
    )
    db.session.add(urlmap)
    db.session.commit()

    short_url = url_for(
        'redirect_to_original', short_id=short, _external=True
    )
    flash('Ваша новая ссылка готова!', 'success')
    return render_template('index.html', form=form, short_url=short_url)


@app.route('/<short_id>')
def redirect_to_original(short_id):
    """Редирект по короткой ссылке на оригинальный URL"""
    url_map = URLMap.query.filter_by(short=short_id).first_or_404()
    return redirect(url_map.original)


@app.route('/download/<short_id>')
def download_file(short_id):
    url_map = URLMap.query.filter_by(short=short_id).first_or_404()

    response = requests.get(url_map.original, timeout=30)
    response.raise_for_status()

    filename = 'file'
    content_disposition = response.headers.get('Content-Disposition')
    if content_disposition and 'filename=' in content_disposition:
        filename = content_disposition.split('filename=')[1].strip('"')
    elif 'filename=' in url_map.original:
        filename = url_map.original.split('filename=')[1].split('&')[0]

    file_obj = BytesIO(response.content)
    return send_file(
        file_obj,
        as_attachment=True,
        download_name=filename,
        mimetype=response.headers.get(
            'Content-Type', 'application/octet-stream'
        )
    )


@app.route('/files', methods=['GET', 'POST'])
async def file_load():
    form = FileLoad()
    file_links = []
    if not form.validate_on_submit():
        return render_template('files.html', form=form, file_links=file_links)

    files = form.files.data

    for file in files:
        file_path = await upload_yandex_disk(file)
        download_url = await get_download_link(file_path)
        short_id = get_unique_short_id()
        urlmap = URLMap(
            original=download_url,
            short=short_id
        )
        db.session.add(urlmap)
        db.session.commit()

        file_links.append({
            'filename': file.filename,
            'short_url': url_for(
                'download_file', short_id=short_id, _external=True
            ),
            'debug_url': download_url
        })
        flash(f'Файл {file.filename} успешно загружен!', 'success')
    return render_template('files.html', form=form, file_links=file_links)
