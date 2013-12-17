import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

SECRET_KEY = 'h)7ir0!6d0!r2d8+xm2+mpiw7z_#=1yk6==c4avbt@#-g#t4jg'
DEBUG = False

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []

HTTP_CACHE = False

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'json_field',
    'dynamicwidgets',

    'forum',
    'simpleauth',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.request",
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'overmind.urls'

WSGI_APPLICATION = 'overmind.wsgi.application'


# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/tmp/overmind_cache/',
    }
}


STATICFILES_DIRS = (
    "static",
)
STATIC_URL = '/static/'

LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "/auth/login/"
LOGOUT_URL = "/auth/logout/"

COUNTER_STORAGE_BACKEND = 'counter.backend.DjangoCache'

FORUM_TOPICS_PER_PAGE = 25
FORUM_POSTS_PER_PAGE = 25

CACHEDB_ADDRESS = 'localhost:12345'
