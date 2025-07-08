#!/usr/bin/env python3

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="triangulum-lx",
    version="1.0.0",
    author="Triangulum Team",
    author_email="info@triangulum-debug.ai",
    description="An agentic debugging system using the triangle paradigm",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/triangulum/triangulum-lx",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Debuggers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "autogen>=0.2.0",
        "numpy>=1.20.0",
        "networkx>=2.6.0",
        "matplotlib>=3.4.0",
        "PyYAML>=6.0",
        "scikit-learn>=1.0.0",
        "joblib>=1.0.0"
    ],
    entry_points={
        "console_scripts": [
            "triangulum=triangulum_lx.scripts.cli:main",
        ],
    },
)
