#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

files=(
  app/cbl/COSGN00C.cbl
  app/cbl/COADM01C.cbl
  app/cbl/COMEN01C.cbl
  app/cbl/COACTVWC.cbl
  app/cbl/COACTUPC.cbl
  app/cbl/COCRDLIC.cbl
  app/cbl/COCRDSLC.cbl
  app/cbl/COCRDUPC.cbl
  app/cbl/COTRN00C.cbl
  app/cbl/COTRN01C.cbl
  app/cbl/COTRN02C.cbl
  app/cbl/COBIL00C.cbl
  app/cbl/CORPT00C.cbl
  app/cbl/GCUSRSEC.cbl
  app/cbl/COUSR00C.cbl
  app/cbl/COUSR01C.cbl
  app/cbl/COUSR02C.cbl
  app/cbl/COUSR03C.cbl
)

if rg -n "EXEC CICS|DFHAID|DFHBMSCA" "${files[@]}"; then
  echo "Non-CICS slice check failed."
  exit 1
fi

echo "Non-CICS slice check passed."
