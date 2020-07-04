import getopt
import sys

def usage():
    print('{}: Generate ebuild for packages on PyPI'.format(sys.argv[0]))
    print('\t-h, --help: display help')
    print('\t-v, --verbose: enable verbose logging')
    print('\t-r, --repo=: set repo directory (default: ../gentoo-localrepo)')

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hr:v", ["help", "repo=", "verbose"])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(1)

    repo = "../gentoo-localrepo"
    verbose = False
    for o, a in opts:
        if o in ("-v", "verbose"):
            verbose = True
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-r", "--repo"):
            repo = a
        else:
            print("unhandled option: {} {}".format(o, a))
            sys.exit(1)



if __name__ == "__main__":
    main()
