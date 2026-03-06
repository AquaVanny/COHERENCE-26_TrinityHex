from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os
from dotenv import load_dotenv
import sys
import traceback
import pandas as pd
import json
from werkzeug.utils import secure_filename

# Add models directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'models'))

from patient_anonymizer import PatientAnonymizer
from trial_matcher import ClinicalTrialMatcher
from fhir_parser import FHIRParser
from anonymizer import EnhancedAnonymizer
from criteria_parser import CriteriaParser
from matching_engine import MatchingEngine
from explainer import RankingModule

load_dotenv()

app = Flask(__name__)
CORS(app, origins=[
    os.getenv('FRONTEND_URL', 'http://localhost:5173'),
    'http://localhost:5173',
    'http://localhost:5174',
    'http://localhost:5175',
    'http://localhost:3000',
    'http://127.0.0.1:5173',
    'http://127.0.0.1:5174',
])

# Initialize AI components — legacy
anonymizer = PatientAnonymizer()
matcher = ClinicalTrialMatcher()

# Initialize new pipeline components (Layers 1-4)
fhir_parser = FHIRParser()
enhanced_anonymizer = EnhancedAnonymizer()
criteria_parser = CriteriaParser()
matching_engine = MatchingEngine()
ranking_module = RankingModule()
# Wire SHAP explainer to the ML model
ranking_module.set_ml_model(matching_engine.ml_scorer.model)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'json', 'csv'}

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_csv_to_patients(csv_file_path):
    """Parse CSV file to patient data format."""
    try:
        df = pd.read_csv(csv_file_path)
        patients = []
        
        for _, row in df.iterrows():
            patient = {}
            
            # Map common CSV column names to our patient data format
            column_mapping = {
                'patient_id': ['patient_id', 'id', 'patient_number', 'mrn'],
                'name': ['name', 'patient_name', 'full_name'],
                'age': ['age', 'patient_age'],
                'gender': ['gender', 'sex'],
                'location': ['location', 'address', 'city', 'state'],
                'diagnosis': ['diagnosis', 'condition', 'medical_condition', 'diagnoses'],
                'medications': ['medications', 'drugs', 'medication_list'],
                'diagnosis_date': ['diagnosis_date', 'date_diagnosed', 'onset_date']
            }
            
            for field, possible_columns in column_mapping.items():
                for col in possible_columns:
                    if col in df.columns and not pd.isna(row.get(col)):
                        value = row[col]
                        if field in ['diagnosis', 'medications'] and isinstance(value, str):
                            # Split comma-separated values
                            patient[field] = [item.strip() for item in value.split(',')]
                        else:
                            patient[field] = value
                        break
            
            # Add any additional columns as lab_results or vital_signs
            lab_results = {}
            vital_signs = {}
            
            for col in df.columns:
                if col not in [item for sublist in column_mapping.values() for item in sublist]:
                    value = row[col]
                    if not pd.isna(value):
                        if any(keyword in col.lower() for keyword in ['lab', 'test', 'result', 'level']):
                            lab_results[col] = value
                        elif any(keyword in col.lower() for keyword in ['vital', 'bp', 'pressure', 'weight', 'height', 'bmi']):
                            vital_signs[col] = value
            
            if lab_results:
                patient['lab_results'] = lab_results
            if vital_signs:
                patient['vital_signs'] = vital_signs
                
            patients.append(patient)
        
        return patients
    except Exception as e:
        raise ValueError(f"Error parsing CSV file: {str(e)}")

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'OK',
        'timestamp': datetime.now().isoformat(),
        'environment': os.getenv('FLASK_ENV', 'development'),
        'python_version': '3.12.4'
    })

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    return jsonify({
        'message': 'Clinical Trial Matching Engine is working!',
        'data': {
            'server': 'Flask',
            'version': '1.0.0',
            'features': ['AI Matching', 'Patient Anonymization', 'Explainable AI', 'Geographic Filtering']
        }
    })

@app.route('/api/anonymize-patient', methods=['POST'])
def anonymize_patient():
    """Anonymize patient data while preserving clinical relevance."""
    try:
        patient_data = request.get_json()
        
        if not patient_data:
            return jsonify({'error': 'No patient data provided'}), 400
        
        # Anonymize the patient record
        anonymized_data = anonymizer.anonymize_patient_record(patient_data)
        
        # Validate anonymization
        validation = anonymizer.validate_anonymization(patient_data, anonymized_data)
        
        return jsonify({
            'anonymized_patient': anonymized_data,
            'validation': validation,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Anonymization failed',
            'message': str(e),
            'traceback': traceback.format_exc() if app.config['DEBUG'] else None
        }), 500

