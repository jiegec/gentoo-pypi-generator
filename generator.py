import argparse
import sys
import json
import os
import requests
import re
import glob
from collections import defaultdict
from pathlib import Path
import datetime

supported_python_versions = ['3.9', '3.10', '3.11']

# already provided by other gentoo packages
exceptions = {
    'bs4': 'dev-python/beautifulsoup:4',
    'funcsigs': '',
    'opencv-python': 'media-libs/opencv[python]',
    'scikit-learn': 'sci-libs/scikit-learn',
    'scipy': 'dev-python/scipy',
    'tensorflow': 'sci-libs/tensorflow',
    'tensorflow-cpu': 'sci-libs/tensorflow',
    'tensorflow-gpu': 'sci-libs/tensorflow[gpu]',
    'torch' : 'sci-libs/pytorch',
    'tornado': 'www-servers/tornado',
    'urllib3': ''
}

# handle '-' and '_'
renames = { k:k.replace('-', '_') for k in ['async-generator',
                                           'jupyter-core',
                                           'jupyter-console',
                                           'jupyter-client',
                                           'jupyter-telemetry',
                                           'Keras-Preprocessing',
                                           'matlab-kernel',
                                           'mpl-axes-aligner',
                                           'pretty-midi',
                                           'prometheus-client',
                                           'importlib-resources',
                                           ]}

# other cases
renames.update({'SQLAlchemy': 'sqlalchemy',
                'Sphinx': 'sphinx',
                'PyYAML': 'pyyaml',
                'Jinja2': 'jinja',
                'jinja2': 'jinja',
                'netcdf4': 'netcdf4-python',
                })

# unneeded packages for python2 backports
removals = [ 'backports.lzma' ]

# license mapping
license_mapping = {
        'BSD 3-clause': 'BSD',
        'BSD 3-clause License': 'BSD',
        'BSD 3-Clause License': 'BSD',
}

# useless dependencies
use_blackhole = set(('dev', 'doc', 'docs', 'all', 'test', 'cuda'))

existing_packages = set()
missing_packages = set()

def get_package_name(package):
    package = package.replace('.', '-')
    if package in exceptions:
        return exceptions[package]
    elif package in renames:
        package = renames[package]

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
    # ignore strings after ';'
    depend = depend.split(';')[0].strip()
    # ignore strings after '[', e.g. horovod[torch]
    depend = depend.split('[')[0]
    # handle: package (>=version)
    match = re.match("(.+) \(?>=([^)]+)\)?", depend)
    if match:
        name = match.group(1)
        version = match.group(2)
        return '>={}-{}[${{PYTHON_USEDEP}}]'.format(get_package_name(name), version)
    else:
        # handle: package (==version)
        match = re.match("(.+) \(?==([^)]+)\)?", depend)
        if match:
            name = match.group(1)
            version = match.group(2)
            return '={}-{}[${{PYTHON_USEDEP}}]'.format(get_package_name(name), version)
        else:
            # strip all exotic (.*), e.g. (~=1-32-0), (~=3-7-4), (<2,>=1-21-1)
            match = re.match("([^ ><=~!]+).*", depend)
            if match:
                name = match.group(1)
                return '{}[${{PYTHON_USEDEP}}]'.format(get_package_name(name))
            else:
                return '{}[${{PYTHON_USEDEP}}]'.format(get_package_name(depend))

def get_iuse_and_depend(project):
    requires = project['info']['requires_dist']
    simple = []
    uses = defaultdict(list)
    if requires == None:
        return ''
    for req in requires:
        for rm in removals:
            if rm in req:
                break
        else:
            match = re.match("(.+); (.* and )?extra == '(.+)'", req)
            if match:
                name = match.group(1).strip()
                use = match.group(3)
                if use in use_blackhole:
                    continue
                uses[use].append(convert_dependency(name))
            else:
                match = re.match('(.+); python_version < "(.+)"', req)
                if match:
                    name = match.group(1).strip()
                    if not name.startswith('backports'):
                        # we don't need backports for python3
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

    package = body['info']['name'].replace('.','-')
    if package in renames:
        package = renames[package]
    versions = get_project_python_versions(body)
    compat = ' '.join(['python' + version.replace('.','_') for version in versions])
    print('Python versions', versions)
    print('Homepage', body['info']['home_page'])
    print('Description', body['info']['summary'])
    license = body['info']['license']
    if license in license_mapping:
        license = license_mapping[license]
    print('License', license)
    print('Version', body['info']['version'])
    iuse_and_depend = get_iuse_and_depend(body)
    print('IUSE and Depend', iuse_and_depend)

    dir = Path(args.repo) / "dev-python" / package
    path = dir / "{}-{}.ebuild".format(package, body['info']['version'])
    print('Writing to', path)
    dir.mkdir(parents=True, exist_ok=True)
    with path.open('w') as f:
        content = f'# Copyright 1999-{datetime.date.today().year} Gentoo Authors\n'
        content += '# Distributed under the terms of the GNU General Public License v2\n\n'
        content += 'EAPI=8\n\n'
        content += 'PYTHON_COMPAT=( {} )\n\n'.format(compat)
        content += 'inherit distutils-r1 pypi\n\n'
        content += 'DESCRIPTION="{}"\n'.format(body['info']['summary'])
        content += 'HOMEPAGE="{}"\n\n'.format(body['info']['home_page'])
        content += 'LICENSE="{}"\n'.format(body['info']['license'])
        content += 'SLOT="0"\n'
        content += 'KEYWORDS="~amd64"\n\n'
        content += iuse_and_depend
        content += '\ndistutils_enable_tests pytest\n'

        f.write(content)

    if args.repoman:
        os.system('cd %s && repoman manifest' % (dir))
        
    if package in missing_packages:
        missing_packages.remove(package)
        existing_packages.add(package)
    
    if args.recursive:
        for pkg in list(missing_packages):
            if pkg not in existing_packages:
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
        f.write("masters = gentoo\nauto-sync = false\n")

    for package in args.packages:
        generate(package, args)

if __name__ == "__main__":
    main()
