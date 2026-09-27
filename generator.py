import argparse
import sys
import json
import os
import requests
import re
import glob
import io
import tarfile
import tomllib
import zipfile
from collections import defaultdict
from pathlib import Path
import datetime
import portage

portagedb = portage.db[portage.root]["porttree"].dbapi

supported_python_versions = ['3.13', '3.14']

# already provided by other gentoo packages
exceptions = {
    'bs4': 'dev-python/beautifulsoup:4',
    'funcsigs': '',
    'opencv-python': 'media-libs/opencv[python]',
    'scikit-learn': 'dev-python/scikit-learn',
    'scipy': 'dev-python/scipy',
    'tensorflow': 'sci-libs/tensorflow',
    'tensorflow-cpu': 'sci-libs/tensorflow',
    'tensorflow-gpu': 'sci-libs/tensorflow[gpu]',
    'torch' : 'sci-libs/pytorch',
    'tornado': 'www-servers/tornado',
    'urllib3': '',
    'Brotli': 'app-arch/brotli',
    'toml' : '',
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
        'Apache License, Version 2.0': 'Apache-2.0',
        'Apache License 2.0': 'Apache-2.0',
        'MIT License': 'MIT',
	'MIT style': 'MIT'
}

# useless dependencies
use_blackhole = set(('dev', 'doc', 'docs', 'all', 'test', 'testing', 'cuda'))

existing_packages = set()
missing_packages = set()
missing_optional = set()

def get_package_name(package_pypi, optional=False, min_version=None):
    package = package_pypi
    package = package.replace('.', '-')
    if package in exceptions:
        return exceptions[package]
    elif package in renames:
        package = renames[package]

    need_generate = package not in existing_packages
    if not need_generate and min_version:
        # check if any existing version satisfies the constraint
        satisfied = False
        for cpv in portagedb.cp_list('dev-python/{}'.format(package)):
            v = portage.versions.cpv_getversion(cpv)
            if portage.versions.vercmp(v, min_version) >= 0:
                satisfied = True
                break
        if not satisfied:
            print("Package '%s' exists but no version satisfies >=%s" % (package, min_version))
            need_generate = True

    if need_generate:
        if optional:
            if package_pypi not in missing_packages:
                print("Optional package '%s' does not exist" % package)
                missing_optional.add(package_pypi)
        else:
            print("Package '%s' does not exist" % package)
            # a hard dependency trumps an optional sighting
            missing_optional.discard(package_pypi)
            missing_packages.add(package_pypi)
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

def convert_dependency(depend, optional=False):
    # ignore strings after ';'
    depend = depend.split(';')[0].strip()
    # ignore strings after '[', e.g. horovod[torch]
    depend = depend.split('[')[0]
    # handle: package (>=version) or package>=version or package<x,>=y
    match = re.match(r"([^ ><=~!]+)[^>=]*>=\s*([^,\s)]+)", depend)
    if match:
        name = match.group(1)
        version = match.group(2)
        return '>={}-{}[${{PYTHON_USEDEP}}]'.format(get_package_name(name, optional, version), version)
    # handle: package (==version) or package==version
    match = re.match(r"([^ ><=~!]+)[^==]*==\s*([^,\s)]+)", depend)
    if match:
        name = match.group(1)
        version = match.group(2)
        return '={}-{}[${{PYTHON_USEDEP}}]'.format(get_package_name(name, optional), version)
    # strip all exotic (.*), e.g. (~=1-32-0), (~=3-7-4), (<2,>=1-21-1)
    match = re.match("([^ ><=~!]+).*", depend)
    if match:
        name = match.group(1)
        return '{}[${{PYTHON_USEDEP}}]'.format(get_package_name(name, optional))
    else:
        return '{}[${{PYTHON_USEDEP}}]'.format(get_package_name(depend, optional))

def get_iuse_and_depend(project, args):
    requires = project['info']['requires_dist']
    if args.verbose:
        print('requires_dist:')
        for r in requires or []:
            print('  {!r}'.format(r))
    simple = []
    uses = defaultdict(list)
    if requires == None:
        return ''
    for req in requires:
        for rm in removals:
            if rm in req:
                break
        else:
            match = re.match("(.+); (.* and )?extra == ['\"](.+)['\"]", req)
            if match:
                name = match.group(1).strip()
                use = match.group(3)
                if use in use_blackhole:
                    continue
                if name.startswith('types-'):
                    continue
                # when not recursing into optional deps, skip them entirely
                # so IUSE/RDEPEND never reference packages outside the tree
                if not args.optional:
                    continue
                uses[use].append(convert_dependency(name, optional=True))
            else:
                match = re.match('(.+); python_version < "(.+)"', req)
                if match:
                    name = match.group(1).strip()
                    if name.startswith('types-'):
                        continue
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

# Values accepted by Gentoo's distutils-r1.eclass.
backend_mapping = {
    'setuptools.build_meta': 'setuptools',
    'setuptools.build_meta:__legacy__': 'setuptools',
    'poetry.core.masonry.api': 'poetry-core',
    'flit_core.buildapi': 'flit-core',
    'hatchling.build': 'hatchling',
    'pdm.backend': 'pdm-backend',
    'mesonpy': 'meson-python',
    'maturin': 'maturin',
    'flit_scm:buildapi': 'flit-scm',
    'jupyter_packaging.build_api': 'jupyter-packaging',
    'pbr.build': 'pbr',
    'scikit_build_core.build': 'scikit-build-core',
    'sipbuild.api': 'sip',
    'uv_build': 'uv-build',
}