@app.route('/api/parse-criteria', methods=['POST'])
def parse_trial_criteria():
    """Parse clinical trial eligibility criteria into structured format."""
    try:
        data = request.get_json()
        criteria_text = data.get('criteria_text', '')
        
        if not criteria_text:
            return jsonify({'error': 'No criteria text provided'}), 400
        
        # Parse the criteria
        parsed_criteria = matcher.parse_eligibility_criteria(criteria_text)
        
        return jsonify({
            'parsed_criteria': parsed_criteria,
            'original_text': criteria_text,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Criteria parsing failed',
            'message': str(e),
            'traceback': traceback.format_exc() if app.config['DEBUG'] else None
        }), 500

@app.route('/api/match-trials', methods=['POST'])
def match_patient_to_trials():
    """Match a patient to clinical trials with explanations."""
    try:
        data = request.get_json()
        patient_data = data.get('patient_data', {})
        trials_data = data.get('trials_data', [])
        
        if not patient_data:
            return jsonify({'error': 'No patient data provided'}), 400
        
        if not trials_data:
            return jsonify({'error': 'No trials data provided'}), 400
        
        # Anonymize patient data first
        anonymized_patient = anonymizer.anonymize_patient_record(patient_data)
        
        # Match trials
        ranked_trials = matcher.rank_trials_for_patient(anonymized_patient, trials_data)
        
        return jsonify({
            'patient_id': anonymized_patient.get('patient_id'),
            'total_trials': len(trials_data),
            'ranked_trials': ranked_trials,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Trial matching failed',
            'message': str(e),
            'traceback': traceback.format_exc() if app.config['DEBUG'] else None
        }), 500

@app.route('/api/eligibility-score', methods=['POST'])
def calculate_eligibility_score():
    """Calculate detailed eligibility score for a patient-trial pair."""
    try:
        data = request.get_json()
        patient_data = data.get('patient_data', {})
        trial_criteria = data.get('trial_criteria', {})
        
        if not patient_data or not trial_criteria:
            return jsonify({'error': 'Patient data and trial criteria required'}), 400
        
        # Anonymize patient data
        anonymized_patient = anonymizer.anonymize_patient_record(patient_data)
        
        # Calculate eligibility score
        score_details = matcher.calculate_eligibility_score(anonymized_patient, trial_criteria)
        
        return jsonify({
            'patient_id': anonymized_patient.get('patient_id'),
            'eligibility_score': score_details['total_score'],
            'confidence': score_details['confidence'],
            'explanations': score_details['explanations'],
            'matching_criteria': score_details['matching_criteria'],
            'failing_criteria': score_details['failing_criteria'],
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Score calculation failed',
            'message': str(e),
            'traceback': traceback.format_exc() if app.config['DEBUG'] else None
        }), 500

