LOCALREPO := $(abspath ../../gentoo-localrepo)

build:
	sudo docker build -t gentoo-pypi-test .

run:
	sudo docker run -it --rm -v $(LOCALREPO):/var/db/repos/localrepo --name gentoo-pypi-test gentoo-pypi-test
