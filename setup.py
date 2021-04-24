# import multiprocessing to avoid this bug (http://bugs.python.org/issue15881#msg170215)
import multiprocessing

assert multiprocessing
import re
from setuptools import setup, find_packages


def get_version():
    """
    Extracts the version number from the version.py file.
    """
    VERSION_FILE = "qe2e/version.py"
    mo = re.search(
        r'^__version__ = [\'"]([^\'"]*)[\'"]', open(VERSION_FILE, "rt").read(), re.M
    )
    if mo:
        return mo.group(1)
    else:
        raise RuntimeError("Unable to find version string in {0}.".format(VERSION_FILE))


with open("requirements.txt") as fin:
    install_requires = fin.read().split("\n")

with open("requirements-dev.txt") as fin:
    tests_require = fin.read().split("\n")

docs_require = ["Sphinx>=1.2.2", "sphinx_rtd_theme"]

extras_require = {
    "test": tests_require,
    "packaging": ["wheel"],
    "docs": docs_require,
}

everything = set(install_requires)
for deps in extras_require.values():
    everything.update(deps)
extras_require["all"] = list(everything)

setup(
    name="qe2e",
    version=get_version(),
    description="",
    long_description=open("README.md").read(),
    url="https://github.com/joshmarlow/qe2e",
    author="Josh Marlow",
    author_email="joshmarlow@gmail.com",
    keywords="",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    license="MIT",
    include_package_data=True,
    test_suite="nose.collector",
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require=extras_require,
    scripts=["qe2e/qe2e"],
    zip_safe=False,
)