@app.route('/api/upload-patients', methods=['POST'])
def upload_patient_file():
    """Upload and process patient data from JSON or CSV file."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Please upload JSON or CSV files only.'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            # Parse file based on extension
            file_ext = filename.rsplit('.', 1)[1].lower()
            
            if file_ext == 'json':
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    # Handle both single patient object and array of patients
                    if isinstance(data, list):
                        patients = data
                    else:
                        patients = [data]
            
            elif file_ext == 'csv':
                patients = parse_csv_to_patients(file_path)
            
            # Anonymize all patients
            anonymized_patients = []
            for patient in patients:
                anonymized_patient = anonymizer.anonymize_patient_record(patient)
                anonymized_patients.append(anonymized_patient)
            
            # Clean up uploaded file
            os.remove(file_path)
            
            return jsonify({
                'message': 'File uploaded and processed successfully',
                'total_patients': len(anonymized_patients),
                'anonymized_patients': anonymized_patients,
                'file_info': {
                    'filename': filename,
                    'file_type': file_ext,
                    'processed_at': datetime.now().isoformat()
                }
            })
            
        except Exception as parse_error:
            # Clean up file on error
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({
                'error': 'Error processing file',
                'message': str(parse_error)
            }), 400
            
    except Exception as e:
        return jsonify({
            'error': 'File upload failed',
            'message': str(e),
            'traceback': traceback.format_exc() if app.config['DEBUG'] else None
        }), 500

@app.route('/api/upload-and-match', methods=['POST'])
def upload_and_match_patients():
    """Upload patient file and immediately match to trials."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Please upload JSON or CSV files only.'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            # Parse file based on extension
            file_ext = filename.rsplit('.', 1)[1].lower()
            
            if file_ext == 'json':
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        patients = data
                    else:
                        patients = [data]
            
            elif file_ext == 'csv':
                patients = parse_csv_to_patients(file_path)
            
            # Load sample trials for matching
            trials_file = os.path.join(os.path.dirname(__file__), 'data', 'sample_trials.json')
            with open(trials_file, 'r') as f:
                trials = json.load(f)
            
            # Process each patient
            results = []
            for patient in patients:
                # Anonymize patient
                anonymized_patient = anonymizer.anonymize_patient_record(patient)
                
                # Match to trials
                ranked_trials = matcher.rank_trials_for_patient(anonymized_patient, trials)
                
                results.append({
                    'patient_id': anonymized_patient.get('patient_id'),
                    'original_patient_id': patient.get('patient_id', 'Unknown'),
                    'anonymized_patient': anonymized_patient,
                    'ranked_trials': ranked_trials[:5],  # Top 5 matches
                    'total_trials_evaluated': len(trials)
                })
            
            # Clean up uploaded file
            os.remove(file_path)
            
            return jsonify({
                'message': 'File uploaded and matching completed successfully',
                'total_patients': len(results),
                'matching_results': results,
                'file_info': {
                    'filename': filename,
                    'file_type': file_ext,
                    'processed_at': datetime.now().isoformat()
                }
            })
            
        except Exception as parse_error:
            # Clean up file on error
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({
                'error': 'Error processing file',
                'message': str(parse_error)
            }), 400
            
    except Exception as e:
        return jsonify({
            'error': 'File upload and matching failed',
            'message': str(e),
            'traceback': traceback.format_exc() if app.config['DEBUG'] else None
        }), 500

@app.route('/api/sample-data', methods=['GET'])
def get_sample_data():
    """Get sample patients and trials for testing."""
    try:
        import json
        
        # Load sample patients
        patients_file = os.path.join(os.path.dirname(__file__), 'data', 'sample_patients.json')
        trials_file = os.path.join(os.path.dirname(__file__), 'data', 'sample_trials.json')
        
        patients = []
        trials = []
        
        if os.path.exists(patients_file):
            with open(patients_file, 'r') as f:
                patients = json.load(f)
        
        if os.path.exists(trials_file):
            with open(trials_file, 'r') as f:
                trials = json.load(f)
        
        return jsonify({
            'patients': patients,
            'trials': trials,
            'total_patients': len(patients),
            'total_trials': len(trials),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to load sample data',
            'message': str(e),
            'traceback': traceback.format_exc() if app.config['DEBUG'] else None
        }), 500

@app.route('/api/demo-match', methods=['GET'])
def demo_matching():
    """Run a demo matching for the first sample patient."""
    try:
        import json
        
        # Load sample data
        patients_file = os.path.join(os.path.dirname(__file__), 'data', 'sample_patients.json')
        trials_file = os.path.join(os.path.dirname(__file__), 'data', 'sample_trials.json')
        
        with open(patients_file, 'r') as f:
            patients = json.load(f)
        
        with open(trials_file, 'r') as f:
            trials = json.load(f)
        
        if not patients or not trials:
            return jsonify({'error': 'No sample data available'}), 400
        
        # Use first patient for demo
        patient = patients[0]
        
        # Anonymize patient data
        anonymized_patient = anonymizer.anonymize_patient_record(patient)
        
        # Match trials
        ranked_trials = matcher.rank_trials_for_patient(anonymized_patient, trials)
        
        return jsonify({
            'demo_patient': anonymized_patient,
            'original_patient_id': patient.get('patient_id'),
            'total_trials_evaluated': len(trials),
            'top_matches': ranked_trials[:3],  # Top 3 matches
            'all_matches': ranked_trials,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Demo matching failed',
            'message': str(e),
            'traceback': traceback.format_exc() if app.config['DEBUG'] else None
        }), 500

