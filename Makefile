.PHONY: help clean-pyc lint test shell coverage html publish
.DEFAULT_GOAL := help

help: ## See what commands are available.
	@echo "clean-pyc - remove Python file artifacts"
	@echo "lint - check style with flake8"
	@echo "test - run tests quickly with the default Python"
	@echo "shell - launch a shell all ready to go"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "html - build the html version of the docs."
	@echo "i18n - extract the marked strings to gettext po files."
	@echo "l10n - generate the gettext mo files."
	@echo "publish - publishes a new version to pypi."
	@echo "purge - purge the cached version of the %coverage button."

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

develop: clean-pyc
	pip install -r requirements.txt

lint:
	flake8 ls/joyous

test:
	python ./runtests.py

shell:
	python ./shell.py

coverage:
	python ./runtests.py --pytest --coverage
	python -m webbrowser htmlcov/index.html

i18n:
	cd ls/joyous && django-admin makemessages --all

l10n:
	cd ls/joyous && django-admin compilemessages

html:
	$(MAKE) --directory=docs html
	python -m webbrowser docs/build/html/index.html

publish:
	rm -f dist/* && python setup.py sdist bdist_wheel && twine upload dist/* && echo 'Success! Go to https://pypi.python.org/pypi/ls.joyous and check that all is well.'
	python -m webbrowser https://pypi.python.org/pypi/ls.joyous/#history

purge:
	curl -X PURGE https://camo.githubusercontent.com/6e29f322d6505de214323b7680fbbdadcbb93ed9/68747470733a2f2f636f766572616c6c732e696f2f7265706f732f6769746875622f6c696e7578736f6674776172652f6c732e6a6f796f75732f62616467652e7376673f6272616e63683d6d6173746572

