#!/usr/bin/env bash
#

HERE="$(cd "$(dirname "$0")"; pwd)"
PROJECT_DIR="$(cd -P "$(dirname "${HERE}/../.." )" && pwd)"

# make sure iroha python is installed
python3 -c 'from iroha import IrohaCrypto' > /dev/null && echo -n '' || pip3 install iroha

# docker-compose down
pushd ${PROJECT_DIR}/docker > /dev/null && docker-compose down; popd > /dev/null

rm -f ${PROJECT_DIR}/keys/*.p*
rm -rf ${PROJECT_DIR}/volumes/*

docker-compose -f ${PROJECT_DIR}/docker/docker-compose.yml up -d
