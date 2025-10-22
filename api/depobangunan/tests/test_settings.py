from django.test import TestCase, override_settings
from django.conf import settings

TEST_DATABASE_NAME = 'test_depobangunan_db'

@override_settings(
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': TEST_DATABASE_NAME,
            'USER': settings.DATABASES['default']['USER'],
            'PASSWORD': settings.DATABASES['default']['PASSWORD'],
            'HOST': settings.DATABASES['default']['HOST'],
            'PORT': settings.DATABASES['default']['PORT'],
            'TEST': {
                'NAME': TEST_DATABASE_NAME,
                'CHARSET': 'utf8mb4',
                'COLLATION': 'utf8mb4_unicode_ci',
            },
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES', time_zone = '+00:00'",
            },
        }
    }
)
class MySQLTestCase(TestCase):
    pass
