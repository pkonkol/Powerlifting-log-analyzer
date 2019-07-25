import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()


setup(
    name='open_powerlifting_log',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    license='',
    description='Commandline program parsing and analyzing powerlifting'
                'training spreadsheets',
    long_description=README,
    long_description_content_type='text/markdown',
    url='https://www.opl.org/',
    author='Petros Tararuj',
    author_email=' ',
    classifiers=[
        ' '
        ],
    )
