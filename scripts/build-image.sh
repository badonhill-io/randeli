#! /bin/sh

topdir=$( cd "$( dirname "$0" )/../" && pwd )

NAME=randeli

date=date

if [ "$(uname -s)" == "Darwin" ]; then
    date=gdate
fi

# process the options

. ${topdir}/scripts/standard-args.sh
ParseArgs $*

if [ -n "${REGISTRY}" ]
then
    PULL=--pull
fi

set -x
set -euo pipefail

docker buildx build --progress plain -o type=image -t ${NAME}:${TAG} .
st=$?
docker image ls "${NAME}"
set +x
exit $st
