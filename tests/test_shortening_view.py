import re
from http import HTTPStatus

import pytest

from tests.conftest import PY_URL, TEST_BASE_URL
from yacut.models import URLMap

CUSTOM_ID = 'py'
INDEX_URL = '/'


def test_index_form_get(client):
    response = client.get(INDEX_URL)
    assert response.status_code == HTTPStatus.OK, (
        'GET-запрос к главной странице должен возвращать статус '
        f'`{HTTPStatus.OK.value}`.'
    )
    assert b'form' in response.data, (
        'Убедитесь, что на главной странице отображается форма.'
    )


def test_index_form_post(client):
    response = client.post(INDEX_URL, data={
        'original_link': PY_URL,
        'custom_id': CUSTOM_ID,
    })
    assert response.status_code == HTTPStatus.OK, (
        'При отправке корректно заполненной формы на главной странице '
        f'должна вернуться ответ со статус-кодом `{HTTPStatus.OK.value}`.'
    )
    url_map_obj = URLMap.query.filter_by(original=PY_URL, short='py').first()
    assert url_map_obj, (
        'После отправки корректно заполненной формы на главной странице '
        'должна быть создана новая запись в базе данных.'
    )
    assert url_map_obj.original == PY_URL, (
        'Убедитесь, что при обработке формы на главной странице '
        'и создании записи в базе данных в поле `original` попадают '
        'корректные данные.'
    )
    assert url_map_obj.short == CUSTOM_ID, (
        'Убедитесь, что если в форме не указана короткая ссылка - '
        'при создании записи в базе данных в поле `short` попадает '
        'значение из формы.'
    )
    expected_link = f'<a href="{TEST_BASE_URL}/{CUSTOM_ID}"'
    assert expected_link in re.sub("'", '"', response.data.decode('utf-8')), (
        'После отправки формы на главной странице должна отобразиться '
        'созданная ссылка.'
    )


def test_duplicated_url_in_form(client, duplicated_custom_id_msg,
                                short_python_url):
    response = client.post(INDEX_URL, data={
        'original_link': PY_URL,
        'custom_id': CUSTOM_ID,
    }, follow_redirects=True)
    assert duplicated_custom_id_msg in response.data.decode('utf-8'), (
        'Если полученный в форме вариант короткой ссылки уже существует - '
        'на главной странице должено отобразиться сообщение '
        f'`{duplicated_custom_id_msg}`'
    )


def test_files_as_a_short_link(client, duplicated_custom_id_msg):
    response = client.post(INDEX_URL, data={
        'original_link': PY_URL,
        'custom_id': 'files',
    }, follow_redirects=True)
    assert duplicated_custom_id_msg in response.data.decode('utf-8'), (
        'При попытке использовать `files` в качестве короткой ссылки - '
        'на главной странице должено отобразиться сообщение '
        f'`{duplicated_custom_id_msg}`'
    )


def test_get_unique_short_id(client):
    asser_msg_pattern = (
        'Если с главной страницы отправлена форма с незаполненным полем для '
        'пользовательского варианта короткой ссылки {}.'
    )
    response = client.post(INDEX_URL, data={
        'original_link': PY_URL,
    })
    assert response.status_code == HTTPStatus.OK, (
        asser_msg_pattern.format(
            f'должен вернуться статус-код {HTTPStatus.OK.value}'
        )
    )
    url_map_object = URLMap.query.filter_by(original=PY_URL).first()
    assert url_map_object, (
        asser_msg_pattern.format(
            'в базе данных должна быть создана новая запись'
        )
    )
    assert url_map_object.short, (
        asser_msg_pattern.format(
            'поле `short` объекта `URLMap` должно быть заполнено автоматически'
        )
    )
    expected_link = f'<a href="{TEST_BASE_URL}/{url_map_object.short}"'
    assert expected_link in re.sub("'", '"', response.data.decode('utf-8')), (
        'После отправки формы на главной странице должна отобразиться '
        'созданная ссылка.'
    )


def test_redirect_url(client, short_python_url):
    response = client.get(f'/{short_python_url.short}')
    assert response.status_code == HTTPStatus.FOUND, (
        'При переходе по короткой ссылке должен вернуться статус-код '
        f'`{HTTPStatus.FOUND.value}`.'
    )
    assert response.location == short_python_url.original, (
        'При переходе по короткой ссылке пользователь должен быть  '
        'перенаправлен на оригинальную страницу.'
    )


def test_len_short_id_form(client):
    assert_msg_pattern = (
        'Если пользовательский вариант короткой ссылки, отправленный в форме '
        'на главной странице, длиннее 16 символов - {}.'
    )
    long_custom_id = 'f' * 17
    response = client.post(INDEX_URL, data={
        'original_link': PY_URL,
        'custom_id': long_custom_id,
    })
    url_map_object = URLMap.query.filter_by(short=long_custom_id).first()
    assert not url_map_object, (
        assert_msg_pattern.format(
            'новая запись в базе данных не должна быть создана'
        )
    )
    posible_link = f'<a href="{TEST_BASE_URL}/long_custom_id"'
    assert (
        posible_link not in re.sub("'", '"', response.data.decode('utf-8'))
    ), (
        assert_msg_pattern.format(
            'короткая ссылка не должна отобразиться на главной странице'
        )
    )


def test_len_short_id_autogenerated_view(client):
    client.post(INDEX_URL, data={
        'original_link': PY_URL,
    })
    unique_id = URLMap.query.filter_by(original=PY_URL).first()
    assert len(unique_id.short) == 6, (
        'Если в отправленной форме не указан пользовательский вариант '
        'короткой ссылки - должно быть сгенерировано значение для поля '
        '`short` объекта `URLMap` длинной в 6 символов.'
    )


@pytest.mark.parametrize('data', [
    ({'url': PY_URL, 'custom_id': '.,/!?'}),
    ({'url': PY_URL, 'custom_id': 'Hodor-Hodor'}),
    ({'url': PY_URL, 'custom_id': 'h@k$r'}),
    ({'url': PY_URL, 'custom_id': '$'}),
])
def test_invalid_short_url(data, client):
    client.post(INDEX_URL, data=data)
    url_map_object = URLMap.query.filter_by(original=PY_URL).first()
    assert not url_map_object, (
        'Если пользовательский вариант которкой ссылки, отправленный через '
        'форму на главной странице содержит недопустымые символы - '
        'новая запись в базе данных не должна быть создана.\n'
        'Допустимы только латинские буквы (верхнего и нижнего регистра) '
        'и цифры.'
    )
