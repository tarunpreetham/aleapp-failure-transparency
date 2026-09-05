# ALEAPP Failure Transparency Microbenchmark

This repository contains the code and reproducibility documentation for the study: **Failure Transparency in Android Forensic Parsing Under Schema and Representation Drift: A Controlled ALEAPP Microbenchmark**

The study evaluates whether selected Android Logs Events And Protobuf Parser (ALEAPP) WhatsApp artifact parsers provide an examiner-visible indication when controlled database changes cause incomplete extraction or semantic misinterpretation.

## Repository Role

This GitHub repository is the maintained code repository for the project.

- **Research Square:** manuscript / preprint
- **OSF:** frozen reproducibility package, synthetic evidence, raw results, hashes, and archival materials
- **GitHub:** maintained source code, baseline generators, and experiment documentation

OSF project: https://osf.io/m72qr/

Research Square preprint: 

## Tested ALEAPP Revision

- ALEAPP version: `v2026.3.2-dev`
- Commit: `18a1c4c6e20c55aefd7ddc0c2d8d5007d8bb26fa`
- Upstream repository: https://github.com/abrignoni/ALEAPP
- Test dates: September 1–2, 2026

## Code in This Repository

```text
.
├── README.md
├── CITATION.cff
├── LICENSE
├── requirements.txt
├── forensic_guard.py
├── generators/
│   ├── generate_C0_contacts_baseline.py
│   └── generate_M0_messages_baseline.py
└── docs/
    ├── EXPERIMENT_MANIFEST.md
    └── environment.md
```

The controlled database changes used in the study were performed manually with DB Browser for SQLite. No mutation scripts were used during the reported experiment. The exact modifications are documented in `docs/EXPERIMENT_MANIFEST.md` and in the accompanying OSF reproducibility package.

## Experimental Conditions

| ID | Artifact | Condition | Ground truth | Observed ALEAPP result |
|---|---|---|---:|---|
| C0 | Contacts | Supported baseline | 20 | 20/20 recovered |
| C1 | Contacts | Additive unused column | 20 | 20/20 recovered |
| C2 | Contacts | `given_name` renamed to `first_name` | 20 | 0/20 recovered |
| C-Empty | Contacts | Valid schema with zero rows | 0 | `No data found` |
| C3 | Contacts | `wa_contacts` table renamed | 20 | 0/20 recovered |
| M0 | Messages | Supported baseline | 20 | 20/20 recovered |
| M1 | Messages | Structural relationship drift | 20 | 15/20 recovered |
| M2 | Messages | Timestamp representation drift | 20 | 20/20 recovered; 5 timestamps incorrect |

Across the four materially incorrect constructed conditions (`C2`, `C3`, `M1`, and `M2`), ALEAPP provided a meaningful examiner-visible reliability diagnostic in `0/4` conditions. The proof-of-concept forensic guard flagged `4/4`.

These counts describe only the controlled benchmark and are not estimates of general detection sensitivity.

## Forensic Guard

`forensic_guard.py` is a proof-of-concept pre-parsing validation tool. It checks selected assumptions required by the tested ALEAPP artifacts:

- required tables and columns;
- expected message relationships; and
- timestamp representation.

It does **not**:

- modify evidence;
- recover omitted artifacts;
- automatically remap schemas;
- replace ALEAPP; or
- function as a general schema-drift detector.

### Guard outcomes

- `FAIL` — a required structural assumption is violated.
- `WARN` — a relationship or representation anomaly is detected without a structural failure.
- `PASS` — none of the tested assumptions are violated.

The guard was developed after the parser assumptions exercised by the benchmark had been identified. No held-out drift conditions were used to independently estimate detection sensitivity.

## Baseline Generators

`generators/generate_C0_contacts_baseline.py` - 
Creates the synthetic Contacts baseline used for C0 and its associated ground-truth records.

`generators/generate_M0_messages_baseline.py` - 
Creates the synthetic One-to-One Messages baseline used for M0 and its associated ground-truth records.

The exact synthetic databases used in the reported study are archived in the OSF reproducibility package. Researchers reproducing the published benchmark should use those frozen files when exact input identity is required.

## Reproducing the ALEAPP Environment

Clone ALEAPP and check out the exact tested revision:

```bash
git clone https://github.com/abrignoni/ALEAPP.git
cd ALEAPP
git checkout 18a1c4c6e20c55aefd7ddc0c2d8d5007d8bb26fa
```

Install ALEAPP according to the instructions associated with that revision.

See `docs/environment.md` for the recorded test environment.

## Running the Forensic Guard

Contacts example:

```powershell
python forensic_guard.py --wa "PATH\TO\wa.db"
```

One-to-One Messages example:

```powershell
python forensic_guard.py --wa "PATH\TO\wa.db" --msg "PATH\TO\msgstore.db"
```

The raw guard JSON outputs used in the paper are archived on OSF.

## Evidence, Ground Truth, and Raw Results

Large/frozen research artifacts are maintained on OSF rather than duplicated here. The OSF package includes:

- synthetic ground-truth CSV files;
- exact evidence-root ZIPs for C0–C3, C-Empty, M0–M2;
- ALEAPP result ZIPs;
- forensic-guard JSON outputs;
- `master_results.csv`;
- SHA-256 integrity manifest; and
- environment metadata.

OSF project: https://osf.io/m72qr/

## Limitations

This repository supports a small controlled microbenchmark using two selected ALEAPP WhatsApp artifact parsers and synthetic evidence. The controlled conditions are parser-assumption violations and are not claimed to reproduce exact schema migrations from a specific WhatsApp release.

The forensic guard is a proof-of-concept developed around the assumptions exercised in the benchmark and should not be interpreted as an independently validated detector of unseen schema or representation changes.

## Citation

If you use this code or benchmark, please cite the associated preprint. See `CITATION.cff` for machine-readable citation metadata.

## License

Code in this GitHub repository is released under the MIT License. See `LICENSE`.

Synthetic datasets, archived experimental results, and accompanying research documentation deposited on OSF are released under the license stated on the OSF project.

## Acknowledgment

ALEAPP is developed by Alexis Brignoni and contributors. This project evaluates selected artifact behavior at the exact revision identified above and is not affiliated with or endorsed by the ALEAPP project.
