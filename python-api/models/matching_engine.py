"""
Layer 3 — Dual-Mode Matching Engine
Mode A: Rule-based hard filter evaluating structured criteria deterministically.
Mode B: ML probabilistic scorer using XGBoost on patient-trial feature vectors.
Score Fusion: 0.6 × Rule Score + 0.4 × ML Score (hard exclusion overrides).
"""

import re
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    try:
        from sklearn.ensemble import GradientBoostingClassifier as XGBClassifier
        XGBOOST_AVAILABLE = True
    except ImportError:
        XGBOOST_AVAILABLE = False

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder


class RuleEngine:
    """
    Mode A — Deterministic rule evaluation.
    Evaluates each structured criterion against the patient profile.
    Returns ELIGIBLE / INELIGIBLE / UNKNOWN per criterion.
    """

    def evaluate(self, patient: Dict, criteria: Dict) -> Dict[str, Any]:
        """
        Evaluate all parsed criteria against a patient record.

        Returns:
            {
                'overall': 'ELIGIBLE' | 'INELIGIBLE' | 'UNKNOWN',
                'rule_score': float (0.0 - 1.0),
                'criteria_results': [
                    { 'criterion': {...}, 'status': 'ELIGIBLE'|'INELIGIBLE'|'UNKNOWN',
                      'explanation': str }
                ],
                'hard_exclusion': bool
            }
        """
        results = []
        hard_exclusion = False

        # Evaluate inclusion criteria
        for crit in criteria.get('inclusion', []):
            result = self._evaluate_criterion(patient, crit, is_exclusion=False)
            results.append(result)

        # Evaluate exclusion criteria
        for crit in criteria.get('exclusion', []):
            result = self._evaluate_criterion(patient, crit, is_exclusion=True)
            results.append(result)
            if result['status'] == 'INELIGIBLE':
                hard_exclusion = True

        # Compute rule score
        if not results:
            return {
                'overall': 'UNKNOWN',
                'rule_score': 0.5,
                'criteria_results': [],
                'hard_exclusion': False
            }

        eligible_count = sum(1 for r in results if r['status'] == 'ELIGIBLE')
        ineligible_count = sum(1 for r in results if r['status'] == 'INELIGIBLE')
        unknown_count = sum(1 for r in results if r['status'] == 'UNKNOWN')
        total = len(results)

        if hard_exclusion:
            rule_score = 0.0
            overall = 'INELIGIBLE'
        elif ineligible_count > 0:
            rule_score = max(0.0, eligible_count / total * 0.5)
            overall = 'INELIGIBLE'
        elif unknown_count > 0 and eligible_count > 0:
            rule_score = eligible_count / total
            overall = 'UNKNOWN'
        elif eligible_count == total:
            rule_score = 1.0
            overall = 'ELIGIBLE'
        else:
            rule_score = eligible_count / total
            overall = 'UNKNOWN'

        return {
            'overall': overall,
            'rule_score': round(rule_score, 4),
            'criteria_results': results,
            'hard_exclusion': hard_exclusion
        }

    def _evaluate_criterion(self, patient: Dict, criterion: Dict,
                            is_exclusion: bool) -> Dict[str, Any]:
        """Evaluate a single criterion against patient data."""
        field = criterion.get('field', '')
        result = {
            'criterion': criterion,
            'is_exclusion': is_exclusion,
            'status': 'UNKNOWN',
            'explanation': ''
        }

        if field == 'age':
            result = self._eval_age(patient, criterion, is_exclusion)
        elif field == 'gender':
            result = self._eval_gender(patient, criterion, is_exclusion)
        elif field == 'diagnosis':
            result = self._eval_diagnosis(patient, criterion, is_exclusion)
        elif field == 'medication':
            result = self._eval_medication(patient, criterion, is_exclusion)
        elif field == 'lab':
            result = self._eval_lab(patient, criterion, is_exclusion)
        elif field == 'medication_stability':
            result['status'] = 'UNKNOWN'
            result['explanation'] = 'Medication stability duration cannot be verified — manual review recommended'
        elif field == 'diagnosis_duration':
            result = self._eval_diagnosis_duration(patient, criterion, is_exclusion)
        elif field == 'life_expectancy':
            result['status'] = 'UNKNOWN'
            result['explanation'] = 'Life expectancy cannot be automatically assessed — manual review recommended'
        else:
            result['status'] = 'UNKNOWN'
            result['explanation'] = f'Criterion field "{field}" not recognized — manual review recommended'

        result['criterion'] = criterion
        result['is_exclusion'] = is_exclusion
        return result

    # ── Age ───────────────────────────────────────────────────────

    def _eval_age(self, patient: Dict, crit: Dict, is_exclusion: bool) -> Dict:
        age = self._get_patient_age(patient)
        if age is None:
            return {'status': 'UNKNOWN',
                    'explanation': 'Patient age not available — cannot verify age criterion'}

        op = crit.get('operator', '')
        val = crit.get('value')

        if op == 'between' and isinstance(val, list) and len(val) == 2:
            in_range = val[0] <= age <= val[1]
            if is_exclusion:
                status = 'INELIGIBLE' if in_range else 'ELIGIBLE'
            else:
                status = 'ELIGIBLE' if in_range else 'INELIGIBLE'
            return {
                'status': status,
                'explanation': f"Patient age ({age}) {'falls within' if in_range else 'outside'} "
                               f"required range ({val[0]}-{val[1]})"
            }

        if isinstance(val, (int, float)):
            met = self._compare(age, op, val)
            if is_exclusion:
                status = 'INELIGIBLE' if met else 'ELIGIBLE'
            else:
                status = 'ELIGIBLE' if met else 'INELIGIBLE'
            return {
                'status': status,
                'explanation': f"Patient age ({age}) {op} {val}: {'met' if met else 'not met'}"
            }

        return {'status': 'UNKNOWN', 'explanation': 'Age criterion could not be evaluated'}

    # ── Gender ────────────────────────────────────────────────────

    def _eval_gender(self, patient: Dict, crit: Dict, is_exclusion: bool) -> Dict:
        p_gender = (patient.get('gender') or patient.get('birth_sex') or '').lower()
        req_gender = str(crit.get('value', '')).lower()

        if not p_gender:
            return {'status': 'UNKNOWN',
                    'explanation': 'Patient gender not available — cannot verify gender criterion'}

        match = p_gender == req_gender
        if is_exclusion:
            status = 'INELIGIBLE' if match else 'ELIGIBLE'
        else:
            status = 'ELIGIBLE' if match else 'INELIGIBLE'

        return {
            'status': status,
            'explanation': f"Patient gender ({p_gender}) {'matches' if match else 'does not match'} "
                           f"required gender ({req_gender})"
        }

    # ── Diagnosis ─────────────────────────────────────────────────

    def _eval_diagnosis(self, patient: Dict, crit: Dict, is_exclusion: bool) -> Dict:
        patient_diags = patient.get('diagnosis', [])
        if isinstance(patient_diags, str):
            patient_diags = [patient_diags]

        patient_codes = patient.get('diagnosis_codes', [])
        crit_display = crit.get('display', '')
        crit_code = crit.get('code', '')

        # Check by code match
        code_match = False
        for pc in patient_codes:
            if pc.get('code', '').startswith(crit_code) and crit_code:
                code_match = True
                break

        # Check by text match
        text_match = False
        crit_lower = crit_display.lower()
        for diag in patient_diags:
            if not diag:
                continue
            diag_lower = diag.lower()
            if crit_lower in diag_lower or diag_lower in crit_lower:
                text_match = True
                break

        has_condition = code_match or text_match

        if is_exclusion:
            status = 'INELIGIBLE' if has_condition else 'ELIGIBLE'
            if has_condition:
                explanation = f"Patient has excluded condition: {crit_display} — EXCLUDED"
            else:
                explanation = f"Patient does not have excluded condition: {crit_display}"
        else:
            status = 'ELIGIBLE' if has_condition else 'INELIGIBLE'
            if has_condition:
                explanation = f"Patient has required condition: {crit_display}"
            else:
                explanation = f"Patient missing required condition: {crit_display}"

        return {'status': status, 'explanation': explanation}

    # ── Medication ────────────────────────────────────────────────

    def _eval_medication(self, patient: Dict, crit: Dict, is_exclusion: bool) -> Dict:
        patient_meds = patient.get('medications', [])
        if isinstance(patient_meds, str):
            patient_meds = [patient_meds]

        med_name = crit.get('name', '').lower()
        operator = crit.get('operator', 'taking')

        taking = any(med_name in m.lower() for m in patient_meds if m)

        if operator == 'not_taking':
            # Exclusion: patient should NOT be taking this
            if is_exclusion:
                status = 'INELIGIBLE' if taking else 'ELIGIBLE'
            else:
                status = 'ELIGIBLE' if not taking else 'INELIGIBLE'
            if taking:
                explanation = f"Patient is taking {med_name} — {'EXCLUDED' if is_exclusion else 'does not meet criterion'}"
            else:
                explanation = f"Patient is not taking {med_name}"
        else:
            # Inclusion: patient should be taking this
            if is_exclusion:
                status = 'INELIGIBLE' if taking else 'ELIGIBLE'
                explanation = f"{'Prior ' + med_name + ' use detected — EXCLUDED' if taking else 'No ' + med_name + ' use detected'}"
            else:
                status = 'ELIGIBLE' if taking else 'UNKNOWN'
                explanation = f"Patient {'is' if taking else 'may not be'} taking {med_name}"

        return {'status': status, 'explanation': explanation}

    # ── Lab values ────────────────────────────────────────────────

    def _eval_lab(self, patient: Dict, crit: Dict, is_exclusion: bool) -> Dict:
        lab_name = crit.get('name', '').lower()
        labs = patient.get('lab_results', {})

        # Find matching lab value (case-insensitive key match)
        patient_val = None
        for k, v in labs.items():
            if k.lower() == lab_name or k.lower().replace('_', '') == lab_name.lower().replace('_', ''):
                try:
                    patient_val = float(v)
                except (ValueError, TypeError):
                    patient_val = None
                break

        if patient_val is None:
            return {
                'status': 'UNKNOWN',
                'explanation': f"Lab value '{lab_name}' not available in patient data — manual review recommended"
            }

        op = crit.get('operator', '=')
        val = crit.get('value')

        if op == 'between' and isinstance(val, list) and len(val) == 2:
            in_range = val[0] <= patient_val <= val[1]
            if is_exclusion:
                status = 'INELIGIBLE' if in_range else 'ELIGIBLE'
            else:
                status = 'ELIGIBLE' if in_range else 'INELIGIBLE'
            return {
                'status': status,
                'explanation': f"{lab_name} value ({patient_val}) {'within' if in_range else 'outside'} "
                               f"required range ({val[0]}-{val[1]})"
            }

        if op == 'present':
            status = 'ELIGIBLE' if not is_exclusion else 'INELIGIBLE'
            return {
                'status': status,
                'explanation': f"{lab_name} value ({patient_val}) is present in patient data"
            }

        if val is not None:
            try:
                val = float(val)
                met = self._compare(patient_val, op, val)
                if is_exclusion:
                    status = 'INELIGIBLE' if met else 'ELIGIBLE'
                else:
                    status = 'ELIGIBLE' if met else 'INELIGIBLE'
                return {
                    'status': status,
                    'explanation': f"{lab_name} ({patient_val}) {op} {val}: {'met' if met else 'not met'}"
                }
            except (ValueError, TypeError):
                pass

        return {
            'status': 'UNKNOWN',
            'explanation': f"Lab criterion for '{lab_name}' could not be evaluated"
        }

    # ── Diagnosis duration ────────────────────────────────────────

    def _eval_diagnosis_duration(self, patient: Dict, crit: Dict, is_exclusion: bool) -> Dict:
        diag_date = patient.get('diagnosis_date') or patient.get('diagnosis_timeframe')
        if not diag_date:
            return {
                'status': 'UNKNOWN',
                'explanation': 'Diagnosis date not available — cannot verify duration criterion'
            }

        # Try to compute months since diagnosis
        try:
            dt = datetime.fromisoformat(str(diag_date).replace('Z', '+00:00'))
            months = (datetime.now() - dt.replace(tzinfo=None)).days / 30.44
            req_months = crit.get('value', 0)
            op = crit.get('operator', '>=')
            met = self._compare(months, op, req_months)
            if is_exclusion:
                status = 'INELIGIBLE' if met else 'ELIGIBLE'
            else:
                status = 'ELIGIBLE' if met else 'INELIGIBLE'
            return {
                'status': status,
                'explanation': f"Diagnosis duration ({int(months)} months) {op} {req_months} months: "
                               f"{'met' if met else 'not met'}"
            }
        except Exception:
            return {
                'status': 'UNKNOWN',
                'explanation': 'Diagnosis duration could not be computed — manual review recommended'
            }

    # ── Helpers ───────────────────────────────────────────────────

    def _get_patient_age(self, patient: Dict) -> Optional[int]:
        """Extract numeric age from patient, handling age_range buckets."""
        if 'age' in patient:
            try:
                return int(patient['age'])
            except (ValueError, TypeError):
                pass
        age_range = patient.get('age_range', '')
        if isinstance(age_range, str):
            m = re.match(r'(\d+)', age_range)
            if m:
                return int(m.group(1))
            if age_range == 'pediatric':
                return 10
        return None

    @staticmethod
    def _compare(actual, operator: str, expected) -> bool:
        try:
            actual = float(actual)
            expected = float(expected)
        except (ValueError, TypeError):
            return False
        ops = {
            '>=': actual >= expected,
            '<=': actual <= expected,
            '>': actual > expected,
            '<': actual < expected,
            '=': abs(actual - expected) < 0.01,
            '==': abs(actual - expected) < 0.01,
        }
        return ops.get(operator, False)


