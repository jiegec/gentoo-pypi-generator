import argparse
import sys
import json
import requests
import re
from collections import defaultdict
from pathlib import Path

supported_python_versions = ['3.6', '3.7']

def get_project_python_versions(project):
    classifiers = project['info']['classifiers']
    res = []
    for classifier in classifiers:
        for version in supported_python_versions:
            if classifier == 'Programming Language :: Python :: {}'.format(version):
                res.append(version)
                break
    return res

def get_iuse_and_depend(project):
    requires = project['info']['requires_dist']
    simple = []
    uses = defaultdict(list)
    for req in requires:
        match = re.match("(.+) ; extra == '(.+)'", req)
        if match:
            name = match.group(1)
            use = match.group(2)
            uses[use].append('dev-python/{}'.format(name))
        else:
            simple.append('dev-python/{}'.format(req))

    use_res = []
    for use in uses:
        use_res.append('{}? ( {} )'.format(use, '\n\t\t'.join(uses[use])))
    iuse = 'IUSE="{}"'.format(" ".join(uses.keys()))
    return iuse + '\n' + 'RDEPEND="' + '\n\t'.join(simple + use_res) + '"'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--repo', help='set repo directory', default='../gentoo-localrepo')
    parser.add_argument('-v', '--verbose', action='store_true', help='enable verbose logging')
    parser.add_argument('packages', nargs='+')
    args = parser.parse_args()

    for package in args.packages:
        print('Generating {} to {}'.format(package, args.repo))
        resp = requests.get("https://pypi.org/pypi/{}/json".format(package))
        body = json.loads(resp.content)

        versions = get_project_python_versions(body)
        compat = ' '.join(['python' + version.replace('.','_') for version in versions])
        print('Python versions', versions)
        print('Homepage', body['info']['home_page'])
        print('Description', body['info']['summary'])
        print('License', body['info']['license'])
        print('Version', body['info']['version'])
        print('IUSE and Depend', get_iuse_and_depend(body))

        path = Path(args.repo) / "dev-python" / package / "{}-{}.ebuild".format(package, body['info']['version'])
        print('Writing to', path)
        with path.open('w') as f:
            content = '# Copyright 1999-2020 Gentoo Authors\n'
            content += '# Distributed under the terms of the GNU General Public License v2\n\n'
            content += 'EAPI=7\n\n'
            content += 'PYTHON_COMPAT=( {} )\n\n'.format(compat)
            content += 'inherit distutils-r1\n\n'
            content += 'DESCRIPTION="{}"\n'.format(body['info']['summary'])
            content += 'SRC_URL="mirror://pypi/${PN:0:1}/${PN}/${PN}-${PV}.tar.gz"\n'
            content += 'HOMEPAGE="{}"\n\n'.format(body['info']['home_page'])
            content += 'LICENSE="{}"\n'.format(body['info']['license'])
            content += 'SLOT="0"\n'
            content += 'KEYWORDS="amd64"\n\n'
            content += get_iuse_and_depend(body)

            f.write(content)

if __name__ == "__main__":
    main()
