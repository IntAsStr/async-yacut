import string

from flask import jsonify, request, url_for

from . import app, db
from .models import URLMap
from .views import get_unique_short_id


@app.route('/api/id/', methods=['POST'])
def api_urlview():
    """Функция для создания короткой ссылки"""
    if not request.get_data():
        return jsonify({'message': 'Отсутствует тело запроса'}), 400

    if not request.is_json:
        return jsonify({
            'message': 'Content-Type должен быть application/json'
        }), 400

    data = request.get_json()

    if data is None:
        return jsonify({'message': 'Отсутствует тело запроса'}), 400

    if 'url' not in data:
        return jsonify({'message': '"url" является обязательным полем!'}), 400

    original_url = data.get('url')
    custom_id = data.get('custom_id')

    if not original_url:
        return jsonify({'message': '"url" является обязательным полем!'}), 400

    if custom_id == "" or custom_id is None:
        custom_id = None
    else:
        custom_id = custom_id
        if not custom_id:
            custom_id = None
        else:
            if len(custom_id) > 16:
                return jsonify({
                    'message': 'Указано недопустимое имя для короткой ссылки'
                }), 400

            # ПРОВЕРКА НА ДОПУСТИМЫЕ СИМВОЛЫ - ТОЛЬКО ЛАТИНИЦА И ЦИФРЫ
            allowed_chars = string.ascii_letters + string.digits
            if not all(char in allowed_chars for char in custom_id):
                return jsonify({
                    'message': 'Указано недопустимое имя для короткой ссылки'
                }), 400

            if not URLMap.is_short_unique(custom_id):
                error_message = (
                    'Предложенный вариант короткой ссылки уже существует.'
                )
                return jsonify({'message': error_message}), 400

    short_id = custom_id if custom_id else get_unique_short_id()

    try:
        urlmap = URLMap(original=original_url, short=short_id)
        db.session.add(urlmap)
        db.session.commit()

        short_url = url_for(
            'redirect_to_original', short_id=short_id, _external=True
        )

        return jsonify({
            'short_link': short_url,
            'url': original_url
        }), 201

    except Exception:
        db.session.rollback()
        return jsonify({
            'message': 'Произошла ошибка при создании ссылки'
        }), 500


@app.route('/api/id/<short_id>/', methods=['GET'])
def get_original_url(short_id):
    data = URLMap.get_by_short(short_id)
    if not data:
        return jsonify({
            'message': 'Указанный id не найден'
        }), 404
    return jsonify({'url': data.original})
