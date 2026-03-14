# Phase 1 Source Artifacts

## Authority

For Phase 1, the GNUCobol flat-file runtime is the authoritative source of business data behavior. Use `app/cbl`, `app/cpy`, `app/data/ASCII`, `app/data/ASCII.seed`, and the local GNUCobol helper scripts before consulting the legacy CICS runtime or optional DB2/IMS/MQ variants.

## Copybooks, Files, And Consumers

| Entity family | Copybook | Record purpose | Runtime file(s) | Seed/bootstrap file(s) | Current GNUCobol consumers |
| :-- | :-- | :-- | :-- | :-- | :-- |
| User security | `app/cpy/CSUSR01Y.cpy` | User security record | `app/data/ASCII/usrsec.dat` | `app/data/ASCII.seed/usrsec.dat` | `COSGN00C` login flow; `CBIMPORT.cbl` for flat-file import |
| Customer | `app/cpy/CVCUS01Y.cpy` | Customer master record | `app/data/ASCII/custdata.txt` | `app/data/ASCII.seed/custdata.txt` | `CBCUS01C.cbl`, `CBTRN01C.cbl`, `CBIMPORT.cbl`, `CBEXPORT.cbl` |
| Account | `app/cpy/CVACT01Y.cpy` | Account master record | `app/data/ASCII/acctdata.txt` | `app/data/ASCII.seed/acctdata.txt` | `CBACT01C.cbl`, `CBACT04C.cbl`, `CBSTM03A.CBL`, `CBTRN01C.cbl`, `CBIMPORT.cbl`, `CBEXPORT.cbl` |
| Card | `app/cpy/CVACT02Y.cpy` | Card record | `app/data/ASCII/carddata.txt` | `app/data/ASCII.seed/carddata.txt` | `CBACT02C.cbl`, `CBTRN01C.cbl`, `CBIMPORT.cbl`, `CBEXPORT.cbl` |
| Card/account cross-reference | `app/cpy/CVACT03Y.cpy` | Card-to-account/customer cross-reference | `app/data/ASCII/cardxref.txt` | `app/data/ASCII.seed/cardxref.txt` | `CBACT03C.cbl`, `CBACT04C.cbl`, `CBSTM03A.CBL`, `CBTRN01C.cbl`, `CBIMPORT.cbl`, `CBEXPORT.cbl` |
| Transaction category balance | `app/cpy/CVTRA01Y.cpy` | Per-account transaction-category balance | `app/data/ASCII/tcatbal.txt` | `app/data/ASCII.seed/tcatbal.txt` | `CBACT04C.cbl`, `CBTRN02C.cbl` |
| Disclosure group | `app/cpy/CVTRA02Y.cpy` | Disclosure-group lookup | `app/data/ASCII/discgrp.txt` | `app/data/ASCII.seed/discgrp.txt` | `CBACT04C.cbl` |
| Transaction type | `app/cpy/CVTRA03Y.cpy` | Transaction-type lookup | `app/data/ASCII/trantype.txt` | `app/data/ASCII.seed/trantype.txt` | `CBTRN03C.cbl` |
| Transaction category | `app/cpy/CVTRA04Y.cpy` | Transaction-category lookup | `app/data/ASCII/trancatg.txt` | `app/data/ASCII.seed/trancatg.txt` | `CBTRN03C.cbl` |
| Online transaction event | `app/cpy/CVTRA05Y.cpy` | Posted transaction record | `app/data/ASCII/dailytran.txt` in the flat-file runtime, replacing the original VSAM-backed online store | No separate shipped seed file; Phase 1 bootstrap should derive runtime data from the shipped transaction inputs and deterministic initialization rules | `CBACT04C.cbl`, `CBTRN01C.cbl`, `CBIMPORT.cbl`, `CBEXPORT.cbl`, `COBIL00C.cbl`, `COTRN00C.cbl`, `COTRN01C.cbl`, `COTRN02C.cbl` |
| Daily transaction input | `app/cpy/CVTRA06Y.cpy` | Batch posting transaction input record | `app/data/ASCII/dailytran.txt` | `app/data/ASCII.seed/dailytran.txt` | `CBTRN01C.cbl` and Phase 1 bootstrap/import work |
| Transaction report layout | `app/cpy/CVTRA07Y.cpy` | Report rendering layout for transaction reports | No standalone flat file; used as an authoritative record-layout reference for report output formatting | None | No current `COPY CVTRA07Y` consumer was found in `app/cbl`; keep it as an authoritative Phase 1 layout reference because the copybook exists in the flat-file source set and Phase 1 must account for `CVTRA07Y` |

## Seed And Runtime Files

Phase 1 bootstrap seed inputs under `app/data/ASCII.seed`:

- `acctdata.txt`
- `carddata.txt`
- `cardxref.txt`
- `custdata.txt`
- `dailytran.txt`
- `discgrp.txt`
- `tcatbal.txt`
- `trancatg.txt`
- `trantype.txt`
- `usrsec.dat`

Related runtime-managed files under `app/data/ASCII` that Phase 1 must preserve in the store contract even when seed data is empty or script-initialized:

- `dateparm.txt`
- `tranrept_requests.txt`
- `dailytran.txt`
- `dailytran_pending.txt` when initialized by script

`tranrept_requests.txt` and `dateparm.txt` are managed by `CORPT00C.cbl`. `tranrept_requests.txt` should be treated as empty-by-default operational data when no requests exist. `dailytran_pending.txt` is created by the runtime scripts and consumed by posting logic in `CBTRN02C.cbl`.

## Reset, Init, And Validation Scripts

Scripts in `scripts/` that Phase 1 should treat as authoritative helpers for flat-file bootstrap behavior:

- `scripts/init_gnucobol_data.sh`: populates `app/data/ASCII` from `app/data/ASCII.seed`, initializes `dateparm.txt`, and creates empty runtime files such as `dailytran_pending.txt` and `tranrept_requests.txt`
- `scripts/reset_gnucobol_data.sh`: restores the same runtime files back to a known seed baseline
- `scripts/build_gnucobol_runtime.sh`: compiles the flat-file GNUCobol runtime used as the execution baseline
- `scripts/check_non_cics_slice.sh`: verifies the non-CICS GNUCobol slice includes the expected flat-file runtime programs

## Phase 1 Implementation Notes

- Treat the copybooks above as the canonical record-layout definitions for Phase 1 models and fixed-width parsing.
- Prefer the flat-file files in `app/data/ASCII` for current runtime semantics and `app/data/ASCII.seed` for deterministic bootstrap inputs.
- Do not infer missing behavior from optional DB2, IMS, MQ, or legacy CICS variants when the flat-file runtime already defines the same domain area.
