# GNUCobol Runtime

This repository now contains a runnable non-CICS base-application path for the migrated slices.

## Scope

The GNUCobol runtime currently covers these base-app online flows:

- sign-on
- admin menu and user security maintenance
- user menu
- account view and update
- card list, view, and update
- transaction list, view, and add
- bill payment
- transaction report request launcher

It also includes a local batch runner for transaction report generation.

These programs are built as a standalone console application and use flat files in `app/data/ASCII`.

Legacy CICS/BMS programs and JCL setup remain in the repository for the original mainframe runtime, but they are not required for the GNUCobol path.

## Build

Use the canonical runtime build script:

```bash
bash scripts/build_gnucobol_runtime.sh
```

This produces:

```text
build/carddemo-admin
```

The older `scripts/build_gnucobol_admin.sh` script is kept as a compatibility wrapper and forwards to the runtime build script.

Build the migrated batch report separately with:

```bash
bash scripts/build_gnucobol_batch.sh
```

This produces:

```text
build/transaction-report
build/post-transactions
```

## Run

Start the console runtime:

```bash
build/carddemo-admin
```

Default credentials:

- admin: `ADMIN001` / `PASSWORD`
- user: `USER0001` / `PASSWORD`

## Initialize Or Reset Data

The GNUCobol runtime now has a committed flat-file seed set in `app/data/ASCII.seed`.

Initialize a new data directory from the seed:

```bash
bash scripts/init_gnucobol_data.sh
```

Reset the active runtime data back to the seed baseline:

```bash
bash scripts/reset_gnucobol_data.sh
```

Both scripts accept an optional target directory argument if you want to initialize or reset a disposable copy for testing.

## Data Files

By default the runtime uses these flat files:

- `app/data/ASCII/usrsec.dat`
- `app/data/ASCII/acctdata.txt`
- `app/data/ASCII/custdata.txt`
- `app/data/ASCII/carddata.txt`
- `app/data/ASCII/cardxref.txt`
- `app/data/ASCII/dailytran.txt`
- `app/data/ASCII/dailytran_pending.txt`
- `app/data/ASCII/dalyrejs.txt`
- `app/data/ASCII/tcatbal.txt`

Optional environment overrides:

- `CARDDEMO_ACCT_PATH`
- `CARDDEMO_CUST_PATH`
- `CARDDEMO_CARD_PATH`
- `CARDDEMO_XREF_PATH`
- `CARDDEMO_TRAN_PATH`
- `CARDDEMO_PENDING_TRAN_PATH`
- `CARDDEMO_REPORT_REQUEST_PATH`
- `CARDDEMO_DATEPARM_PATH`
- `CARDDEMO_TRANTYPE_PATH`
- `CARDDEMO_TRANCATG_PATH`
- `CARDDEMO_TCATBAL_PATH`
- `CARDDEMO_REJECT_PATH`
- `CARDDEMO_REPORT_OUTPUT_PATH`

## Report Launcher

The non-CICS report launcher writes file-backed artifacts instead of using a CICS TD queue:

- `app/data/ASCII/dateparm.txt`
- `app/data/ASCII/tranrept_requests.txt`

Those files are created on demand when a report request is submitted.

Run the migrated batch report with:

```bash
build/transaction-report
```

By default it reads `app/data/ASCII/dateparm.txt` and writes `app/data/ASCII/tranrept.txt`.

For the shipped sample transaction file, records are dated `2022-06-10`, so a matching `dateparm.txt` range is required to produce report output.

Run the migrated transaction posting batch with:

```bash
build/post-transactions
```

By default it:

- reads pending rows from `app/data/ASCII/dailytran_pending.txt`
- appends posted rows to `app/data/ASCII/dailytran.txt`
- rewrites `app/data/ASCII/acctdata.txt`
- rewrites `app/data/ASCII/tcatbal.txt`
- writes rejects to `app/data/ASCII/dalyrejs.txt`

The pending queue is cleared after the batch run, so use a disposable copy if you want to rerun the same input repeatedly during testing.

## Verification

Check that the migrated runtime slice stays free of required CICS dependencies:

```bash
bash scripts/check_non_cics_slice.sh
```

This verifies that the active GNUCobol runtime sources do not contain `EXEC CICS`, `DFHAID`, or `DFHBMSCA`.
