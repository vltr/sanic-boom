import io
import re
from glob import glob
from os.path import basename, dirname, join, splitext

from setuptools import find_packages, setup


def read(*names, **kwargs):
    return io.open(
        join(dirname(__file__), *names),
        encoding=kwargs.get("encoding", "utf8"),
    ).read()


setup(
    name="sanic-boom",
    version="0.1.1",
    license="MIT license",
    description="Components injection, fast routing and non-global (layered) "
    "middlewares. Give your Sanic application a Boom!",
    long_description="%s\n%s"
    % (
        re.compile("^.. start-badges.*^.. end-badges", re.M | re.S).sub(
            "", read("README.rst")
        ),
        re.sub(":[a-z]+:`~?(.*?)`", r"``\1``", read("CHANGELOG.rst")),
    ),
    author="Richard Kuesters",
    author_email="rkuesters@gmail.com",
    url="https://github.com/vltr/sanic-boom",
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob("src/*.py")],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        # 'Programming Language :: Python :: Implementation :: PyPy',
        "Topic :: Utilities",
    ],
    keywords=["sanic", "components", "lifecycle", "productivity"],
    install_requires=[
        "Sanic>=0.8.0",
        "xrtr>=0.2.1",
        "sanic-ipware>=0.1.0",
        "httptools>=0.0.11",
    ],
    extras_require={
        # eg:
        #   'rst': ['docutils>=0.11'],
        #   ':python_version=="2.6"': ['argparse'],
    },
)
