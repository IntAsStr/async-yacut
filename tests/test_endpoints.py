import pytest
from http import HTTPStatus

from tests.conftest import PY_URL, TEST_BASE_URL
from yacut.models import URLMap

CREATE_SHORT_LINK_URL = '/api/id/'
GET_ORIGINAL_LINK_URL = '/api/id/{short_id}/'
VALIDATION_ERROR_KEY = 'message'


def test_create_id(client):
    request_short_link = 'py'
    response = client.post(CREATE_SHORT_LINK_URL, json={
        'url': PY_URL,
        'custom_id': request_short_link,
    })
    assert response.status_code == HTTPStatus.CREATED, (
        f'POST-запрос на создание короткой ссылки к эндпоинту '
        f'`{CREATE_SHORT_LINK_URL}` с корректными данными должен вернуть '
        f'ответ со статус-кодом {HTTPStatus.CREATED.value}.'
    )
    expected_response = {
        'url': PY_URL,
        'short_link': f'{TEST_BASE_URL}/{request_short_link}'
    }
    assert response.json.keys() == expected_response.keys(), (
        f'Ответ на валидный POST-запрос к эндпоинту `{CREATE_SHORT_LINK_URL}` '
        'должен содержать ключи `url`, `short_link`.'
    )
    for key in expected_response:
        assert response.json.get(key) == expected_response[key], (
            f'Значение ключа `{key}` в ответе на POST-запрос к эндпоинту '
            f'`{CREATE_SHORT_LINK_URL}` отличается от ожидаемого.'
        )


def test_create_empty_body(client):
    response = client.post(CREATE_SHORT_LINK_URL,
                           content_type='application/json')
    assert response.status_code == HTTPStatus.BAD_REQUEST, (
        f'В ответ на пустой POST-запрос к эндпоинту `{CREATE_SHORT_LINK_URL}` '
        f'должен вернуться ответ статус-кодом {HTTPStatus.BAD_REQUEST.value}.'
    )
    assert response.json, (
        f'Ответ на POST-запрос к эндпоинту `{CREATE_SHORT_LINK_URL}`, '
        'не содержащий тело запроса, должен быть быть в формате JSON.'
    )
    expected_response = {VALIDATION_ERROR_KEY: 'Отсутствует тело запроса'}
    assert response.json.keys() == expected_response.keys(), (
        'В ответе на пустой POST-запрос к эндпоинту '
        f'`{CREATE_SHORT_LINK_URL}` должен содержать единственный ключ '
        f'`{VALIDATION_ERROR_KEY}`.'
    )
    assert response.json == expected_response, (
        f'Отевт на пустой POST-запрос к эндпоинту {CREATE_SHORT_LINK_URL} '
        'не соответствует спецификации.'
    )


@pytest.mark.parametrize('json_data', [
    ({'url': PY_URL, 'custom_id': '.,/!?'}),
    ({'url': PY_URL, 'custom_id': 'Hodor-Hodor'}),
    ({'url': PY_URL, 'custom_id': 'h@k$r'}),
    ({'url': PY_URL, 'custom_id': '$'}),
    ({'url': PY_URL, 'custom_id': 'п'}),
    ({'url': PY_URL, 'custom_id': 'l l'}),
])
def test_invalid_short_url(json_data, client):
    response = client.post(CREATE_SHORT_LINK_URL, json=json_data)
    assert response.status_code == HTTPStatus.BAD_REQUEST, (
        f'Если POST-запрос к эндпоинту `{CREATE_SHORT_LINK_URL}` содержит '
        'некоррекнтое значение для поля `custom_id`, должен вернуться '
        f'ответ со статус-кодом {HTTPStatus.BAD_REQUEST.value}.\n'
        'Для данного поля допустимо использование только латинских букв '
        '(верхнего и нижнего регистра) и цифр.'
    )
    expected_response = {
        VALIDATION_ERROR_KEY: 'Указано недопустимое имя для короткой ссылки'
    }
    assert response.json.keys() == expected_response.keys(), (
        f'Ответ на POST-запроса к эндпоинту `{CREATE_SHORT_LINK_URL}` с '
        'некорректным значением для поля `custom_id` должен содержать '
        f'единственный ключ `{VALIDATION_ERROR_KEY}`.'
    )
    assert response.json == expected_response, (
        f'Ответ на POST-запроса к эндпоинту `{CREATE_SHORT_LINK_URL}` с '
        'некорректным значением для поля `custom_id` не соответствует '
        'спецификации.'
    )
    url_map_obj = URLMap.query.filter_by(original=PY_URL).first()
    assert not url_map_obj, (
        f'POST-запрос к эндпоинту `{CREATE_SHORT_LINK_URL}` с некорректным '
        'значением для поля `custom_id` не должен создавать новую запись в '
        'базе данных.'
    )


