import aiohttp
import re
from contextlib import suppress
from hashlib import md5
from urllib.parse import unquote, quote

import pytest
from aiohttp import web

REQUEST_UPLOAD_URL = '/v1/disk/resources/upload'
UPLOAD_URL = '/upload-target'
DOWNLOAD_LINK_URL = '/v1/disk/resources/download'

COMMON_ASSERT_MSG_FOR_UPLOAD_FILES = (
    'Убедитесь, что для загрузки полученных файлов на Яндекс Диск `'
    'используется такая последовательность запросов к API Диска:\n'
    f'1. GET-запрос к эндпоинту `{REQUEST_UPLOAD_URL}` для получения '
    'ссылки для загрузки файла;\n'
    f'2. PUT-запрос к эндпоинту `{UPLOAD_URL}` для загрузки файла;\n'
    f'3. GET-запрос к эндпоинту `{DOWNLOAD_LINK_URL}` для получения '
    'ссылки для скачивания файла.'
)


@pytest.fixture
async def mock_server(aiohttp_server):
    """Возвращает мок-сервер для проверки работы с API Я.Диска."""
    user_calls = set()
    file_names = {}

    async def check_headers(path, headers):
        assert 'Authorization' in headers, (
            'Убедитесь, что в запросе к эндпоинту Яндекс Диска '
            f'`{path}` передаётся заголовок `Authorization` с токеном доступа.'
        )

    async def handle_fields_param(request, response_data):
        fields_query_param = request.query.get('fields')
        if fields_query_param:
            keys_to_remove = (
                response_data.keys() - set(fields_query_param.split(','))
            )
            for key in keys_to_remove:
                del response_data[key]
        return response_data

    async def get_upload_link_handler(request):
        """Обработчик для запросов на получение ссылки для загрузки файлов."""
        user_calls.add('get_upload_link')
        await check_headers(request.path, request.headers)
        assert 'path' in request.query, (
            'Убедитесь, что в запросе к эндпоинту Яндекс Диска '
            'для получения ссылки для загрузки файла '
            f'(`{REQUEST_UPLOAD_URL}`) передаётся параметр запроса `path` с '
            'путем для загрузки файла.'
        )
        path_param = request.query['path']
        with suppress(Exception):
            path_param = unquote(path_param)
        assert '/' in path_param, (
            f'Убедитесь, что в запросе к `{REQUEST_UPLOAD_URL}` '
            'путь в параметре `path` содержит символ `/` перед именем файла.'
        )
        file_name = path_param.split('/')[-1]
        path_hash = md5(request.query['path'].encode()).hexdigest()
        file_names[path_hash] = file_name

        link = f'http://{request.host}{UPLOAD_URL}/{path_hash}'
        response_data = await handle_fields_param(
            request,
            {
                'href': link,
                'method': 'PUT',
                'templated': False
            }
        )
        return web.json_response(response_data, status=200)

    async def mock_upload_handler(request):
        """Обработчик для запросов на загрузку файла."""
        user_calls.add('upload')
        request_data = await request.read()
        assert request_data, (
            'Убедитесь, что PUT-запрос на загрузку файла на Яндекс Диск '
            'содержит загружаемые данные.'
        )
        location_header = '/disk/{}'.format(
            quote(file_names[request.url.name])
        )
        return web.Response(headers={'Location': location_header}, status=201)

    async def mock_get_download_link_handler(request):
        """Обработчик для запросов на получение ссылки для скачивания файла."""
        user_calls.add('get_download_link')
        await check_headers(request.path, request.headers)
        assert 'path' in request.query, (
            'Убедитесь, что при отправке запроса к эндпоинту Яндекс Диска '
            'для получения ссылки на скачивание файла '
            f'(`{DOWNLOAD_LINK_URL}`) передаётся параметр запроса `path` с '
            'путем к скачиваемому файлу.'
        )
        path_hash = md5(request.query['path'].encode()).hexdigest()
        link = f'http://{request.host}disk/{path_hash}'
        response_data = await handle_fields_param(
            request,
            {
                'href': link,
                'method': 'GET',
                'templated': False
            }
        )
        return web.json_response(response_data, status=200)

    async def disk_info_handler(request):
        """Обработчик для запроса информации о Я.Диске."""
        return web.json_response(
            {
                'is_paid': True,
                'max_file_size': 53687091200,
                'paid_max_file_size': 53687091200,
                'reg_time': '2016-08-28T08:00:34+00:00',
                'revision': 1718044099614274,
                'system_folders': {'applications': 'disk:/Приложения'},
                'total_space': 2478196129792,
                'trash_size': 1574013,
                'unlimited_autoupload_enabled': False,
                'used_space': 20888456034
            },
            status=200
        )

    async def catch_all_handler(request):
        """Обработчик для любых других запросов."""
        raise AssertionError(COMMON_ASSERT_MSG_FOR_UPLOAD_FILES)

    app = web.Application()
    app.router.add_get(REQUEST_UPLOAD_URL, get_upload_link_handler)
    app.router.add_put(UPLOAD_URL + '/{path_hash}', mock_upload_handler)
    app.router.add_get(DOWNLOAD_LINK_URL, mock_get_download_link_handler)

    app.router.add_get('/v1/disk/', disk_info_handler)
    app.router.add_route('*', '/{tail:.*}', catch_all_handler)

    server = await aiohttp_server(app)
    return server, user_calls


async def intercept_requests(mock_server, monkeypatch):
    """Перехватывает запросы к API Я.Диска, используя мок-сервер."""
    def substitute_host(url):
        if 'yandex' in url:
            pattern = r'^(https?:\/\/)([^\/]+)'
            replacement = rf'http://{mock_server.host}:{mock_server.port}'
            url = re.sub(pattern, replacement, url)
        return url

    def request_decorator(func):
        def wrapper(*args, **kwargs):
            if len(args) > 1:
                args[1] = substitute_host(args[1])
            else:
                kwargs['url'] = substitute_host(kwargs['url'])
            return func(*args, **kwargs)
        return wrapper

    class InterceptedClientSession(aiohttp.ClientSession):

        async def _request(self, method, url, *args, **kwargs):
            url = substitute_host(url)
            return await super()._request(method, url, *args, **kwargs)

    monkeypatch.setattr(aiohttp, 'ClientSession', InterceptedClientSession)
    monkeypatch.setattr(aiohttp, 'request', request_decorator(aiohttp.request))
