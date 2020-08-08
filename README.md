# gentoo-pypi-generator

Generate ebuild from PyPI packages with ease.

## How to develop

### Docker environment

You can directly use the version on DockerHub:

```shell
$ docker pull jiegec/gentoo-pypi-test:latest
```

Or, you can build locally:

```shell
$ cd developing
$ make build
```

### How to run

Create a localrepo at `../gentoo-localrepo`. Then, run script to generate ebuild:

```shell
$ python3 generator.py xgboost
```

You can find generated files at `../gentoo-localrepo`. Then, test it in docker environment:

```shell
$ cd developing
$ make run
```
