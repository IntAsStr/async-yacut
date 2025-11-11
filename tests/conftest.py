import os
import sys
from pathlib import Path
from random import choice

import pytest
from dotenv import load_dotenv
from io import BytesIO
from PIL import Image

load_dotenv()

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
sys.path.append(str(BASE_DIR))

_user_environment = os.environ.copy()
_tmp_db_uri = 'sqlite:///:memory:'
os.environ['DATABASE_URI'] = _tmp_db_uri
os.environ['DISK_TOKEN'] = 'y0_nbfoiu3445tno35_fd09v854bn2_cs0e8hrb4k'

PY_URL = 'https://www.python.org'
TEST_BASE_URL = 'http://localhost'

pytest_plugins = [
    'tests.yandex_disk_mock_server'
]

try:
    from yacut import app, db
    from yacut.models import URLMap  # noqa
except NameError as exc:
    raise AssertionError(
        'При попытке импорта объекта приложения вознакло исключение: '
        f'`{type(exc).__name__}: {exc}`'
    )
except ImportError as exc:
    if any(obj in exc.name for obj in ['models', 'URLMap']):
        raise AssertionError('В файле `models` не найдена модель `URLMap`.')
    raise AssertionError(
        'При попытке запуска приложения вознакло исключение: '
        f'`{type(exc).__name__}: {exc}`'
    )

assert app.config['SQLALCHEMY_DATABASE_URI'] == _tmp_db_uri, (
    'Проверьте, что конфигурационному ключу `SQLALCHEMY_DATABASE_URI` '
    'присвоено значение с настройками для подключения базы данных с '
    'использованием переменной окружения `DATABASE_URI`.'
)


@pytest.fixture
def user_environment():
    return _user_environment


@pytest.fixture
def default_app():
    with app.app_context():
        yield app


@pytest.fixture
def _app():
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
        db.session.close()


@pytest.fixture
def client(_app):
    return _app.test_client()


@pytest.fixture
def cli_runner():
    return app.test_cli_runner()


@pytest.fixture
def short_python_url():
    url_map_object = URLMap(original='https://www.python.org', short='py')
    db.session.add(url_map_object)
    db.session.commit()
    return url_map_object


@pytest.fixture(scope='session')
def duplicated_custom_id_msg():
    return 'Предложенный вариант короткой ссылки уже существует.'


def generate_png_bytes():
    """
    Генерирует PNG-файл в 1 пиксель случайного цвета в байтовом представлении.

    Возвращает байтовое представление файла.
    """
    colors = [
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (255, 255, 0),
        (255, 0, 255),
        (0, 255, 255)
    ]
    selected_color = choice(colors)

    img = Image.new('RGB', (1, 1), color=selected_color)
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr.read()
