"""
Django settings for graphomics project.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""
import os

from configurations import Configuration, values
from django.contrib.messages import constants as message_constants
from django.urls import reverse_lazy

from linker.constants import EXTERNAL_GO_DATA, EXTERNAL_KEGG_TO_CHEBI, EXTERNAL_GENE_NAMES, EXTERNAL_COMPOUND_NAMES


class Common(Configuration):
    # Build paths inside the project like this: os.path.join(BASE_DIR, ...)
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))

    # SECURITY WARNING: keep the secret key used in production secret!
    SECRET_KEY = values.SecretValue()

    # SECURITY WARNING: don't run with debug turned on in production!
    DEBUG = values.BooleanValue(False)

    ALLOWED_HOSTS = []

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{name} {levelname} {asctime} {filename}:{lineno} | {message}',
                'style': '{',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
        },
        'root': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'loggers': {
            'neobolt': {
                'level': 'WARNING'
            },
            'matplotlib': {
                'level': 'WARNING'
            },
            'suds': {
                'level': 'WARNING'
            },
        },
    }

    # Application definition
    INSTALLED_APPS = [
        'grappelli',
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'whitenoise.runserver_nostatic',
        'django.contrib.staticfiles',
        'django_extensions',
        'django_select2',
        'webpack_loader',
        'graphomics.users',
        'linker',
        'registration'
    ]

    WEBPACK_LOADER = {
        'DEFAULT': {
            'BUNDLE_DIR_NAME': 'bundles/',
            'STATS_FILE': os.path.join(BASE_DIR, 'webpack-stats.json'),
        }
    }

    MIDDLEWARE = [
        'django.middleware.security.SecurityMiddleware',
        'whitenoise.middleware.WhiteNoiseMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
        'django.middleware.gzip.GZipMiddleware',
    ]

    ROOT_URLCONF = 'graphomics.urls'

    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [os.path.join(BASE_DIR, 'templates')],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                ],
            },
        },
    ]

    WSGI_APPLICATION = 'graphomics.wsgi.application'

    # Database
    # https://docs.djangoproject.com/en/2.0/ref/settings/#databases
    DATABASES = values.DatabaseURLValue(
        'sqlite:///{}'.format(os.path.join(BASE_DIR, 'db.sqlite3'))
    )

    # Password validation
    # https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators
    AUTH_PASSWORD_VALIDATORS = [
        {
            'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        },
    ]

    # Internationalization
    # https://docs.djangoproject.com/en/2.0/topics/i18n/
    LANGUAGE_CODE = 'en-us'

    TIME_ZONE = 'UTC'

    USE_I18N = True

    USE_L10N = True

    USE_TZ = True

    # Static files (CSS, JavaScript, Images)
    # https://docs.djangoproject.com/en/2.0/howto/static-files/
    STATIC_URL = '/static/'
    STATIC_PATH = os.path.join(BASE_DIR,'static')
    STATIC_ROOT = os.path.join(BASE_DIR,'assets')
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

    STATICFILES_DIRS = (
        STATIC_PATH,
    )

    # For file upload
    # See https://simpleisbetterthancomplex.com/tutorial/2016/08/01/how-to-upload-files-with-django.html
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

    AUTH_USER_MODEL = 'users.User'
    LOGIN_URL = reverse_lazy('login')

    # to let save group function work
    DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880

class Development(Common):
    """
    The in-development settings and the default configuration.
    """
    DEBUG = True
    MESSAGE_LEVEL = message_constants.DEBUG

    ALLOWED_HOSTS = ['*']

    INTERNAL_IPS = [
        '127.0.0.1'
    ]


class Production(Common):
    """
    The production settings.
    """

    # for https and proxy stuff
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_TRUSTED_ORIGINS = ['graphomics.glasgowcompbio.org']
    ALLOWED_HOSTS = ['127.0.0.1']
