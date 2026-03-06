"""
Batch ingest real Synthea FHIR patient data into the application.
Parses FHIR bundles, anonymizes, and stores as JSON for the production app.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'models'))

from fhir_parser import FHIRParser
from anonymizer import EnhancedAnonymizer

def ingest_fhir_directory(fhir_dir: str, output_file: str, limit: int = 50):
    """
    Ingest FHIR bundles from directory, anonymize, and save to JSON.
    
    Args:
        fhir_dir: Path to directory containing FHIR bundle JSON files
        output_file: Path to output JSON file for anonymized patients
        limit: Maximum number of patients to ingest (default 50)
    """
    parser = FHIRParser()
    anonymizer = EnhancedAnonymizer()
    
    fhir_path = Path(fhir_dir)
    if not fhir_path.exists():
        print(f"Error: Directory {fhir_dir} does not exist")
        return
    
    # Get all JSON files
    json_files = list(fhir_path.glob('*.json'))
    # Exclude hospital and practitioner info files
    json_files = [f for f in json_files if 'hospital' not in f.name.lower() and 'practitioner' not in f.name.lower()]
    
    print(f"Found {len(json_files)} FHIR bundle files")
    print(f"Processing up to {limit} patients...")
    
    anonymized_patients = []
    audit_logs = []
    errors = []
    
    for i, fhir_file in enumerate(json_files[:limit]):
        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{min(limit, len(json_files))} patients...")
        
        try:
            with open(fhir_file, 'r', encoding='utf-8') as f:
                bundle = json.load(f)
            
            # Parse FHIR bundle
            patient = parser.parse_bundle(bundle)
            
            # Skip if no meaningful data
            if not patient.get('age') or not patient.get('gender'):
                continue
            
            # Anonymize
            anon_patient = anonymizer.anonymize(patient)
            audit = anonymizer.get_audit_log()
            
            anonymized_patients.append(anon_patient)
            audit_logs.extend(audit)
            
        except Exception as e:
            errors.append({'file': fhir_file.name, 'error': str(e)})
    
    # Save anonymized patients
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(anonymized_patients, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Successfully ingested {len(anonymized_patients)} patients")
    print(f"✓ Saved to: {output_file}")
    print(f"✓ Audit log entries: {len(audit_logs)}")
    
    if errors:
        print(f"\n⚠ Encountered {len(errors)} errors:")
        for err in errors[:5]:
            print(f"  - {err['file']}: {err['error']}")
    
    # Save audit log
    audit_file = output_path.parent / 'ingestion_audit.json'
    with open(audit_file, 'w', encoding='utf-8') as f:
        json.dump(audit_logs, f, indent=2)
    print(f"✓ Audit log saved to: {audit_file}")
    
    return anonymized_patients


if __name__ == '__main__':
    # Configuration
    FHIR_DIR = r'c:\Coherence\synthea_sample_data_fhir_stu3_nov2021\fhir_stu3'
    OUTPUT_FILE = r'c:\Coherence\New folder\python-api\data\real_patients.json'
    LIMIT = 50  # Ingest 50 real patients
    
    print("=" * 60)
    print("FHIR Patient Data Ingestion")
    print("=" * 60)
    
    patients = ingest_fhir_directory(FHIR_DIR, OUTPUT_FILE, LIMIT)
    
    if patients:
        print("\n" + "=" * 60)
        print(f"Sample Patient (Anonymized):")
        print("=" * 60)
        sample = patients[0]
        print(f"  ID: {sample.get('patient_id')}")
        print(f"  Age Range: {sample.get('age_range')}")
        print(f"  Gender: {sample.get('gender')}")
        print(f"  Region: {sample.get('region')}")
        print(f"  Diagnoses: {len(sample.get('diagnosis', []))}")
        print(f"  Medications: {len(sample.get('medications', []))}")
        print(f"  Lab Results: {len(sample.get('lab_results', {}))}")
        print("\n✓ Ingestion complete!")
