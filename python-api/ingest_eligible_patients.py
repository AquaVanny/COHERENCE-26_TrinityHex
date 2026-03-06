"""
Find and ingest patients from FHIR dataset that match trial eligibility criteria.
Prioritizes patients with good matches for demonstration purposes.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'models'))

from fhir_parser import FHIRParser
from anonymizer import EnhancedAnonymizer
from criteria_parser import CriteriaParser
from matching_engine import MatchingEngine

def find_eligible_patients(fhir_dir: str, trials_file: str, output_file: str, target_count: int = 250):
    """
    Find patients from FHIR dataset that have good matches with trials.
    
    Target profiles:
    - Diabetes patients (18-75, on metformin, HbA1c 7-10.5)
    - Breast cancer patients (female, 18-70, early stage)
    - Alzheimer's patients (55-85, mild-moderate)
    - Asthma patients (12-65, severe persistent)
    - Cardiovascular risk patients (40-80, diabetes)
    
    Also includes patients with partial matches for variety.
    """
    parser = FHIRParser()
    anonymizer = EnhancedAnonymizer()
    criteria_parser = CriteriaParser()
    matching_engine = MatchingEngine()
    
    # Load trials
    with open(trials_file, 'r') as f:
        trials = json.load(f)
    
    fhir_path = Path(fhir_dir)
    json_files = list(fhir_path.glob('*.json'))
    json_files = [f for f in json_files if 'hospital' not in f.name.lower() and 'practitioner' not in f.name.lower()]
    
    print(f"Scanning {len(json_files)} FHIR bundles for eligible patients...")
    print(f"Target: {target_count} patients with good trial matches\n")
    
    eligible_patients = []
    match_scores = []
    
    for i, fhir_file in enumerate(json_files):
        if len(eligible_patients) >= target_count:
            break
            
        if (i + 1) % 50 == 0:
            print(f"  Scanned {i + 1} files, found {len(eligible_patients)} eligible patients...")
        
        try:
            with open(fhir_file, 'r', encoding='utf-8') as f:
                bundle = json.load(f)
            
            # Parse FHIR
            patient = parser.parse_bundle(bundle)
            
            # Skip if missing critical data
            if not patient.get('age') or not patient.get('gender'):
                continue
            
            # Quick eligibility check
            age = patient.get('age', 0)
            diagnoses = [d.lower() for d in patient.get('diagnosis', [])]
            meds = [m.lower() for m in patient.get('medications', [])]
            
            # Check if patient matches any trial criteria
            # Relaxed criteria to get more patients with varying match quality
            is_eligible = False
            best_score = 0
            
            # Diabetes trial (18-75, diabetes)
            if 18 <= age <= 75 and any('diabetes' in d for d in diagnoses):
                is_eligible = True
                best_score = max(best_score, 0.6)
            
            # Breast cancer (female, 18-70, cancer/neoplasm)
            if patient.get('gender') == 'female' and 18 <= age <= 70 and any('cancer' in d or 'neoplasm' in d or 'malignant' in d for d in diagnoses):
                is_eligible = True
                best_score = max(best_score, 0.6)
            
            # Alzheimer's (55-85, dementia/alzheimer's/cognitive)
            if 55 <= age <= 85 and any('alzheimer' in d or 'dementia' in d or 'cognitive' in d for d in diagnoses):
                is_eligible = True
                best_score = max(best_score, 0.6)
            
            # Asthma (12-65, asthma/respiratory)
            if 12 <= age <= 65 and any('asthma' in d or 'bronchial' in d for d in diagnoses):
                is_eligible = True
                best_score = max(best_score, 0.6)
            
            # Cardiovascular (40-80, diabetes OR cardiovascular conditions)
            if 40 <= age <= 80:
                has_diabetes = any('diabetes' in d for d in diagnoses)
                has_cardio = any('hypertension' in d or 'heart' in d or 'cardio' in d or 'coronary' in d for d in diagnoses)
                if has_diabetes and has_cardio:
                    is_eligible = True
                    best_score = max(best_score, 0.75)
                elif has_diabetes or has_cardio:
                    is_eligible = True
                    best_score = max(best_score, 0.5)
            
            # Also include patients with chronic conditions for variety
            if not is_eligible and len(diagnoses) >= 5:
                if any('chronic' in d or 'disorder' in d for d in diagnoses):
                    is_eligible = True
                    best_score = 0.3
            
            if is_eligible:
                # Anonymize
                anon_patient = anonymizer.anonymize(patient)
                
                # Run full matching to get actual score
                raw_matches = matching_engine.match_all_trials(anon_patient, trials, criteria_parser)
                if raw_matches:
                    top_score = raw_matches[0].get('fused_score', 0)
                    best_score = max(best_score, top_score)
                
                eligible_patients.append(anon_patient)
                match_scores.append({
                    'patient_id': anon_patient['patient_id'],
                    'age_range': anon_patient.get('age_range'),
                    'diagnoses': len(anon_patient.get('diagnosis', [])),
                    'best_match_score': round(best_score, 3),
                    'top_trial': raw_matches[0]['title'] if raw_matches else 'None'
                })
                
        except Exception as e:
            continue
    
    # Save eligible patients
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(eligible_patients, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Found {len(eligible_patients)} eligible patients")
    print(f"✓ Saved to: {output_file}\n")
    
    # Show match summary
    print("=" * 70)
    print("ELIGIBLE PATIENT SUMMARY")
    print("=" * 70)
    
    # Sort by best match score
    match_scores.sort(key=lambda x: x['best_match_score'], reverse=True)
    
    print(f"\n{'Patient ID':<20} {'Age':<10} {'Dx':<5} {'Score':<8} {'Top Trial':<30}")
    print("-" * 70)
    for m in match_scores[:15]:
        print(f"{m['patient_id']:<20} {m['age_range']:<10} {m['diagnoses']:<5} {m['best_match_score']:<8.1%} {m['top_trial'][:30]:<30}")
    
    if len(match_scores) > 15:
        print(f"... and {len(match_scores) - 15} more patients")
    
    print("\n" + "=" * 70)
    
    # Statistics
    high_matches = sum(1 for m in match_scores if m['best_match_score'] >= 0.7)
    medium_matches = sum(1 for m in match_scores if 0.4 <= m['best_match_score'] < 0.7)
    
    print(f"\nMatch Quality Distribution:")
    print(f"  HIGH (≥70%):   {high_matches} patients")
    print(f"  MEDIUM (40-70%): {medium_matches} patients")
    print(f"  LOW (<40%):    {len(match_scores) - high_matches - medium_matches} patients")
    
    return eligible_patients


if __name__ == '__main__':
    FHIR_DIR = r'c:\Coherence\synthea_sample_data_fhir_stu3_nov2021\fhir_stu3'
    TRIALS_FILE = r'c:\Coherence\New folder\python-api\data\sample_trials.json'
    OUTPUT_FILE = r'c:\Coherence\New folder\python-api\data\real_patients.json'
    TARGET_COUNT = 250  # Find 200-300 eligible patients
    
    print("=" * 70)
    print("FINDING ELIGIBLE PATIENTS FOR CLINICAL TRIALS")
    print("=" * 70)
    print()
    
    patients = find_eligible_patients(FHIR_DIR, TRIALS_FILE, OUTPUT_FILE, TARGET_COUNT)
    
    print("\n✓ Ingestion complete! Patients ready for matching.")
