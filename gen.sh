#!/bin/sh
cat tested | xargs -L 1 -- python3 generator.py -p -R
