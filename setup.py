"""
setup.py
"""
import os
from codecs import open
from setuptools import setup, find_packages
from setuptools.command.develop import develop
from subprocess import check_call
import shlex
from warnings import warn

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, "README.rst"), encoding="utf-8") as f:
    readme = f.read()

with open(os.path.join(here, "NRWAL", "version.py"), encoding="utf-8") as f:
    version = f.read()

version = version.split('=')[-1].strip().strip('"').strip("'")


class PostDevelopCommand(develop):
    """
    Class to run post setup commands
    """

    def run(self):
        """
        Run method that tries to install pre-commit hooks
        """
        try:
            check_call(shlex.split("pre-commit install"))
        except Exception as e:
            warn("Unable to run 'pre-commit install': {}"
                 .format(e))

        develop.run(self)


def find_data_files(extensions=('.yaml', '.yml', '.json'), path='./NRWAL'):
    """Find all equation and config files in the NRWAL library to include as
    package data for pip install.

    Parameters
    ----------
    extensions : list | tuple
        List of equation file extensions to include as part of the install.
    path : str | list
        Directory(s) of equation files to include in install.

    Returns
    -------
    equation_files : list
        List of equation file paths relative to input path to include in
        package data.
    """

    equation_files = []
    if isinstance(path, (list, tuple)):
        for p in path:
            equation_files += find_data_files(extensions=extensions, path=p)
    else:
        for root, _, files in os.walk(path):
            for fn in files:
                if any(ext in fn for ext in extensions):
                    fp = os.path.join(root, fn)
                    fp = fp.lstrip('./NRWAL')
                    equation_files.append(fp.replace(path, ''))

    return equation_files


with open("requirements.txt") as f:
    install_requires = f.readlines()


test_requires = ["pytest>=5.2", ]
description = ("National Renewable Energy Laboratory's (NREL's) Wind Analysis"
               "Library: NRWAL")


setup(
    name="NREL-NRWAL",
    version=version,
    description=description,
    long_description=readme,
    author="Jacob Nunemaker",
    author_email="jacob.nunemaker@nrel.gov",
    url="https://nrel.github.io/NRWAL/",
    packages=find_packages(),
    package_dir={"NRWAL": "NRWAL"},
    package_data={'NRWAL': find_data_files()},
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "NRWAL=NRWAL.cli:main",
        ],
    },
    license="BSD 3-Clause",
    zip_safe=False,
    keywords="NRWAL",
    python_requires='>=3.7',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    test_suite="tests",
    install_requires=install_requires,
    extras_require={
        "test": test_requires,
        "dev": test_requires + ["flake8", "pre-commit", "pylint"],
    },
    cmdclass={"develop": PostDevelopCommand},
)
