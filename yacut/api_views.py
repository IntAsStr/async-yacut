from flask import jsonify, request, url_for
from http import HTTPStatus

from . import app, db
from .models import URLMap
from .views import get_unique_short_id, is_short_available, get_by_short


@app.route('/api/id/', methods=['POST'])
def api_urlview():
    """Создание короткой ссылки"""
    if not request.get_data() or not request.is_json:
        return jsonify({
            'message': 'Отсутствует тело запроса'
        }), HTTPStatus.BAD_REQUEST

    data = request.get_json()
    if not data or 'url' not in data or not data['url']:
        return jsonify({
            'message': '"url" является обязательным полем!'
        }), HTTPStatus.BAD_REQUEST

    original_url, custom_id = data['url'], data.get('custom_id')

    short_id = get_validated_short_id(custom_id)
    if isinstance(short_id, tuple):
        return short_id

    try:
        urlmap = URLMap(original=original_url, short=short_id)
        db.session.add(urlmap)
        db.session.commit()
        short_url = url_for(
            'redirect_to_original', short_id=short_id, _external=True
        )
        return jsonify({
            'short_link': short_url, 'url': original_url
        }), HTTPStatus.CREATED
    except Exception:
        db.session.rollback()
        return jsonify({
            'message': 'Произошла ошибка при создании ссылки'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


def get_validated_short_id(custom_id):
    """Валидация и генерация short_id"""
    if not custom_id or not custom_id.strip():
        return get_unique_short_id()

    custom_id = custom_id.strip()
    if len(custom_id) > app.config['MAX_CUSTOM_ID_LENGTH']:
        return jsonify({
            'message': 'Указано недопустимое имя для короткой ссылки'
        }), HTTPStatus.BAD_REQUEST

    allowed_chars = app.config['ALLOWED_SHORT_ID_CHARS']
    if not all(character in allowed_chars for character in custom_id):
        return jsonify({
            'message': 'Указано недопустимое имя для короткой ссылки'
        }), HTTPStatus.BAD_REQUEST

    if not is_short_available(custom_id):
        msg = 'Предложенный вариант короткой ссылки уже существует.'
        return jsonify({'message': msg}), HTTPStatus.BAD_REQUEST

    return custom_id


@app.route('/api/id/<short_id>/', methods=['GET'])
def get_original_url(short_id):
    data = get_by_short(short_id)
    if not data:
        return jsonify({
            'message': 'Указанный id не найден'
        }), HTTPStatus.NOT_FOUND
    return jsonify({'url': data.original}), HTTPStatus.OK
