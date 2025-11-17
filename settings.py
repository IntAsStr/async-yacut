import os
import string

from dotenv import load_dotenv

load_dotenv()


class Config(object):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI')
    SECRET_KEY = os.getenv('SECRET_KEY')
    YANDEX_DISK_TOKEN = os.getenv('DISK_TOKEN')
    UPLOAD_URL = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
    MAX_CUSTOM_ID_LENGTH = 16
    ALLOWED_SHORT_ID_CHARS = string.ascii_letters + string.digits
    MAX_ATTEMPS = 10
    DOWNLOAD_URL = 'https://cloud-api.yandex.net/v1/disk/resources/download'
    SHORT_ID_LENGTH = 6
