from setuptools import setup
from os import path
import re

here = path.abspath(path.dirname(__file__))

install_requires = ['urllib3>=1.25.11', 'aiohttp>=3.7.2']
cmdclass = {}

# Parse version
with open(path.join(here, 'amanobot', '__init__.py')) as f:
    m = re.search(r'^__version_info__ *= *\(([0-9]+), *([0-9]+), ([0-9]+)\)', f.read(), re.MULTILINE)
    version = '.'.join(m.groups())

with open('README.md') as f:
    long_desc = f.read()

setup(
    cmdclass=cmdclass,

    name='amanobot',
    packages=['amanobot', 'amanobot.aio'],
    # Do not filter out packages because we need the whole thing during `sdist`.

    install_requires=install_requires,
    python_requires='>=3.5.3',

    version=version,

    description='Python framework for Telegram Bot API forked from Telepot',

    long_description=long_desc,
    long_description_content_type='text/markdown',

    url='https://github.com/AmanoTeam/amanobot',

    author='AmanoTeam',
    author_email='contact@amanoteam.com',

    license='MIT',

    # See https://pypi.org/classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Communications :: Chat',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],

    keywords='telegram bot api python wrapper',
)
