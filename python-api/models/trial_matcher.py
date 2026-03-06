import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.ensemble import RandomForestClassifier
from typing import Dict, List, Tuple, Any
import re
import json
from datetime import datetime
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    print("Warning: spaCy not available. Some advanced NLP features will be disabled.")

class ClinicalTrialMatcher:
    """
    AI-powered matching engine for clinical trials using rule-based and ML approaches.
    """
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.ml_model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.nlp = None
        if SPACY_AVAILABLE:
            self._load_nlp_model()
        
    def _load_nlp_model(self):
        """Load spaCy model for medical text processing."""
        if not SPACY_AVAILABLE:
            return
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("Warning: spaCy model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None
    
    def parse_eligibility_criteria(self, criteria_text: str) -> Dict[str, List[str]]:
        """
        Parse eligibility criteria text into structured inclusion/exclusion rules.
        """
        criteria = {
            'inclusion': [],
            'exclusion': [],
            'age_range': None,
            'gender': None,
            'conditions': [],
            'medications': [],
            'lab_values': []
        }
        
        # Handle None or empty criteria text
        if not criteria_text:
            return criteria
        
        # Split into inclusion and exclusion sections
        text_lower = criteria_text.lower()
        
        # Extract age criteria
        age_patterns = [
            r'age[s]?\s*(?:between|from)?\s*(\d+)\s*(?:to|and|-)\s*(\d+)',
            r'(\d+)\s*(?:to|-)\s*(\d+)\s*years?\s*old',
            r'age[s]?\s*(?:>=|≥|>)\s*(\d+)',
            r'age[s]?\s*(?:<=|≤|<)\s*(\d+)'
        ]
        
        for pattern in age_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                if len(matches[0]) == 2:  # Range
                    criteria['age_range'] = {'min': int(matches[0][0]), 'max': int(matches[0][1])}
                else:  # Single value
                    if '>=' in pattern or '>' in pattern:
                        criteria['age_range'] = {'min': int(matches[0]), 'max': None}
                    else:
                        criteria['age_range'] = {'min': None, 'max': int(matches[0])}
                break
        
        # Extract gender criteria
        if 'male' in text_lower and 'female' not in text_lower:
            criteria['gender'] = 'male'
        elif 'female' in text_lower and 'male' not in text_lower:
            criteria['gender'] = 'female'
        
        # Extract medical conditions
        condition_keywords = [
            'diabetes', 'hypertension', 'cancer', 'heart disease', 'stroke',
            'depression', 'anxiety', 'asthma', 'copd', 'arthritis'
        ]
        
        for condition in condition_keywords:
            if condition in text_lower:
                criteria['conditions'].append(condition)
        
        # Extract medication criteria
        medication_patterns = [
            r'taking\s+([a-zA-Z]+)',
            r'on\s+([a-zA-Z]+)\s+therapy',
            r'receiving\s+([a-zA-Z]+)'
        ]
        
        for pattern in medication_patterns:
            matches = re.findall(pattern, text_lower)
            criteria['medications'].extend(matches)
        
        # Parse inclusion/exclusion sections
        inclusion_section = self._extract_section(criteria_text, 'inclusion')
        exclusion_section = self._extract_section(criteria_text, 'exclusion')
        
        criteria['inclusion'] = self._parse_criteria_list(inclusion_section)
        criteria['exclusion'] = self._parse_criteria_list(exclusion_section)
        
        return criteria
    
    def _extract_section(self, text: str, section_type: str) -> str:
        """Extract inclusion or exclusion section from criteria text."""
        patterns = {
            'inclusion': [
                r'inclusion\s+criteria[:\s]*(.*?)(?=exclusion|$)',
                r'eligible\s+patients[:\s]*(.*?)(?=exclusion|ineligible|$)'
            ],
            'exclusion': [
                r'exclusion\s+criteria[:\s]*(.*?)(?=inclusion|$)',
                r'ineligible\s+patients[:\s]*(.*?)(?=inclusion|eligible|$)'
            ]
        }
        
        if not text:
            return ""
        text_lower = text.lower()
        for pattern in patterns[section_type]:
            match = re.search(pattern, text_lower, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _parse_criteria_list(self, criteria_text: str) -> List[str]:
        """Parse criteria text into individual criteria items."""
        if not criteria_text:
            return []
        
        # Split by common delimiters
        items = re.split(r'[;\n•\-]\s*', criteria_text)
        items = [item.strip() for item in items if item.strip()]
        
        # Filter out very short items
        items = [item for item in items if len(item) > 10]
        
        return items
    
    def calculate_eligibility_score(self, patient_data: Dict, trial_criteria: Dict) -> Dict[str, Any]:
        """
        Calculate eligibility score for a patient-trial pair.
        """
        score_details = {
            'total_score': 0.0,
            'confidence': 0.0,
            'matching_criteria': [],
            'failing_criteria': [],
            'explanations': []
        }
        
        # Age matching
        age_score = self._check_age_eligibility(patient_data, trial_criteria)
        score_details['total_score'] += age_score['score']
        score_details['explanations'].append(age_score['explanation'])
        
        # Gender matching
        gender_score = self._check_gender_eligibility(patient_data, trial_criteria)
        score_details['total_score'] += gender_score['score']
        score_details['explanations'].append(gender_score['explanation'])
        
        # Medical conditions matching
        condition_score = self._check_condition_eligibility(patient_data, trial_criteria)
        score_details['total_score'] += condition_score['score']
        score_details['explanations'].extend(condition_score['explanations'])
        
        # Medication compatibility
        medication_score = self._check_medication_eligibility(patient_data, trial_criteria)
        score_details['total_score'] += medication_score['score']
        score_details['explanations'].extend(medication_score['explanations'])
        
        # Normalize score to 0-1 range
        max_possible_score = 4.0  # Age, gender, conditions, medications
        score_details['total_score'] = min(score_details['total_score'] / max_possible_score, 1.0)
        
        # Calculate confidence based on data completeness
        score_details['confidence'] = self._calculate_confidence(patient_data, trial_criteria)
        
        return score_details
    
    def _check_age_eligibility(self, patient_data: Dict, trial_criteria: Dict) -> Dict:
        """Check age eligibility."""
        result = {'score': 0.0, 'explanation': ''}
        
        patient_age_range = patient_data.get('age_range', '')
        trial_age_range = trial_criteria.get('age_range')
        
        if not trial_age_range:
            result['score'] = 0.5
            result['explanation'] = "Age: No specific age requirements in trial"
            return result
        
        # Map age ranges to numeric values for comparison
        age_mapping = {
            'pediatric': (0, 17),
            '18-29': (18, 29),
            '30-44': (30, 44),
            '45-64': (45, 64),
            '65+': (65, 100)
        }
        
        if patient_age_range in age_mapping:
            patient_min, patient_max = age_mapping[patient_age_range]
            trial_min = trial_age_range.get('min', 0)
            trial_max = trial_age_range.get('max', 100)
            
            # Check overlap
            if patient_max >= trial_min and patient_min <= trial_max:
                result['score'] = 1.0
                result['explanation'] = f"Age: Patient age range ({patient_age_range}) matches trial requirements"
            else:
                result['score'] = 0.0
                result['explanation'] = f"Age: Patient age range ({patient_age_range}) does not match trial requirements"
        else:
            result['score'] = 0.3
            result['explanation'] = "Age: Unable to determine age compatibility"
        
        return result
    
    def _check_gender_eligibility(self, patient_data: Dict, trial_criteria: Dict) -> Dict:
        """Check gender eligibility."""
        result = {'score': 0.0, 'explanation': ''}
        
        patient_gender = (patient_data.get('gender') or '').lower()
        trial_gender = (trial_criteria.get('gender') or '').lower()
        
        if not trial_gender:
            result['score'] = 1.0
            result['explanation'] = "Gender: No gender restrictions in trial"
        elif patient_gender == trial_gender:
            result['score'] = 1.0
            result['explanation'] = f"Gender: Patient gender ({patient_gender}) matches trial requirement"
        elif patient_gender and trial_gender:
            result['score'] = 0.0
            result['explanation'] = f"Gender: Patient gender ({patient_gender}) does not match trial requirement ({trial_gender})"
        else:
            result['score'] = 0.5
            result['explanation'] = "Gender: Unable to determine gender compatibility"
        
        return result
    
    def _check_condition_eligibility(self, patient_data: Dict, trial_criteria: Dict) -> Dict:
        """Check medical condition eligibility."""
        result = {'score': 0.0, 'explanations': []}
        
        patient_conditions = patient_data.get('diagnosis', [])
        if isinstance(patient_conditions, str):
            patient_conditions = [patient_conditions]
        
        trial_conditions = trial_criteria.get('conditions', [])
        
        if not trial_conditions:
            result['score'] = 0.5
            result['explanations'].append("Conditions: No specific condition requirements in trial")
            return result
        
        matches = 0
        total_conditions = len(trial_conditions)
        
        for trial_condition in trial_conditions:
            condition_match = False
            for patient_condition in patient_conditions:
                # Add null checks before calling lower()
                trial_cond_lower = (trial_condition or '').lower()
                patient_cond_lower = (patient_condition or '').lower()
                if trial_cond_lower and patient_cond_lower and trial_cond_lower in patient_cond_lower:
                    matches += 1
                    condition_match = True
                    result['explanations'].append(f"Conditions: Patient has required condition: {trial_condition}")
                    break
            
            if not condition_match:
                result['explanations'].append(f"Conditions: Patient missing required condition: {trial_condition}")
        
        result['score'] = matches / total_conditions if total_conditions > 0 else 0.5
        return result
    
    def _check_medication_eligibility(self, patient_data: Dict, trial_criteria: Dict) -> Dict:
        """Check medication eligibility."""
        result = {'score': 0.5, 'explanations': []}
        
        patient_medications = patient_data.get('medications', [])
        trial_medications = trial_criteria.get('medications', [])
        
        if not trial_medications:
            result['explanations'].append("Medications: No specific medication requirements in trial")
            return result
        
        # Simple medication compatibility check
        result['explanations'].append("Medications: Medication compatibility requires detailed review")
        return result
    
    def _calculate_confidence(self, patient_data: Dict, trial_criteria: Dict) -> float:
        """Calculate confidence score based on data completeness."""
        required_fields = ['age_range', 'gender', 'diagnosis']
        available_fields = sum(1 for field in required_fields if patient_data.get(field))
        
        return available_fields / len(required_fields)
    
    def rank_trials_for_patient(self, patient_data: Dict, trials_data: List[Dict]) -> List[Dict]:
        """
        Rank all trials for a given patient.
        """
        ranked_trials = []
        
        for trial in trials_data:
            # Parse trial criteria
            criteria = self.parse_eligibility_criteria(trial.get('eligibility_criteria', ''))
            
            # Calculate eligibility score
            score_details = self.calculate_eligibility_score(patient_data, criteria)
            
            # Add trial information
            trial_result = {
                'trial_id': trial.get('trial_id'),
                'title': trial.get('title'),
                'phase': trial.get('phase'),
                'location': trial.get('location'),
                'sponsor': trial.get('sponsor'),
                'eligibility_score': score_details['total_score'],
                'confidence': score_details['confidence'],
                'explanations': score_details['explanations'],
                'matching_criteria': score_details['matching_criteria'],
                'failing_criteria': score_details['failing_criteria']
            }
            
            ranked_trials.append(trial_result)
        
        # Sort by eligibility score (descending)
        ranked_trials.sort(key=lambda x: x['eligibility_score'], reverse=True)
        
        return ranked_trials