##############################################################################
# ── V2 API ENDPOINTS (Layers 1-4 Pipeline) ─────────────────────────────────
##############################################################################

@app.route('/api/v2/ingest', methods=['POST'])
def v2_ingest():
    """
    Layer 1 — Unified data ingestion endpoint.
    Accepts FHIR R4 JSON bundles, flat JSON patient records, or CSV files.
    Anonymizes using Presidio-based PII stripping with audit log.
    """
    try:
        # ── File upload path ──────────────────────────────────────
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400

            filename = secure_filename(file.filename)
            file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            if file_ext not in ('json', 'csv'):
                return jsonify({'error': 'Unsupported file type. Use JSON or CSV.'}), 400

            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            try:
                if file_ext == 'json':
                    with open(file_path, 'r') as f:
                        data = json.load(f)

                    # Auto-detect FHIR bundle vs flat patient(s)
                    if isinstance(data, dict) and data.get('resourceType') == 'Bundle':
                        patients = [fhir_parser.parse_bundle(data)]
                    elif isinstance(data, list):
                        patients = []
                        for item in data:
                            if isinstance(item, dict) and item.get('resourceType') == 'Bundle':
                                patients.append(fhir_parser.parse_bundle(item))
                            else:
                                patients.append(item)
                    else:
                        patients = [data]

                elif file_ext == 'csv':
                    patients = parse_csv_to_patients(file_path)

                os.remove(file_path)

            except Exception as parse_err:
                if os.path.exists(file_path):
                    os.remove(file_path)
                return jsonify({'error': 'File parse error', 'message': str(parse_err)}), 400

        # ── JSON body path ────────────────────────────────────────
        else:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided. Send JSON body or file upload.'}), 400

            if isinstance(data, dict) and data.get('resourceType') == 'Bundle':
                patients = [fhir_parser.parse_bundle(data)]
            elif isinstance(data, list):
                patients = []
                for item in data:
                    if isinstance(item, dict) and item.get('resourceType') == 'Bundle':
                        patients.append(fhir_parser.parse_bundle(item))
                    else:
                        patients.append(item)
            else:
                patients = [data]

        # ── Anonymize all patients ────────────────────────────────
        anonymized = []
        audit_logs = []
        for patient in patients:
            anon = enhanced_anonymizer.anonymize(patient)
            audit = enhanced_anonymizer.get_audit_log()
            validation = enhanced_anonymizer.validate(patient, anon)
            anonymized.append({
                'anonymized_patient': anon,
                'validation': validation
            })
            audit_logs.extend(audit)

        return jsonify({
            'message': 'Ingestion and anonymization complete',
            'total_patients': len(anonymized),
            'patients': anonymized,
            'audit_log': audit_logs,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'error': 'Ingestion failed',
            'message': str(e),
            'traceback': traceback.format_exc() if app.config['DEBUG'] else None
        }), 500


@app.route('/api/v2/parse-criteria', methods=['POST'])
def v2_parse_criteria():
    """
    Layer 2 — Parse eligibility criteria text into structured JSON.
    Uses spaCy + BioBERT + regex heuristics.
    """
    try:
        data = request.get_json()
        criteria_text = data.get('criteria_text', '')
        if not criteria_text:
            return jsonify({'error': 'No criteria_text provided'}), 400

        parsed = criteria_parser.parse(criteria_text)

        return jsonify({
            'parsed_criteria': parsed,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'error': 'Criteria parsing failed',
            'message': str(e),
            'traceback': traceback.format_exc() if app.config['DEBUG'] else None
        }), 500