def test_no_required_field(client):
    try:
        response = client.post(CREATE_SHORT_LINK_URL, json={
            'short_link': 'python',
        })
    except Exception as exc:
        raise AssertionError(
            f'POST-запрос к эндпоинту `{CREATE_SHORT_LINK_URL}` без '
            'обязательного поля `url` вызывает исключение: '
            f'`{type(exc).__name__}: {exc}`.\n'
            'Обработайте исключение и верните ответ со статус-кодом '
            f'{HTTPStatus.BAD_REQUEST.value}.'
        )
    assert response.status_code == HTTPStatus.BAD_REQUEST, (
        f'Если тело POST-запроса к эндпоинту `{CREATE_SHORT_LINK_URL}` '
        'отличается от ожидаемого - верните ответ со статус-кодом '
        f'{HTTPStatus.BAD_REQUEST.value}.'
    )
    expected_response = {
        VALIDATION_ERROR_KEY: '"url" является обязательным полем!',
    }
    assert response.json.keys() == expected_response.keys(), (
        f'Если в запросе к эндпоинту `{CREATE_SHORT_LINK_URL}` отсутствует '
        'обяазательное поле `url`, должен вернуться ответ, содержащий '
        f'ключ `{VALIDATION_ERROR_KEY}`.'
    )
    assert response.json == expected_response, (
        f'Ответ на запрос к эндпоинту {CREATE_SHORT_LINK_URL} не '
        'соответствует спецификации.'
    )


def test_url_already_exists(client, short_python_url,
                            duplicated_custom_id_msg):
    try:
        response = client.post(CREATE_SHORT_LINK_URL, json={
            'url': short_python_url.original,
            'custom_id': short_python_url.short,
        })
    except Exception as exc:
        raise AssertionError(
            f'POST-запрос к эндпоинту `{CREATE_SHORT_LINK_URL}` с '
            'занятым значением для поля `custom_id` вызывает исключение: '
            f'`{type(exc).__name__}: {exc}`.\n'
            'Обработайте исключение и верните ответ со статус-кодом '
            f'{HTTPStatus.BAD_REQUEST.value}.'
        )
    assert response.status_code == HTTPStatus.BAD_REQUEST, (
        f'POST-запрос к эндпоинту `{CREATE_SHORT_LINK_URL}` с '
        'занятым значением для поля `custom_id` должен вернуться ответ '
        f'со статус-кодом {HTTPStatus.BAD_REQUEST.value}.'
    )
    expected_response = {VALIDATION_ERROR_KEY: duplicated_custom_id_msg}
    assert response.json.keys() == expected_response.keys(), (
        f'Ответ на POST-запрос к эндпоинту `{CREATE_SHORT_LINK_URL}` с '
        'уже существующим значением для поля `custom_id` должен содержать '
        f'ключ `{VALIDATION_ERROR_KEY}`.'
    )
    assert response.json == expected_response, (
        f'Ответ на POST-запрос к эндпоинту `{CREATE_SHORT_LINK_URL}` с '
        'уже существующим значением для поля `custom_id` не соответствует '
        'спецификации.'
    )


@pytest.mark.parametrize('json_data', [
    ({'url': PY_URL}),
    ({'url': PY_URL, 'custom_id': ''}),
])
def test_generated_unique_short_id(json_data, client):
    assert_msg_pattern = (
        f'POST-запрос к эндпоинту `{CREATE_SHORT_LINK_URL}` без указания '
        'поля `custom_id` либо пустой строкой в качестве значения для поля '
        '`custom_id` {}.'
    )
    try:
        response = client.post(CREATE_SHORT_LINK_URL, json=json_data)
    except Exception as exc:
        raise AssertionError(
            assert_msg_pattern.format(
                f'вызывает исключение: `{type(exc).__name__}: {exc}`.'
            )
        )
    assert response.status_code == HTTPStatus.CREATED, (
        assert_msg_pattern.format(
            'должен вернуться ответ со статус-кодом '
            f'{HTTPStatus.CREATED.value}.'
        )
    )
    unique_id = URLMap.query.filter_by(original=PY_URL).first()
    assert unique_id, (
        f'Если POST-запрос к эндпоинту `{CREATE_SHORT_LINK_URL}` не '
        'содержит данных для поля `custom_id`, которкая ссылка должна '
        'быть сгенерирована автоматически и сохранена в базе данных.'
    )
    expected_response = {
        'url': PY_URL,
        'short_link': f'{TEST_BASE_URL}/{unique_id.short}',
    }
    assert response.json.keys() == expected_response.keys(), (
        f'Ключи в ответе на POST-запрос к эндпоинту `{CREATE_SHORT_LINK_URL}` '
        'отличаются от предусмотренных спецификацией.'
    )
    for key in expected_response:
        assert response.json.get(key) == expected_response[key], (
            f'Значение ключа `{key}` в ответе на POST-запрос к эндпоинту '
            f'`{CREATE_SHORT_LINK_URL}` отличается от ожидаемого.'
        )


