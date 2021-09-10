tox:
	python --version
	python -m tox -e py36

test:
	pytest test/
