#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p build

cobc -x -free \
  -I app/cpy \
  -o build/transaction-report \
  app/cbl/CBTRN03C.cbl

cobc -x -free \
  -I app/cpy \
  -o build/post-transactions \
  app/cbl/CBTRN02C.cbl