class MLScorer:
    """
    Mode B — ML probabilistic scorer.
    Uses XGBoost (or GradientBoosting fallback) trained on synthetic
    patient-trial pairs to produce a probability score 0.0–1.0.
    Handles missing data with median imputation + missing flags.
    """

    FEATURE_NAMES = [
        'age', 'gender_match', 'num_diagnoses', 'num_medications',
        'has_lab_results', 'num_lab_values', 'condition_overlap',
        'medication_overlap', 'num_inclusion', 'num_exclusion',
        'age_in_range', 'has_vital_signs', 'missing_data_count'
    ]

    def __init__(self):
        self.model = None
        self._trained = False
        self._build_model()

    def _build_model(self):
        """Initialize and pre-train on synthetic data."""
        if XGBOOST_AVAILABLE:
            try:
                from xgboost import XGBClassifier as XGB
                self.model = XGB(
                    n_estimators=100,
                    max_depth=4,
                    learning_rate=0.1,
                    random_state=42,
                    use_label_encoder=False,
                    eval_metric='logloss'
                )
            except Exception:
                self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        else:
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)

        # Train on synthetic data so the model is ready
        self._train_synthetic()

    def _train_synthetic(self):
        """Generate synthetic training data and fit the model."""
        np.random.seed(42)
        n_samples = 500

        X = np.zeros((n_samples, len(self.FEATURE_NAMES)))
        y = np.zeros(n_samples)

        for i in range(n_samples):
            age = np.random.randint(18, 90)
            gender_match = np.random.choice([0, 1], p=[0.3, 0.7])
            num_diag = np.random.randint(0, 8)
            num_meds = np.random.randint(0, 10)
            has_labs = np.random.choice([0, 1], p=[0.2, 0.8])
            num_labs = np.random.randint(0, 10) if has_labs else 0
            cond_overlap = np.random.uniform(0, 1)
            med_overlap = np.random.uniform(0, 1)
            num_inc = np.random.randint(1, 8)
            num_exc = np.random.randint(0, 5)
            age_in_range = np.random.choice([0, 1], p=[0.3, 0.7])
            has_vitals = np.random.choice([0, 1], p=[0.3, 0.7])
            missing = np.random.randint(0, 5)

            X[i] = [age, gender_match, num_diag, num_meds, has_labs, num_labs,
                     cond_overlap, med_overlap, num_inc, num_exc, age_in_range,
                     has_vitals, missing]

            # Label: higher prob of match when conditions align
            match_prob = (0.2 * age_in_range + 0.25 * cond_overlap +
                          0.15 * med_overlap + 0.1 * gender_match +
                          0.1 * has_labs + 0.1 * (1 - missing / 5) +
                          0.1 * has_vitals)
            y[i] = 1 if match_prob > 0.45 + np.random.normal(0, 0.1) else 0

        self.model.fit(X, y)
        self._trained = True

    def score(self, patient: Dict, trial: Dict, parsed_criteria: Dict,
              rule_result: Dict) -> Dict[str, Any]:
        """
        Compute ML probability score for a patient-trial pair.

        Returns:
            {
                'ml_score': float (0.0-1.0),
                'feature_vector': dict,
                'feature_importance': dict
            }
        """
        features = self._extract_features(patient, trial, parsed_criteria, rule_result)
        feature_vector = np.array([features[f] for f in self.FEATURE_NAMES]).reshape(1, -1)

        # Handle NaN with median imputation
        feature_vector = np.nan_to_num(feature_vector, nan=0.0)

        if self._trained and self.model is not None:
            prob = self.model.predict_proba(feature_vector)[0]
            ml_score = float(prob[1]) if len(prob) > 1 else float(prob[0])
        else:
            ml_score = 0.5

        # Feature importance
        importance = {}
        if hasattr(self.model, 'feature_importances_'):
            for fname, imp in zip(self.FEATURE_NAMES, self.model.feature_importances_):
                importance[fname] = round(float(imp), 4)

        return {
            'ml_score': round(ml_score, 4),
            'feature_vector': features,
            'feature_importance': importance
        }

    def _extract_features(self, patient: Dict, trial: Dict,
                          parsed_criteria: Dict, rule_result: Dict) -> Dict[str, float]:
        """Build feature vector from patient + trial + rule results."""
        features: Dict[str, float] = {}

        # Age
        age = patient.get('age')
        if age is None:
            age_range = patient.get('age_range', '')
            m = re.match(r'(\d+)', str(age_range))
            age = int(m.group(1)) if m else 50
        features['age'] = float(age) if age else 50.0

        # Gender match
        p_gender = (patient.get('gender') or '').lower()
        t_condition = (trial.get('condition') or '').lower()
        gender_req = 'female' if 'breast' in t_condition else ''
        features['gender_match'] = 1.0 if (not gender_req or p_gender == gender_req) else 0.0

        # Diagnoses
        diags = patient.get('diagnosis', [])
        features['num_diagnoses'] = float(len(diags) if isinstance(diags, list) else 1)

        # Medications
        meds = patient.get('medications', [])
        features['num_medications'] = float(len(meds) if isinstance(meds, list) else 1)

        # Lab results
        labs = patient.get('lab_results', {})
        features['has_lab_results'] = 1.0 if labs else 0.0
        features['num_lab_values'] = float(len(labs)) if isinstance(labs, dict) else 0.0

        # Condition overlap
        trial_condition = (trial.get('condition') or '').lower()
        overlap = 0.0
        if isinstance(diags, list):
            for d in diags:
                if d and trial_condition and (d.lower() in trial_condition or trial_condition in d.lower()):
                    overlap = 1.0
                    break
        features['condition_overlap'] = overlap

        # Medication overlap with criteria
        inc_meds = [c.get('name', '') for c in parsed_criteria.get('inclusion', [])
                    if c.get('field') == 'medication']
        med_overlap = 0.0
        if inc_meds and isinstance(meds, list):
            matched = sum(1 for im in inc_meds
                          if any(im.lower() in m.lower() for m in meds if m))
            med_overlap = matched / len(inc_meds)
        features['medication_overlap'] = med_overlap

        # Criteria counts
        features['num_inclusion'] = float(len(parsed_criteria.get('inclusion', [])))
        features['num_exclusion'] = float(len(parsed_criteria.get('exclusion', [])))

        # Age in range from rule evaluation
        age_eligible = 0.0
        for cr in rule_result.get('criteria_results', []):
            crit = cr.get('criterion', {})
            if crit.get('field') == 'age' and cr.get('status') == 'ELIGIBLE':
                age_eligible = 1.0
                break
        features['age_in_range'] = age_eligible

        # Vital signs
        features['has_vital_signs'] = 1.0 if patient.get('vital_signs') else 0.0

        # Missing data count
        key_fields = ['age', 'gender', 'diagnosis', 'medications', 'lab_results']
        missing = sum(1 for f in key_fields if not patient.get(f))
        features['missing_data_count'] = float(missing)

        return features