def test_get_url_endpoint(client, short_python_url):
    response = client.get(
        GET_ORIGINAL_LINK_URL.format(short_id=short_python_url.short)
    )
    assert response.status_code == HTTPStatus.OK, (
        f'GET-запрос к эндпоинту `{GET_ORIGINAL_LINK_URL}` должен вернуть '
        f'ответ со статус-кодом {HTTPStatus.OK.value}.'
    )
    expected_key = 'url'
    expected_response = {expected_key: PY_URL}
    assert response.json.keys() == expected_response.keys(), (
        f'Ответ на GET-запрос к эндпоинту `{GET_ORIGINAL_LINK_URL}` должен '
        f'содержать ключ `{expected_key}`.'
    )
    assert response.json[expected_key] == expected_response[expected_key], (
        f'Ключ `{expected_key}` в ответе на GET-запрос к эндпоинту '
        f'`{GET_ORIGINAL_LINK_URL}` содержит значение, отличное от ожидаемого.'
    )


def test_get_url_not_found(client):
    assert_msg_pattern = (
        f'GET-запрос к эндпоинту `{GET_ORIGINAL_LINK_URL}` с несуществующим '
        '`short_id` {}.'
    )
    response = client.get(
        GET_ORIGINAL_LINK_URL.format(short_id='does_not_exist')
    )
    assert response.status_code == HTTPStatus.NOT_FOUND, (
        f'GET-запрос к эндпоинту `{GET_ORIGINAL_LINK_URL}` с несуществующим '
        '`short_id` должен вернуть ответ со статус-кодом '
        f'{HTTPStatus.NOT_FOUND.value}.'
    )
    expected_response = {VALIDATION_ERROR_KEY: 'Указанный id не найден'}
    assert response.json.keys() == expected_response.keys(), (
        assert_msg_pattern.format(
            f'должен содержать ключ `{VALIDATION_ERROR_KEY}`.'
        )
    )
    assert response.json == expected_response, (
        'Ответ на ' + assert_msg_pattern.format(
            'не соответствует спецификации.'
        )
    )


def test_len_short_id_api(client):
    assert_msg_pattern = (
        f'Если при POST-запросе к эндпоинту `{CREATE_SHORT_LINK_URL}` '
        'содержит значение для поля `custom_id` длиннее 16 символов - '
    )
    long_custom_id = 'f' * 17
    response = client.post(CREATE_SHORT_LINK_URL, json={
        'url': PY_URL,
        'custom_id': long_custom_id,
    })
    assert response.status_code == HTTPStatus.BAD_REQUEST, (
        assert_msg_pattern.format(
            'должен вернуться ответ со статус-кодом '
            f'{HTTPStatus.BAD_REQUEST.value}.'
        )
    )
    expected_response = {
        VALIDATION_ERROR_KEY: 'Указано недопустимое имя для короткой ссылки'
    }
    assert response.json.keys() == expected_response.keys(), (
        assert_msg_pattern.format(
            f'в ответе должен быть ключ `{VALIDATION_ERROR_KEY}`.'
        )
    )
    assert response.json == expected_response, (
        f'Ответ на POST-запрос к эндпоинту `{CREATE_SHORT_LINK_URL}` со '
        'значением для поля `custom_id` длиннее 16 символов не соответствует '
        'спецификации.'
    )


def test_len_short_id_autogenerated_api(client):
    client.post(CREATE_SHORT_LINK_URL, json={
        'url': PY_URL,
    })
    url_map_obj = URLMap.query.filter_by(original=PY_URL).first()
    assert url_map_obj, (
        f'Корректный POST-запрос к эндпоинту `{CREATE_SHORT_LINK_URL}` '
        'должен создавать новую запись в базе данных.'
    )
    assert len(url_map_obj.short) == 6, (
        f'Если POST-запрос к эндпоинту `{CREATE_SHORT_LINK_URL}` не '
        'содержит значение для поля `custom_id`, при создании нового объекта '
        'в базе данных должна генерироваться короткая ссылка длинной 6 '
        'символов.'
    )
