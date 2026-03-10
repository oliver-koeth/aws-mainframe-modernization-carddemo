#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

target_dir="${1:-app/data/ASCII}"
seed_dir="app/data/ASCII.seed"

seed_files=(
  acctdata.txt
  carddata.txt
  cardxref.txt
  custdata.txt
  dailytran.txt
  discgrp.txt
  tcatbal.txt
  trancatg.txt
  trantype.txt
  usrsec.dat
)

mkdir -p "$target_dir"

for name in "${seed_files[@]}"; do
  cp "$seed_dir/$name" "$target_dir/$name"
done

printf '2022-06-10 2022-06-10\n' > "$target_dir/dateparm.txt"
: > "$target_dir/dailytran_pending.txt"
: > "$target_dir/dalyrejs.txt"
: > "$target_dir/tranrept.txt"
: > "$target_dir/tranrept_requests.txt"

echo "Reset GNUCobol flat-file runtime in $target_dir"
