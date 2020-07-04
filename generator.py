import argparse
import sys
import json
import requests
import re

supported_python_versions = ['3.5', '3.6']

def get_project_python_versions(project):
    classifiers = project['info']['classifiers']
    res = []
    for classifier in classifiers:
        for version in supported_python_versions:
            if classifier == 'Programming Language :: Python :: {}'.format(version):
                res.append(version)
                break
    return res

def get_depend(project):
    requires = project['info']['requires_dist']
    res = []
    for req in requires:
        match = re.match("(.+) ; extra == '(.+)'", req)
        if match:
            name = match.group(1)
            use = match.group(2)
            res.append('{}? ( dev-python/{} )'.format(use, name))
        else:
            res.append('dev-python/{}'.format(req))
    return 'RDEPEND="' + '\n\t'.join(res) + '"'

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

        print('Python versions', get_project_python_versions(body))
        print('Homepage', body['info']['home_page'])
        print('License', body['info']['license'])
        print('Version', body['info']['version'])
        print('Depend', get_depend(body))

if __name__ == "__main__":
    main()
