import os

from lizard_ui.settingshelper import setup_logging
from lizard_ui.settingshelper import STATICFILES_FINDERS

DEBUG = True
TEMPLATE_DEBUG = True

# SETTINGS_DIR allows media paths and so to be relative to this settings file
# instead of hardcoded to c:\only\on\my\computer.
SETTINGS_DIR = os.path.dirname(os.path.realpath(__file__))

# BUILDOUT_DIR is for access to the "surrounding" buildout, for instance for
# BUILDOUT_DIR/var/static files to give django-staticfiles a proper place
# to place all collected static files.
BUILDOUT_DIR = os.path.abspath(os.path.join(SETTINGS_DIR, '..'))
LOGGING = setup_logging(BUILDOUT_DIR)

# ENGINE: 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
# In case of geodatabase, prepend with:
# django.contrib.gis.db.backends.(postgis)
DATABASES = {
    # Switched to postgis instead of spatialite because we test a function that
    # uses .extent() and that isn't supported by spatialite.
    'default': {
        'NAME': 'lizard_progress',
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'USER': 'buildout',
        'PASSWORD': 'buildout',
        'HOST': '',  # empty string for localhost.
        'PORT': '',  # empty string for default.
        }
    }
SITE_ID = 1
INSTALLED_APPS = [
    'lizard_progress',
    'lizard_progress.changerequests',
    'lizard_ui',
    'lizard_map',
    'lizard_security',
    'staticfiles',
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
    # Uncomment this one if you use lizard-map.
    # 'lizard_map.context_processors.processor.processor',
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


try:
    # Import local settings that aren't stored in svn/git.
    from lizard_progress.local_testsettings import *
except ImportError:
    pass
