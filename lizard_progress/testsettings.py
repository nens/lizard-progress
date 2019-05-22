import os

from lizard_progress.settingshelper import setup_logging
from lizard_progress.settingshelper import STATICFILES_FINDERS

DEBUG = True
TEMPLATE_DEBUG = True

# SETTINGS_DIR allows media paths and so to be relative to this settings file
# instead of hardcoded to c:\only\on\my\computer.
SETTINGS_DIR = os.path.dirname(os.path.realpath(__file__))

# BUILDOUT_DIR is for access to the "surrounding" buildout, for instance for
# BUILDOUT_DIR/var/static files to give django-staticfiles a proper place
# to place all collected static files.
BUILDOUT_DIR = os.path.abspath(os.path.join(SETTINGS_DIR, '..'))
#LOGGING = setup_logging(BUILDOUT_DIR)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'simple':  {
            'format': '%(levelname)s %(message)s'},
        'verbose': {
            'format': '%(asctime)s %(name)s %(levelname)s\n%(message)s'}
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'level': None
        },
        'logfile': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BUILDOUT_DIR, 'var', 'log', 'django.log'),
            'formatter': 'verbose',
            'level': 'WARN'
        },
        'null': {
            'class': 'logging.NullHandler',
            'level': 'DEBUG'
        }
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True
        },
        'django.request': {
            'handlers': ['console', 'logfile'],
            'propagate': False,
            'level': 'WARN',  # WARN also shows 404 errors
        },
        'django.db.backends': {
            'handlers': ['null'],
            'level': 'WARN',
            'propagate': False
        },
        'south': {
            'handlers': ['null'],
            'level': 'WARN',
            'propagate': False
        },
        'factory': {
            'handlers': ['null'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
}

SECRET_KEY = "Does not need to be secret"

DATABASES = {
    # Switched to postgis instead of spatialite because we test a function that
    # uses .extent() and that isn't supported by spatialite.
    'default': {
        'NAME': 'lizard_progress',
        # For some reason using lizard_progress.db_backend here fails, probably
        # because of the order in which things are loaded. Using it in the site
        # works.
        'ENGINE': 'lizard_progress.db_backend',
        'USER': 'buildout',
        'PASSWORD': 'buildout',
        'HOST': 'db',  # The 'db' host from docker-compose.yml
        'PORT': '',  # empty string for default.
    }
}
SOUTH_DATABASE_ADAPTERS = {
    'default': 'south.db.postgresql_psycopg2',
}


SITE_ID = 1
INSTALLED_APPS = [
    'lizard_progress',
    'lizard_progress.changerequests',
    'lizard_progress.email_notifications',
    'django.contrib.staticfiles',
    'compressor',
    'south',
    'django_nose',
    'django_extensions',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.gis',
    'django.contrib.sites',
]
ROOT_URLCONF = 'lizard_progress.urls'

TEMPLATE_CONTEXT_PROCESSORS = (
    # Default django 1.3 processors.
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.contrib.messages.context_processors.messages"
)

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

# Used for django-staticfiles (and for media files
STATIC_URL = '/static_media/'
ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'
MEDIA_URL = '/media/'
STATIC_ROOT = os.path.join(BUILDOUT_DIR, 'var', 'static')
MEDIA_ROOT = os.path.join(BUILDOUT_DIR, 'var', 'media')
STATICFILES_FINDERS = STATICFILES_FINDERS

# Let tasks (called with .delay()) run as if they were called normally.
CELERY_ALWAYS_EAGER = True
import djcelery
djcelery.setup_loader()
BROKER_URL = 'memory'

# For testing, use the in-memory email backend
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'

# For translating things in Celery tasks, mostly.
LANGUAGE_CODE = 'nl-NL'

# RIONED GWSW HTTP API urls and credentials:
GWSW_API_ENABLED = True
GWSW_UPLOAD_URL = 'TODO (site setting)'
GWSW_GETIDS_URL = 'TODO (site setting)'
GWSW_GETLOG_URL = 'TODO (site setting)'


try:
    # Import local settings that aren't stored in svn/git.
    from lizard_progress.local_testsettings import *
except ImportError:
    pass
