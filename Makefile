# This file is part of the Triangulum project.
#
# To start the application, run the following command:
#
# tsh --help
#

.PHONY: install lint test package

install:
	pip install .

lint:
	flake8 tsh tests
	isort --check-only tsh tests

test:
	pytest -q --cov=tsh

package:
	python setup.py sdist bdist_wheel
