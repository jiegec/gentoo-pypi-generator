LOCALREPO := $(abspath ../../gentoo-localrepo)
PROJECT := $(abspath ../)

build:
	sudo docker build -t gentoo-pypi-test .

run:
	sudo docker run -it --rm -v $(LOCALREPO):/var/db/repos/localrepo -v $(PROJECT):/root/project --name gentoo-pypi-test gentoo-pypi-test