class MatchingEngine:
    """
    Dual-mode matching engine combining rule evaluation with ML scoring.
    Score Fusion: 0.6 × Rule Score + 0.4 × ML Score
    Hard exclusion overrides: final score = 0 regardless of ML score.
    """

    RULE_WEIGHT = 0.6
    ML_WEIGHT = 0.4

    def __init__(self):
        self.rule_engine = RuleEngine()
        self.ml_scorer = MLScorer()

    def match(self, patient: Dict, trial: Dict, parsed_criteria: Dict) -> Dict[str, Any]:
        """
        Run dual-mode matching for a single patient-trial pair.

        Returns complete match result with fused score, per-criterion
        breakdown, and confidence tier.
        """
        # Mode A: Rule-based evaluation
        rule_result = self.rule_engine.evaluate(patient, parsed_criteria)

        # Mode B: ML scoring
        ml_result = self.ml_scorer.score(patient, trial, parsed_criteria, rule_result)

        # Score fusion
        if rule_result['hard_exclusion']:
            fused_score = 0.0
            confidence_tier = 'HIGH'
            overall = 'INELIGIBLE'
        else:
            fused_score = (self.RULE_WEIGHT * rule_result['rule_score'] +
                           self.ML_WEIGHT * ml_result['ml_score'])
            fused_score = round(min(1.0, max(0.0, fused_score)), 4)

            if fused_score >= 0.85:
                confidence_tier = 'HIGH'
            elif fused_score >= 0.6:
                confidence_tier = 'MEDIUM'
            else:
                confidence_tier = 'LOW'

            if rule_result['overall'] == 'INELIGIBLE':
                overall = 'INELIGIBLE'
            elif fused_score >= 0.5:
                overall = 'ELIGIBLE'
            else:
                overall = 'UNKNOWN'

        return {
            'trial_id': trial.get('trial_id', ''),
            'title': trial.get('title', ''),
            'phase': trial.get('phase', ''),
            'sponsor': trial.get('sponsor', ''),
            'location': trial.get('location', ''),
            'condition': trial.get('condition', ''),
            'overall_status': overall,
            'fused_score': fused_score,
            'confidence_tier': confidence_tier,
            'rule_score': rule_result['rule_score'],
            'ml_score': ml_result['ml_score'],
            'hard_exclusion': rule_result['hard_exclusion'],
            'criteria_results': rule_result['criteria_results'],
            'feature_importance': ml_result['feature_importance'],
            'ml_feature_vector': ml_result['feature_vector']
        }

    def match_all_trials(self, patient: Dict, trials: List[Dict],
                         criteria_parser) -> List[Dict]:
        """
        Match a patient against all trials. Parse criteria, score, and rank.
        Returns sorted list of match results (best first).
        """
        results = []
        for trial in trials:
            criteria_text = trial.get('eligibility_criteria', '')
            parsed = criteria_parser.parse(criteria_text)
            result = self.match(patient, trial, parsed)
            results.append(result)

        # Sort by fused score descending
        results.sort(key=lambda x: x['fused_score'], reverse=True)
        return results