@app.route('/api/v2/match', methods=['POST'])
def v2_match():
    """
    Layer 3+4 — Full pipeline: ingest → anonymize → parse criteria → match → rank → explain.
    Accepts patient_data (or raw FHIR bundle) + optional trials_data.
    If trials_data is omitted, uses the built-in sample trials.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        patient_data = data.get('patient_data', {})
        trials_data = data.get('trials_data', None)

        if not patient_data:
            return jsonify({'error': 'No patient_data provided'}), 400

        # Auto-detect FHIR bundle
        if isinstance(patient_data, dict) and patient_data.get('resourceType') == 'Bundle':
            patient_data = fhir_parser.parse_bundle(patient_data)

        # Anonymize
        anonymized_patient = enhanced_anonymizer.anonymize(patient_data)
        audit_log = enhanced_anonymizer.get_audit_log()

        # Load trials if not provided
        if not trials_data:
            trials_file = os.path.join(os.path.dirname(__file__), 'data', 'sample_trials.json')
            with open(trials_file, 'r') as f:
                trials_data = json.load(f)

        # Match (Layer 3)
        raw_results = matching_engine.match_all_trials(
            anonymized_patient, trials_data, criteria_parser
        )

        # Rank and explain (Layer 4)
        explained_results = ranking_module.rank_and_explain(raw_results, patient_data)

        return jsonify({
            'patient_id': anonymized_patient.get('patient_id'),
            'anonymized_patient': anonymized_patient,
            'total_trials_evaluated': len(trials_data),
            'ranked_matches': explained_results,
            'audit_log': audit_log,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'error': 'Matching failed',
            'message': str(e),
            'traceback': traceback.format_exc() if app.config['DEBUG'] else None
        }), 500


@app.route('/api/v2/upload-and-match', methods=['POST'])
def v2_upload_and_match():
    """
    Layer 1-4 — Upload file → ingest → anonymize → match → rank → explain.
    Supports FHIR R4 bundles, flat JSON, and CSV.
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        if file_ext not in ('json', 'csv'):
            return jsonify({'error': 'Unsupported file type. Use JSON or CSV.'}), 400

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            if file_ext == 'json':
                with open(file_path, 'r') as f:
                    data = json.load(f)
                if isinstance(data, dict) and data.get('resourceType') == 'Bundle':
                    patients = [fhir_parser.parse_bundle(data)]
                elif isinstance(data, list):
                    patients = []
                    for item in data:
                        if isinstance(item, dict) and item.get('resourceType') == 'Bundle':
                            patients.append(fhir_parser.parse_bundle(item))
                        else:
                            patients.append(item)
                else:
                    patients = [data]
            elif file_ext == 'csv':
                patients = parse_csv_to_patients(file_path)

            os.remove(file_path)
        except Exception as parse_err:
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'error': 'File parse error', 'message': str(parse_err)}), 400

        # Load trials
        trials_file = os.path.join(os.path.dirname(__file__), 'data', 'sample_trials.json')
        with open(trials_file, 'r') as f:
            trials_data = json.load(f)

        # Process each patient through the full pipeline
        all_results = []
        for patient in patients:
            anonymized = enhanced_anonymizer.anonymize(patient)
            audit = enhanced_anonymizer.get_audit_log()

            raw_matches = matching_engine.match_all_trials(
                anonymized, trials_data, criteria_parser
            )
            explained = ranking_module.rank_and_explain(raw_matches, patient)

            all_results.append({
                'patient_id': anonymized.get('patient_id'),
                'original_patient_id': patient.get('patient_id', 'Unknown'),
                'anonymized_patient': anonymized,
                'ranked_matches': explained,
                'total_trials_evaluated': len(trials_data),
                'audit_log': audit
            })

        return jsonify({
            'message': 'File processed and matching complete',
            'total_patients': len(all_results),
            'matching_results': all_results,
            'file_info': {
                'filename': filename,
                'file_type': file_ext,
                'processed_at': datetime.now().isoformat()
            }
        })

    except Exception as e:
        return jsonify({
            'error': 'Upload and match failed',
            'message': str(e),
            'traceback': traceback.format_exc() if app.config['DEBUG'] else None
        }), 500


@app.route('/api/v2/ingest-fhir-directory', methods=['POST'])
def v2_ingest_fhir_directory():
    """
    Batch ingest: parse all FHIR bundle files from a server-side directory.
    Body: { "directory": "path/to/fhir/bundles", "limit": 10 }
    """
    try:
        data = request.get_json()
        directory = data.get('directory', '')
        limit = data.get('limit', None)

        if not directory or not os.path.isdir(directory):
            return jsonify({'error': f'Directory not found: {directory}'}), 400

        patients = fhir_parser.parse_bundle_directory(directory, limit=limit)

        anonymized = []
        audit_logs = []
        for patient in patients:
            anon = enhanced_anonymizer.anonymize(patient)
            audit = enhanced_anonymizer.get_audit_log()
            anonymized.append(anon)
            audit_logs.extend(audit)

        return jsonify({
            'message': f'Ingested {len(anonymized)} patients from {directory}',
            'total_patients': len(anonymized),
            'patients': anonymized,
            'audit_log_sample': audit_logs[:20],
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'error': 'FHIR directory ingestion failed',
            'message': str(e),
            'traceback': traceback.format_exc() if app.config['DEBUG'] else None
        }), 500