def get_build_backend(project):
    sdist = next(url for url in project['urls'] if url['packagetype'] == 'sdist')
    distfile = Path(portage.settings['DISTDIR']) / sdist['filename']
    if not distfile.exists():
        response = requests.get(sdist['url'])
        response.raise_for_status()
        distfile.write_bytes(response.content)
    archive = io.BytesIO(distfile.read_bytes())

    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as source:
            name = next((name for name in source.namelist()
                         if name.count('/') == 1 and name.endswith('/pyproject.toml')), None)
            pyproject = tomllib.loads(source.read(name).decode()) if name else {}
    else:
        archive.seek(0)
        with tarfile.open(fileobj=archive, mode='r:*') as source:
            member = next((member for member in source.getmembers()
                           if member.isfile() and member.name.count('/') == 1
                           and member.name.endswith('/pyproject.toml')), None)
            pyproject = tomllib.load(source.extractfile(member)) if member else {}
    backend = pyproject.get('build-system', {}).get('build-backend', 'setuptools.build_meta')
    return backend_mapping[backend]

def find_packages(pypi_repo, search_all):
    repodirs = [portagedb.repositories.mainRepoLocation()]
    repodirs += [pypi_repo]
    if search_all:
        for reponame in portagedb.repositories.prepos_order[1:-1]:
            repodir = portagedb.repositories.get_location_for_name(reponame)
            if Path(repodir) != Path(pypi_repo):
                repodirs += [repodir]
    for repodir in repodirs:
        for file in glob.glob(repodir + '/dev-python/**/*.ebuild', recursive=True):
            match = re.match(".*dev-python/(.+)/.*ebuild", file)
            if match:
                existing_packages.add(match.group(1))

    print('Found %d packages in gentoo repo' % len(existing_packages))

def generate(package_pypi, args):
    print('Generating {} to {}'.format(package_pypi, args.repo))
    resp = requests.get("https://pypi.org/pypi/{}/json".format(package_pypi))
    resp.raise_for_status()
    body = json.loads(resp.content)
    backend = get_build_backend(body)

    package = body['info']['name'].replace('.','-')
    if package in renames:
        package = renames[package]
    versions = get_project_python_versions(body)
    compat = ' '.join(['python' + version.replace('.','_') for version in versions])
    print('Python versions', versions)
    homepage = body['info']['home_page']
    if not homepage and body['info'].get('project_urls'):
        homepage = body['info']['project_urls'].get('Homepage')
    print('Homepage', homepage)
    print('Description', body['info']['summary'])
    license = body['info']['license']
    if license in license_mapping:
        license = license_mapping[license]
    print('License', license)
    print('Version', body['info']['version'])
    iuse_and_depend = get_iuse_and_depend(body, args)
    print('IUSE and Depend', iuse_and_depend)

    dir = Path(args.repo) / "dev-python" / package
    path = dir / "{}-{}.ebuild".format(package, body['info']['version'])
    print('Writing to', path)
    dir.mkdir(parents=True, exist_ok=True)
    with path.open('w') as f:
        content = f'# Copyright 1999-{datetime.date.today().year} Gentoo Authors\n'
        content += '# Distributed under the terms of the GNU General Public License v2\n\n'
        content += 'EAPI=8\n\n'
        content += 'DISTUTILS_USE_PEP517={}\n'.format(backend)
        content += 'PYTHON_COMPAT=( {} )\n\n'.format(compat)
        content += 'inherit distutils-r1 pypi\n\n'
        content += 'DESCRIPTION="{}"\n'.format(body['info']['summary'])
        content += 'HOMEPAGE="{}"\n'.format(homepage)
        content += 'LICENSE="{}"\n'.format(license)
        content += 'SLOT="0"\n'
        content += 'KEYWORDS="~amd64"\n\n'
        content += iuse_and_depend
        content += '\ndistutils_enable_tests pytest\n'

        f.write(content)

    if args.manifest:
        os.system('cd %s && pkgdev manifest' % (dir))

    # always record what we generated, so back-references from
    # other packages (e.g. plugin extras) do not trigger regeneration
    existing_packages.add(package)
    missing_packages.discard(package_pypi)
    missing_optional.discard(package_pypi)

    if args.recursive:
        for pkg in list(missing_packages):
            generate(pkg, args)
        if args.optional:
            for pkg in list(missing_optional):
                generate(pkg, args)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--repo', help='set repo directory', default='../gentoo-localrepo')
    parser.add_argument('-v', '--verbose', action='store_true', help='enable verbose logging')
    parser.add_argument('-R', '--recursive', action='store_true', help='generate ebuild recursively')
    parser.add_argument('-o', '--optional', action='store_true', help='with -R, also recurse into optional (extras) dependencies')
    parser.add_argument('-m', '--manifest', action='store_true', help='run "pkgdev manifest" after generation')
    parser.add_argument('-a', '--all-repo', action='store_true', help='search all repos for existing packages including overlays')
    parser.add_argument('packages', nargs='+')
    args = parser.parse_args()

    find_packages(args.repo, args.all_repo)

    # setup repo structure
    metadata = Path(args.repo) / "metadata"
    metadata.mkdir(parents=True, exist_ok=True)
    with (metadata / "layout.conf").open('w') as f:
        f.write("masters = gentoo\nauto-sync = false\n")

    for package in args.packages:
        generate(package, args)

    if missing_optional and not args.optional:
        print('Skipped optional dependencies: {}'.format(', '.join(sorted(missing_optional))))
        print('Rerun with -o to generate them as well.')

if __name__ == "__main__":
    main()
