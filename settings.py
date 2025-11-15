import os

from dotenv import load_dotenv

load_dotenv()


class Config(object):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI')
    SECRET_KEY = os.getenv('SECRET_KEY')
    YANDEX_DISK_TOKEN = os.getenv('DISK_TOKEN')
    UPLOAD_URL = 'https://cloud-api.yandex.net/v1/disk/resources/upload'