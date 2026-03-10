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
  if [[ ! -f "$target_dir/$name" ]]; then
    cp "$seed_dir/$name" "$target_dir/$name"
  fi
done

if [[ ! -f "$target_dir/dateparm.txt" ]]; then
  printf '2022-06-10 2022-06-10\n' > "$target_dir/dateparm.txt"
fi

touch "$target_dir/dailytran_pending.txt"
touch "$target_dir/dalyrejs.txt"
touch "$target_dir/tranrept.txt"
touch "$target_dir/tranrept_requests.txt"

echo "Initialized GNUCobol flat-file runtime in $target_dir"