@app.route('/api/v2/demo-match', methods=['GET'])
def v2_demo_match():
    """
    Run matching pipeline on a real patient from the ingested dataset.
    Query param: patient_index (default: random selection)
    """
    try:
        # Use real ingested patients
        patients_file = os.path.join(os.path.dirname(__file__), 'data', 'real_patients.json')
        trials_file = os.path.join(os.path.dirname(__file__), 'data', 'sample_trials.json')

        with open(patients_file, 'r') as f:
            patients = json.load(f)
        with open(trials_file, 'r') as f:
            trials = json.load(f)

        if not patients or not trials:
            return jsonify({'error': 'No patient data available'}), 400

        # Get patient index from query param or select randomly
        patient_index = request.args.get('patient_index', type=int)
        if patient_index is None:
            import random
            patient_index = random.randint(0, len(patients) - 1)
        else:
            patient_index = min(patient_index, len(patients) - 1)

        patient = patients[patient_index]
        
        # Patient is already anonymized from ingestion
        raw_matches = matching_engine.match_all_trials(patient, trials, criteria_parser)
        explained = ranking_module.rank_and_explain(raw_matches, patient)

        return jsonify({
            'patient': patient,
            'patient_index': patient_index,
            'total_patients_available': len(patients),
            'total_trials_evaluated': len(trials),
            'top_matches': explained[:3],
            'all_matches': explained,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'error': 'Demo matching failed',
            'message': str(e),
            'traceback': traceback.format_exc() if app.config['DEBUG'] else None
        }), 500


@app.route('/api/v2/patients', methods=['GET'])
def v2_get_patients():
    """Get list of available patients (anonymized) for selection."""
    try:
        patients_file = os.path.join(os.path.dirname(__file__), 'data', 'real_patients.json')
        with open(patients_file, 'r') as f:
            patients = json.load(f)
        
        # Return summary info only
        patient_list = []
        for idx, p in enumerate(patients):
            patient_list.append({
                'index': idx,
                'patient_id': p.get('patient_id'),
                'age_range': p.get('age_range'),
                'gender': p.get('gender'),
                'region': p.get('region'),
                'diagnosis_count': len(p.get('diagnosis', [])),
                'medication_count': len(p.get('medications', []))
            })
        
        return jsonify({
            'total_patients': len(patient_list),
            'patients': patient_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v2/pipeline-info', methods=['GET'])
def v2_pipeline_info():
    """Return information about the active pipeline components."""
    try:
        from anonymizer import PRESIDIO_AVAILABLE
        from criteria_parser import SPACY_AVAILABLE, TRANSFORMERS_AVAILABLE
        from matching_engine import XGBOOST_AVAILABLE

        return jsonify({
            'pipeline_version': '2.0',
            'layers': {
                'layer1_ingestion': {
                    'fhir_parser': True,
                    'csv_parser': True,
                    'presidio_anonymizer': PRESIDIO_AVAILABLE,
                    'audit_logging': True
                },
                'layer2_nlp_parser': {
                    'spacy': SPACY_AVAILABLE,
                    'biobert': TRANSFORMERS_AVAILABLE,
                    'regex_heuristics': True
                },
                'layer3_matching': {
                    'rule_engine': True,
                    'xgboost_scorer': XGBOOST_AVAILABLE,
                    'score_fusion': True,
                    'rule_weight': 0.6,
                    'ml_weight': 0.4
                },
                'layer4_explainer': {
                    'rule_explanations': True,
                    'shap_available': True,
                    'geographic_distance': True,
                    'confidence_tiers': True
                }
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Route not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': str(error) if app.config['DEBUG'] else 'Something went wrong'
    }), 500

if __name__ == '__main__':
    port = int(os.getenv('PYTHON_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f'🐍 Python Flask API starting on port {port}')
    print(f'📱 Environment: {os.getenv("FLASK_ENV", "development")}')
    print(f'🌐 API available at: http://localhost:{port}/api')
    
    app.run(host='0.0.0.0', port=port, debug=debug)
