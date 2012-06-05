from setuptools import setup

version = '0.12'

long_description = '\n\n'.join([
    open('README.rst').read(),
    open('CREDITS.rst').read(),
    open('CHANGES.rst').read(),
    ])

install_requires = [
    'Django',
    'django-extensions',
    'django-nose',
    # We don't work with 4.0 yet; firstly because then we must require lizard-security
    # and add it to installed_apps, secondly because there's only one customer using
    # this app right now (HDSR) and they don't get the new interface yet.
    'lizard-ui >= 3.0, < 4.0a1',
    'lizard-map >= 3.23, < 4.0a1',
    'pkginfo',
    'factory_boy',
    ],

tests_require = [
    ]

setup(name='lizard-progress',
      version=version,
      description="TODO",
      long_description=long_description,
      # Get strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=['Programming Language :: Python',
                   'Framework :: Django',
                   ],
      keywords=[],
      author='TODO',
      author_email='TODO@nelen-schuurmans.nl',
      url='',
      license='GPL',
      packages=['lizard_progress'],
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      tests_require=tests_require,
      extras_require = {'test': tests_require},
      entry_points={
          'console_scripts': [],
          'lizard_map.adapter_class': [
              'adapter_progress = lizard_progress.layers:ProgressAdapter',
              ]})
