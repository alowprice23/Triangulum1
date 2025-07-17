# This file is part of the Triangulum project.
#
# To start the application, run the following command:
#
# tsh --help
#

from setuptools import setup, find_packages

setup(
    name="triangulum-lx",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'triangulum = triangulum_lx.cli:cli',
        ],
    },
)
