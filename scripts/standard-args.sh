# Use bash-builtin getopts rather than GNU getopt for cross-platform compatability

DIR="${NAME}"
PROJECT=""
REGISTRY=""
DOCKERFILE="Dockerfile"
TAG=""
CLEAN=true

ParseArgs()
{
    usage() {
        cat <<EOF

Usage: $1 -d <arg> [ -p <args> -r <arg> -f <arg> -k ]

Options:

    -d DIRECTORY    - build DIRECTORY (required)
    -p PROJECT      - used in CI builds - should be set from CI_PROJECT_NAMESPACE
    -r REGISTRY     - if set then push images to REGISTRY - must be logged in already.
    -t TAG          - if set then used as name of image
    -f DOCKERFILE   - Use this as Dockerfile
    -k              - keep temporary files

Not all options are applicable to all scripts, but the same options are
allowed (and ignored) for all scripts

EOF
        exit
    }

    OPTIND=1

    while getopts "d:p:r:f:kt:" arg; do
        case "${arg}" in
            d)
                DIR=${OPTARG}
                ;;
            p)
                PROJECT=${OPTARG}
                ;;
            r)
                REGISTRY=${OPTARG}
                ;;
            f)
                DOCKERFILE=${OPTARG}
                ;;
            t)
                TAG=${OPTARG}
                ;;
            k)
                CLEAN=false
                ;;
            *)
                usage $0
                ;;
        esac
    done

    shift $((OPTIND-1))

}
