import aiohttp
import requests
import random
import string
import urllib

from io import BytesIO
from flask import abort, flash, redirect, render_template, url_for, current_app, send_file
from . import app, db
from .models import URLMap
from .forms import URLForm, FileLoad


def get_unique_short_id(length=6):
    characters = string.ascii_letters + string.digits
    max_attempts = 10

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
    if form.validate_on_submit():
        original = form.original_link.data
        custom_short = form.custom_id.data if form.custom_id.data else ""
        if custom_short != "":
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


async def upload_yandex_disk(file):
    """Асинхронная загрузка файла на Яндекс.Диск"""
    token = current_app.config['YANDEX_DISK_TOKEN']
    upload_url = current_app.config['UPLOAD_URL']
    headers = {'Authorization': f'OAuth {token}'}
    params = {
        'path': f'app:/{file.filename}', 'overwrite': 'true', 'fields': 'href'
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(
            upload_url, headers=headers, params=params
        ) as response:
            upload_data = await response.json()
            put_url = upload_data['href']

        async with session.put(put_url, data=file.read()) as response:
            location = response.headers.get('Location')
            if location:
                location = urllib.parse.unquote(location)
                location = location.replace('/disk', '')
                return location
            else:
                raise Exception("Не удалось получить расположение файла")


async def get_download_link(file_path):
    """Получает публичную ссылку для скачивания файла"""
    token = current_app.config['YANDEX_DISK_TOKEN']
    download_url = 'https://cloud-api.yandex.net/v1/disk/resources/download'
    headers = {'Authorization': f'OAuth {token}'}
    params = {'path': file_path}

    async with aiohttp.ClientSession() as session:
        async with session.get(
            download_url, headers=headers, params=params
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data['href']  # Ссылка для скачивания
            else:
                error_text = await response.text()
                raise Exception(
                    f"Ошибка получения ссылки: {response.status}: {error_text}"
                )


@app.route('/download/<short_id>')
def download_file(short_id):
    url_map = URLMap.query.filter_by(short=short_id).first_or_404()

    try:
        response = requests.get(url_map.original, timeout=30)
        response.raise_for_status()

        filename = "file"
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

    except Exception as e:
        print(f"Ошибка при скачивании: {e}")
        flash('Ошибка при скачивании файла', 'error')
        return redirect(url_for('file_load'))


@app.route('/files', methods=['GET', 'POST'])
async def file_load():
    form = FileLoad()
    file_links = []
    if form.validate_on_submit():
        files = form.files.data

        for file in files:
            file_path = await upload_yandex_disk(file)
            download_url = await get_download_link(file_path)
            print(f"Download URL: {download_url}")
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
