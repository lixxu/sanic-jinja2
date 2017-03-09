"""
sanic-jinja2
--------------
Jinja2 support for sanic
"""
from setuptools import setup

setup(
    name='sanic-jinja2',
    version='0.5.1',
    url='https://github.com/lixxu/sanic-jinja2',
    license='BSD',
    author='Lix Xu',
    author_email='xuzenglin@gmail.com',
    description='Jinja2 support for sanic',
    long_description=__doc__,
    packages=['sanic_jinja2'],
    zip_safe=False,
    platforms='any',
    install_requires=[
        'sanic',
        'jinja2',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)
