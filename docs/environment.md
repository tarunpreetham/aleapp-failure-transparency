# Experimental Environment

## Forensic Tool

- **Tool:** Android Logs Events And Protobuf Parser (ALEAPP)
- **Version:** `v2026.3.2-dev`
- **Commit:** `18a1c4c6e20c55aefd7ddc0c2d8d5007d8bb26fa`
- **Upstream repository:** https://github.com/abrignoni/ALEAPP
- **Test dates:** September 1–2, 2026

## System

- **Operating system:** Windows 11 Pro
- **Device:** Dell Precision 7760
- **Processor:** Intel Xeon W-11955M @ 2.60 GHz

## Software

- **Python:** 3.12.10
- **Windows PowerShell:** 5.1.26100.9278
- **DB Browser for SQLite:** 3.13.1
- **Visual Studio Code:** 1.136.0
- **VS Code commit:** `520fb30b2d3d324b4cb2342f6e88e2cd93751de1`

## Experimental Consistency

The same workstation, pinned ALEAPP revision, and software environment were retained across the supported baselines and controlled test conditions.

Each condition was executed once using a fixed database input and the pinned ALEAPP revision. Between-run variability was not evaluated.

## Database Modification

The controlled database changes were performed manually with DB Browser for SQLite 3.13.1. No mutation scripts were used during the reported experiment.

See `EXPERIMENT_MANIFEST.md` for the exact condition-level modifications.

## ALEAPP Reproduction

```bash
git clone https://github.com/abrignoni/ALEAPP.git
cd ALEAPP
git checkout 18a1c4c6e20c55aefd7ddc0c2d8d5007d8bb26fa
```

Install dependencies according to the ALEAPP instructions associated with the pinned revision.

## Archived Environment Record

The OSF reproducibility package contains the frozen environment metadata and SHA-256 manifest associated with the study.

OSF project: https://osf.io/m72qr/
