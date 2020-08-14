import argparse
import sys
import json
import os
import requests
import re
import glob
from collections import defaultdict
from pathlib import Path

supported_python_versions = ['3.6', '3.7']
exceptions = {
    'scipy': 'sci-libs/scipy'
}
existing_packages = set()
missing_packages = set()

def get_package_name(package):
    if package in exceptions:
        return exceptions[package]
    else:
        if not package in existing_packages:
            print("Package '%s' does not exist" % package)
            missing_packages.add(package)
        return 'dev-python/' + package

def get_project_python_versions(project):
    classifiers = project['info']['classifiers']
    res = []
    for classifier in classifiers:
        for version in supported_python_versions:
            if classifier == 'Programming Language :: Python :: {}'.format(version):
                res.append(version)
                break
    
    # some packages just specified Python3
    if len(res) == 0:
        res = supported_python_versions
    return res

def convert_dependency(depend):
    # handle: package (>=version)
    match = re.match("(.+) \(>=(.+)\)", depend)
    if match:
        name = match.group(1)
        version = match.group(2)
        return '>={}-{}'.format(get_package_name(name), version)
    else:
        # handle: package (==version)
        match = re.match("(.+) \(==(.+)\)", depend)
        if match:
            name = match.group(1)
            version = match.group(2)
            return '=={}-{}'.format(get_package_name(name), version)
        else:
            return get_package_name(depend)

def get_iuse_and_depend(project):
    requires = project['info']['requires_dist']
    simple = []
    uses = defaultdict(list)
    if requires == None:
        return ''
    for req in requires:
        match = re.match("(.+); extra == '(.+)'", req)
        if match:
            name = match.group(1).strip()
            use = match.group(2)
            uses[use].append(convert_dependency(name))
        else:
            match = re.match('(.+); python_version < "(.+)"', req)
            if match:
                name = match.group(1).strip()
                simple.append(convert_dependency(name))
            else:
                simple.append(convert_dependency(req.strip()))

    use_res = []
    for use in uses:
        use_res.append('{}? ( {} )'.format(use, '\n\t\t'.join(uses[use])))
    iuse = 'IUSE="{}"'.format(" ".join(uses.keys()))
    return iuse + '\n' + 'RDEPEND="' + '\n\t'.join(simple + use_res) + '"'

def find_packages():
    for file in glob.glob('/var/db/repos/*/dev-python/**/*.ebuild', recursive=True):
        match = re.match(".*dev-python/(.+)/.*ebuild", file)
        if match:
            existing_packages.add(match.group(1))

    print('Found %d packages in gentoo repo' % len(existing_packages))

def generate(package, args):
    print('Generating {} to {}'.format(package, args.repo))
    resp = requests.get("https://pypi.org/pypi/{}/json".format(package))
    body = json.loads(resp.content)

    package = body['info']['name']
    versions = get_project_python_versions(body)
    compat = ' '.join(['python' + version.replace('.','_') for version in versions])
    print('Python versions', versions)
    print('Homepage', body['info']['home_page'])
    print('Description', body['info']['summary'])
    print('License', body['info']['license'])
    print('Version', body['info']['version'])
    iuse_and_depend = get_iuse_and_depend(body)
    print('IUSE and Depend', iuse_and_depend)

    dir = Path(args.repo) / "dev-python" / package
    path = dir / "{}-{}.ebuild".format(package, body['info']['version'])
    print('Writing to', path)
    dir.mkdir(parents=True, exist_ok=True)
    with path.open('w') as f:
        content = '# Copyright 1999-2020 Gentoo Authors\n'
        content += '# Distributed under the terms of the GNU General Public License v2\n\n'
        content += 'EAPI=7\n\n'
        content += 'PYTHON_COMPAT=( {} )\n\n'.format(compat)
        content += 'inherit distutils-r1\n\n'
        content += 'DESCRIPTION="{}"\n'.format(body['info']['summary'])
        content += 'SRC_URI="mirror://pypi/${PN:0:1}/${PN}/${P}.tar.gz"\n'
        content += 'HOMEPAGE="{}"\n\n'.format(body['info']['home_page'])
        content += 'LICENSE="{}"\n'.format(body['info']['license'])
        content += 'SLOT="0"\n'
        content += 'KEYWORDS="amd64"\n\n'
        content += iuse_and_depend

        f.write(content)

    if args.repoman:
        os.system('cd %s && repoman manifest' % (dir))
        
    if package in missing_packages:
        missing_packages.remove(package)
        existing_packages.add(package)
    
    if args.recursive:
        for pkg in list(missing_packages):
            if package not in existing_packages:
                generate(pkg, args)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--repo', help='set repo directory', default='../gentoo-localrepo')
    parser.add_argument('-v', '--verbose', action='store_true', help='enable verbose logging')
    parser.add_argument('-R', '--recursive', action='store_true', help='generate ebuild recursively')
    parser.add_argument('-p', '--repoman', action='store_true', help='run "repoman manifest" after generation')
    parser.add_argument('packages', nargs='+')
    args = parser.parse_args()

    find_packages()

    # setup repo structure
    metadata = Path(args.repo) / "metadata"
    metadata.mkdir(parents=True, exist_ok=True)
    with (metadata / "layout.conf").open('w') as f:
        f.write("masters = gentoo\nauto-sync = false")

    for package in args.packages:
        generate(package, args)

if __name__ == "__main__":
    main()
