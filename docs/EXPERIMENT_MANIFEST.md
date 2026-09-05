# Experiment Manifest

## Study

**Failure Transparency in Android Forensic Parsing Under Schema and Representation Drift: A Controlled ALEAPP Microbenchmark**

This document maps the controlled benchmark conditions to the frozen inputs and reported outcomes.

## Important Reproducibility Note

The controlled database modifications in the reported experiment were performed manually using DB Browser for SQLite 3.13.1. No mutation scripts were executed during the reported study.

The modification descriptions below document the exact experimental changes. The frozen post-modification evidence roots are archived in the accompanying OSF project and should be treated as the authoritative experimental inputs.

## Condition Map

| ID | Artifact | Starting point | Controlled change | Expected artifacts | ALEAPP result | Guard |
|---|---|---|---|---:|---|---|
| C0 | Contacts | Synthetic baseline | None | 20 | 20 recovered | PASS |
| C1 | Contacts | Fresh C0 baseline | Added unused column to `wa_contacts` | 20 | 20 recovered | PASS |
| C2 | Contacts | Fresh C0 baseline | Renamed `given_name` to `first_name` | 20 | 0 recovered; `No data found` | FAIL |
| C-Empty | Contacts | Fresh C0 baseline | Deleted all contact rows while retaining supported schema | 0 | `No data found` | PASS |
| C3 | Contacts | Fresh C0 baseline | Renamed `wa_contacts` table | 20 | 0 recovered; `No data found` | FAIL |
| M0 | Messages | Synthetic baseline | None | 20 | 20 recovered | PASS |
| M1 | Messages | Fresh M0 baseline | Added `participant_jid_row_id`; migrated 5 relationships away from `jid_row_id` | 20 | 15 recovered | WARN |
| M2 | Messages | Fresh M0 baseline | Converted timestamp representation for 5 messages from milliseconds to seconds | 20 | 20 recovered; 5 timestamp errors | WARN |

## Contacts Conditions

### C0 — Supported baseline
Baseline `wa.db` containing 20 synthetic Contacts records matching the columns required by the tested ALEAPP Contacts artifact.

### C1 — Additive column
An unused column was added to `wa_contacts`. Existing required tables, columns, and records remained available.

Purpose: determine whether a non-breaking additive schema change affects extraction.

### C2 — Referenced column rename
`given_name` was renamed to `first_name`.

Purpose: violate a fixed referenced-column assumption while retaining the 20 underlying contact records.

Observed result: ALEAPP returned no Contacts records and displayed `No data found` without a schema-specific diagnostic.

### C-Empty — Valid empty control
All rows were removed from the supported Contacts schema.

Purpose: represent genuine artifact absence.

Observed result: ALEAPP displayed the same `No data found` message seen in C2 and C3.

### C3 — Referenced table rename
The `wa_contacts` table was renamed while the underlying contact records remained present.

Purpose: violate the tested parser's fixed table-name assumption.

Observed result: ALEAPP returned no Contacts records and displayed `No data found` without a schema-specific diagnostic.

## Message Conditions

### M0 — Supported baseline
Baseline `msgstore.db` and `wa.db` containing 20 synthetic One-to-One Messages with known message text, participant, direction, JID, and timestamps.

Expected relationship chain:

`message → chat → jid → wa_contacts`

### M1 — Structural relationship drift
A new `participant_jid_row_id` field was introduced and 5 of 20 relationships were migrated from the relationship expected by the fixed parser.

The 5/20 split was selected to produce an observable partial-failure condition while retaining 15 unaffected records as an internal comparison set.

Observed result:
- expected: 20
- retrieved: 15
- false negatives: 5
- artifact recall: 75%
- retrieved records otherwise correct
- no examiner-visible incompleteness diagnostic

### M2 — Timestamp representation drift
The timestamp representation for 5 of 20 messages was changed from milliseconds to seconds.

The mixed representation was a controlled representation-mismatch test and is not claimed to reproduce a documented WhatsApp release migration.

Observed result:
- expected: 20
- retrieved: 20
- artifact recall: 100%
- timestamp correctness: 15/20
- 5 timestamps semantically misinterpreted
- no examiner-visible representation warning

## Materially Incorrect Conditions

The materially incorrect conditions were:

- C2
- C3
- M1
- M2

ALEAPP meaningful reliability diagnostic: **0/4**

Proof-of-concept forensic guard flagged: **4/4**

These counts apply only to the controlled benchmark and are not estimates of general detection sensitivity.

## Authoritative Archived Inputs

The accompanying OSF project contains the exact evidence-root ZIPs, ALEAPP result packages, guard JSON outputs, ground-truth files, `master_results.csv`, and SHA-256 manifest used to support the reported results.

OSF project: https://osf.io/m72qr/
