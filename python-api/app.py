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

load_dotenv()

app = Flask(__name__)
CORS(app, origins=os.getenv('FRONTEND_URL', 'http://localhost:5173'))

# Initialize AI components
anonymizer = PatientAnonymizer()
matcher = ClinicalTrialMatcher()

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
