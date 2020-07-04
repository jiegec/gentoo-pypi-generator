import argparse
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--repo', help='set repo directory', default='../gentoo-localrepo')
    parser.add_argument('-v', '--verbose', action='store_true', help='enable verbose logging')
    args = parser.parse_args()

if __name__ == "__main__":
    main()
