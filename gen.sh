#!/bin/sh
cat tested | xargs -L 1 -- python3 generator.py -p -r /var/db/repos/gentoo-pypi-sci
