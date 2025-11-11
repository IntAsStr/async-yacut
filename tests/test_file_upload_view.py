import asyncio
from http import HTTPStatus
from io import BytesIO

from tests.conftest import generate_png_bytes, TEST_BASE_URL
from tests.yandex_disk_mock_server import (
    COMMON_ASSERT_MSG_FOR_UPLOAD_FILES, intercept_requests
)

FILES_URL = '/files'
EXPECTED_API_CALLS = {
    'get_upload_link',
    'upload',
    'get_download_link'
}


def test_files_upload_page_available(client):
    response = client.get(FILES_URL)
    assert response.status_code == HTTPStatus.OK, (
        'Убедитесь, что GET-запрос к странице загрузки файлов '
        f'(`{FILES_URL}`) возвращает статус {HTTPStatus.OK.value}.'
    )


def test_files_upload_page_has_form(client):
    response = client.get(FILES_URL)
    assert b'form' in response.data, (
        'Убедитесь, что на странице загрузки файлов отображается форма.'
    )


def test_files_upload_page_form_fields(client):
    response = client.get(FILES_URL)
    assert b'type="file"' in response.data, (
        'Убедитесь, что на странице загрузки файлов отображается поле '
        'для выбора файлов (`type="file"`).'
    )
    assert b'type="submit"' in response.data, (
        'Убедитесь, что на странице загрузки файлов отображается кнопка '
        'отправки формы (`type="submit"`).'
    )


async def test_upload_files(client, mock_server, monkeypatch):
    mock_server, user_calls = await mock_server
    await intercept_requests(mock_server, monkeypatch)
    png_bytes_1 = generate_png_bytes()
    png_bytes_2 = generate_png_bytes()
    form_data = {
        'files': [
            (BytesIO(png_bytes_1), 'картинка 1.png'),
            (BytesIO(png_bytes_2), 'картинка 2.png')
        ]
    }

    def sync_test():
        response = client.post(FILES_URL, data=form_data)
        assert response.status_code == HTTPStatus.OK, (
            'Убедитесь, что при отправке корректно заполненной формы для '
            f'загрузки файлов со страницы `{FILES_URL}` возвращается статус '
            f'{HTTPStatus.OK.value}.'
        )
        file_names = [name for _, name in form_data['files']]
        mocked_yadisk_direct_link_domain = (
            f'http://{mock_server.host}:{mock_server.port}'
        )
        response_data = response.data.decode('utf-8')
        assert mocked_yadisk_direct_link_domain not in response_data, (
            'Убедитесь, что после успешной загрузки файлов '
            f'на странице `{FILES_URL}` не отображаются прямые ссылки '
            'на файлы, полученные от API Яндекс Диска. Ссылки на файлы должны '
            'быть сокращены с использованием сервиса для генерации коротких '
            'ссылок.'
        )
        assert TEST_BASE_URL in response_data, (
            'Убедитесь, что после отправки корректно заполненной формы для '
            f'загрузки файлов на странице `{FILES_URL}` выводятся ссылки на '
            'загруженные файлы.'
        )
        assert all(
            [name in response_data for name in file_names]
        ), (
            'Убедитесь, что после отправки корректно заполненной формы для '
            f'загрузки файлов на странице `{FILES_URL}` выводятся названия '
            'всех загруженных файлов.'
        )
        assert not (EXPECTED_API_CALLS - user_calls), (
            COMMON_ASSERT_MSG_FOR_UPLOAD_FILES
        )

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, sync_test)
