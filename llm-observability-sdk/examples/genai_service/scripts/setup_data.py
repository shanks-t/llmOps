#!/usr/bin/env python3
"""
setup_data.py

Upload Synthea FHIR data to GCS and create patient index.

Usage:
    uv run python scripts/setup_data.py
    uv run python scripts/setup_data.py --dry-run
    uv run python scripts/setup_data.py --project=my-project --bucket=my-bucket
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()


def get_patient_info(bundle: dict, patient_id: str) -> dict:
    """Extract patient info from FHIR bundle.

    Args:
        bundle: FHIR bundle dict.
        patient_id: Patient ID (filename stem).

    Returns:
        Patient info dict with id, name, gender, birth_date, age.
    """
    patient_resource = None
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            patient_resource = resource
            break

    if not patient_resource:
        return {
            "id": patient_id,
            "name": "Unknown",
            "gender": "unknown",
            "birth_date": "unknown",
            "age": 0,
        }

    # Extract name
    name = "Unknown"
    names = patient_resource.get("name", [])
    if names:
        first_name = names[0]
        if "text" in first_name:
            name = first_name["text"]
        else:
            given = first_name.get("given", [])
            family = first_name.get("family", "")
            if given and family:
                name = f"{given[0]} {family}"
            elif family:
                name = family
            elif given:
                name = given[0]

    # Extract gender
    gender = patient_resource.get("gender", "unknown")

    # Extract birth date and calculate age
    birth_date_str = patient_resource.get("birthDate", "")
    age = 0
    if birth_date_str:
        try:
            birth_date = date.fromisoformat(birth_date_str)
            today = date.today()
            age = today.year - birth_date.year
            if (today.month, today.day) < (birth_date.month, birth_date.day):
                age -= 1
        except ValueError:
            birth_date_str = "unknown"

    return {
        "id": patient_id,
        "name": name,
        "gender": gender,
        "birth_date": birth_date_str or "unknown",
        "age": age,
    }


def run_gcloud(
    args: list[str], project_id: str, dry_run: bool = False, capture_output: bool = False
) -> subprocess.CompletedProcess | None:
    """Run a gcloud command.

    Args:
        args: Command arguments (without 'gcloud').
        project_id: GCP project ID.
        dry_run: If True, print command instead of executing.
        capture_output: If True, capture and return output.

    Returns:
        CompletedProcess if executed, None if dry_run.

    Raises:
        subprocess.CalledProcessError: If command fails.
    """
    cmd = ["gcloud"] + args + [f"--project={project_id}"]

    if dry_run:
        print(f"[DRY RUN] {' '.join(cmd)}")
        return None

    return subprocess.run(cmd, check=True, capture_output=capture_output, text=True)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Upload Synthea FHIR data to GCS and create patient index."
    )
    parser.add_argument("--project", help="GCP project ID (default: GCS_PROJECT_ID env var)")
    parser.add_argument("--bucket", help="GCS bucket name (default: GCS_BUCKET_NAME env var)")
    parser.add_argument(
        "--synthea-dir",
        type=Path,
        default=Path(__file__).parent.parent / "synthea_output",
        help="Path to Synthea output directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing",
    )
    args = parser.parse_args()

    # Resolve configuration
    project_id = args.project or os.getenv("GCS_PROJECT_ID")
    bucket_name = args.bucket or os.getenv("GCS_BUCKET_NAME")

    if not project_id:
        print("ERROR: GCS_PROJECT_ID not set. Use --project or set GCS_PROJECT_ID env var.")
        return 1
    if not bucket_name:
        print("ERROR: GCS_BUCKET_NAME not set. Use --bucket or set GCS_BUCKET_NAME env var.")
        return 1

    synthea_dir = args.synthea_dir.resolve()
    fhir_dir = synthea_dir / "fhir"

    if not fhir_dir.exists():
        print(f"ERROR: FHIR directory not found: {fhir_dir}")
        return 1

    # Find patient FHIR files (exclude practitioner and hospital info)
    fhir_files = sorted(
        f
        for f in fhir_dir.glob("*.json")
        if not f.name.startswith(("practitioner", "hospital"))
    )

    if not fhir_files:
        print(f"ERROR: No patient FHIR files found in {fhir_dir}")
        return 1

    print(f"Found {len(fhir_files)} patient FHIR files")
    print(f"Project: {project_id}")
    print(f"Bucket: gs://{bucket_name}")
    print()

    # Build index
    index_entries = []
    patient_files: list[tuple[Path, str]] = []

    for i, fhir_file in enumerate(fhir_files, start=1):
        patient_id = f"patient-{i:03d}"
        print(f"Processing {fhir_file.name} -> {patient_id}.json")

        with open(fhir_file) as f:
            bundle = json.load(f)

        patient_info = get_patient_info(bundle, patient_id)
        index_entries.append(patient_info)
        patient_files.append((fhir_file, patient_id))

    print()
    print("Patient index:")
    for entry in index_entries:
        print(f"  {entry['id']}: {entry['name']} ({entry['gender']}, {entry['age']} y/o)")

    # Write index to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        json.dump(index_entries, tmp, indent=2)
        index_path = tmp.name

    print()
    print("Uploading files to GCS...")

    try:
        # Upload patient files to raw/
        for fhir_file, patient_id in patient_files:
            dest = f"gs://{bucket_name}/raw/{patient_id}.json"
            run_gcloud(
                ["storage", "cp", str(fhir_file), dest],
                project_id,
                dry_run=args.dry_run,
            )

        # Upload index
        run_gcloud(
            ["storage", "cp", index_path, f"gs://{bucket_name}/index.json"],
            project_id,
            dry_run=args.dry_run,
        )

        # Create summaries/.keep placeholder
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp.write("")
            keep_path = tmp.name

        run_gcloud(
            ["storage", "cp", keep_path, f"gs://{bucket_name}/summaries/.keep"],
            project_id,
            dry_run=args.dry_run,
        )
        os.unlink(keep_path)

        # Validate uploads
        if not args.dry_run:
            print()
            print("Validating uploads...")
            result = run_gcloud(
                ["storage", "ls", f"gs://{bucket_name}/"],
                project_id,
                capture_output=True,
            )
            if result:
                print(result.stdout)

        print()
        print("Done!" if not args.dry_run else "Dry run complete.")
        return 0

    finally:
        # Clean up temp index file
        if os.path.exists(index_path):
            os.unlink(index_path)


if __name__ == "__main__":
    sys.exit(main())
