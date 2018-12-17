"""
sanic-jinja2
--------------
Jinja2 support for sanic
"""
import os
from pathlib import Path
import platform
from setuptools import setup

if platform.system().startswith("Windows"):
    os.environ["SANIC_NO_UVLOOP"] = "yes"

p = Path(__file__) / "../sanic_jinja2/__init__.py"
with p.resolve().open(encoding="utf-8") as f:
    for line in f:
        if line.startswith("__version__ = "):
            version = line.split("=")[-1].strip().replace("'", "")
            break

setup(
    name="sanic-jinja2",
    version=version.replace('"', ""),
    url="https://github.com/lixxu/sanic-jinja2",
    license="BSD",
    author="Lix Xu",
    author_email="xuzenglin@gmail.com",
    description="Jinja2 support for sanic",
    long_description=__doc__,
    packages=["sanic_jinja2"],
    zip_safe=False,
    platforms="any",
    install_requires=["sanic", "jinja2"],
    classifiers=[
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
)
