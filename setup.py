try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from gpio import __version__


with open("README.md") as f:
    ldesc = f.read()

config = {
    'name': 'gpio',
    'author': 'Garrett Berg',
    'author_email': 'garrett@cloudformdesign.com',
    'version': __version__,
    'py_modules': ['gpio'],
    'license': 'MIT',
    'install_requires': [
    ],
    'extras_require': {
    },
    'description': "gpio access via the standard linux sysfs interface",
    'long_description': ldesc,
    'url': "https://github.com/cloudformdesign/gpio",
    'classifiers': [
        # 'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Embedded Systems',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
}

setup(**config)
