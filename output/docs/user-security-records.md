# User Security Records

`CSUSR01Y` defines the authoritative Phase 1 user-security record consumed by the GNUCobol sign-on flow (`COSGN00C`) and user-maintenance utility (`GCUSRSEC`). The runtime file is `app/data/ASCII/usrsec.dat`, with shipped bootstrap rows in `app/data/ASCII.seed/usrsec.dat`.

## Record Layout

- Copybook: `app/cpy/CSUSR01Y.cpy`
- Logical width: `80` bytes
- Physical file behavior: GNUCobol writes `usrsec.dat` as `LINE SEQUENTIAL`, so trailing spaces may be omitted on disk. Parsers should right-pad each line to `80` characters before slicing copybook fields.

| Copybook field | Width | JSON target | Handling |
| --- | ---: | --- | --- |
| `SEC-USR-ID` | 8 | `user_id` | Required. Right-trimmed. Blank values are rejected. |
| `SEC-USR-FNAME` | 20 | `name.first_name` | Required. Right-trimmed. Blank values are rejected because `GCUSRSEC` rejects blank first names. |
| `SEC-USR-LNAME` | 20 | `name.last_name` | Required. Right-trimmed. Blank values are rejected because `GCUSRSEC` rejects blank last names. |
| `SEC-USR-PWD` | 8 | `password` | Required. Right-trimmed. Blank values are rejected because `GCUSRSEC` rejects blank passwords. |
| `SEC-USR-TYPE` | 1 | `user_type_code`, `role` | Required. Supported values are `A` -> `admin` and `U` -> `user`. Any other value is rejected as unsupported. |
| `SEC-USR-FILLER` | 23 | `filler` | Optional. Right-trimmed. All-space values normalize to `null`. |

## Semantics

- Presence of a row means the user is active. The flat-file runtime does not encode a separate inactive or locked status; deleting a user removes the row.
- `COSGN00C` uppercases sign-on input before comparison, and `GCUSRSEC` uppercases passwords and user-type input before writing records. Phase 1 parsing preserves stored values as written rather than re-normalizing them.
- `COSGN00C` authenticates by scanning `usrsec.dat` until it finds a row whose `SEC-USR-ID` equals the uppercased input user ID and whose uppercased stored password equals the uppercased input password.
- On successful sign-on, `COSGN00C` moves `SEC-USR-TYPE` into `CDEMO-USER-TYPE` and routes admins to `COADM01C` while regular users continue to `COMEN01C`; Phase 1 `AuthenticationService` reuses that same user-type resolution and can optionally require a specific role for callers that need admin-only access.
- `GCUSRSEC` rejects blank user IDs, blank first names, blank last names, blank passwords, and user types outside `A` or `U`.
- Durable session issuance is not described by `COSGN00C` or `GCUSRSEC`; the modernization backend therefore treats `operations.sessions` as a lookup-only JSON contract and defers session creation semantics to a later API slice.
- Unsupported user-type values are treated as deterministic parse failures instead of being coerced to a fallback role.
