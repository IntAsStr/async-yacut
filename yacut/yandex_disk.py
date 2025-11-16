import aiohttp
import urllib.parse
from flask import current_app


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
            if not location:
                raise Exception('Не удалось получить расположение файла')

            location = urllib.parse.unquote(location)
            location = location.replace('/disk', '')
            return location


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
            if response.status != 200:
                error_text = await response.text()
                raise Exception(
                    f'Ошибка получения ссылки: {response.status}: {error_text}'
                )
            data = await response.json()
            return data['href']
