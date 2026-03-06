"""
Layer 2 — Clinical Trial Criteria Parser (NLP Module)
Converts free-text eligibility criteria into structured JSON conditions.
Uses spaCy for sentence segmentation, BioBERT for medical NER when available,
and regex heuristics as robust fallback.
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    from transformers import pipeline as hf_pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class CriteriaParser:
    """
    Parse raw eligibility criteria text into structured inclusion/exclusion
    conditions the matching engine can evaluate.
    """

    # Known medical condition patterns
    CONDITION_PATTERNS = [
        (r'type\s*[12]\s*diabetes(?:\s*mellitus)?', 'E11', 'ICD10', 'Type 2 Diabetes Mellitus'),
        (r'type\s*1\s*diabetes(?:\s*mellitus)?', 'E10', 'ICD10', 'Type 1 Diabetes Mellitus'),
        (r'breast\s*cancer', 'C50', 'ICD10', 'Breast Cancer'),
        (r'lung\s*cancer', 'C34', 'ICD10', 'Lung Cancer'),
        (r'prostate\s*cancer', 'C61', 'ICD10', 'Prostate Cancer'),
        (r'colorectal\s*cancer', 'C18', 'ICD10', 'Colorectal Cancer'),
        (r'alzheimer', 'G30', 'ICD10', "Alzheimer's Disease"),
        (r'parkinson', 'G20', 'ICD10', "Parkinson's Disease"),
        (r'hypertension', 'I10', 'ICD10', 'Hypertension'),
        (r'heart\s*failure', 'I50', 'ICD10', 'Heart Failure'),
        (r'coronary\s*artery\s*disease', 'I25', 'ICD10', 'Coronary Artery Disease'),
        (r'chronic\s*kidney\s*disease', 'N18', 'ICD10', 'Chronic Kidney Disease'),
        (r'asthma', 'J45', 'ICD10', 'Asthma'),
        (r'copd|chronic\s*obstructive', 'J44', 'ICD10', 'COPD'),
        (r'depression', 'F32', 'ICD10', 'Depression'),
        (r'anxiety', 'F41', 'ICD10', 'Anxiety Disorder'),
        (r'stroke', 'I63', 'ICD10', 'Stroke'),
        (r'epilepsy', 'G40', 'ICD10', 'Epilepsy'),
        (r'rheumatoid\s*arthritis', 'M05', 'ICD10', 'Rheumatoid Arthritis'),
        (r'osteoarthritis', 'M15', 'ICD10', 'Osteoarthritis'),
        (r'multiple\s*sclerosis', 'G35', 'ICD10', 'Multiple Sclerosis'),
        (r'hepatitis\s*[bc]', 'B18', 'ICD10', 'Hepatitis'),
        (r'hiv|human\s*immunodeficiency', 'B20', 'ICD10', 'HIV'),
        (r'obesity', 'E66', 'ICD10', 'Obesity'),
        (r'anemia', 'D64', 'ICD10', 'Anemia'),
        (r'diabetic\s*ketoacidosis', 'E13.1', 'ICD10', 'Diabetic Ketoacidosis'),
        (r'metastatic\s*disease', 'C79', 'ICD10', 'Metastatic Disease'),
        (r'autoimmune\s*disorder', 'M35.9', 'ICD10', 'Autoimmune Disorder'),
        (r'dementia', 'F03', 'ICD10', 'Dementia'),
    ]

    # Lab value patterns
    LAB_PATTERNS = [
        (r'hba1c|hemoglobin\s*a1c|glycated\s*hemoglobin', 'HbA1c'),
        (r'fasting\s*(?:blood\s*)?glucose|fbg', 'fasting_glucose'),
        (r'(?:blood\s*)?glucose', 'glucose'),
        (r'egfr|estimated\s*glomerular', 'eGFR'),
        (r'creatinine', 'creatinine'),
        (r'bmi|body\s*mass\s*index', 'BMI'),
        (r'ldl(?:\s*cholesterol)?', 'LDL'),
        (r'hdl(?:\s*cholesterol)?', 'HDL'),
        (r'triglycerides?', 'triglycerides'),
        (r'total\s*cholesterol', 'total_cholesterol'),
        (r'mmse\s*(?:score)?', 'MMSE'),
        (r'moca\s*(?:score)?', 'MoCA'),
        (r'ecog\s*(?:performance\s*status)?', 'ECOG'),
        (r'fev1', 'FEV1'),
        (r'eosinophils?', 'eosinophils'),
        (r'ige|immunoglobulin\s*e', 'IgE'),
        (r'cea', 'CEA'),
        (r'platelet(?:s|\s*count)?', 'platelets'),
        (r'white\s*blood\s*cell|wbc', 'WBC'),
        (r'hemoglobin(?!\s*a1c)', 'hemoglobin'),
        (r'albumin', 'albumin'),
        (r'bilirubin', 'bilirubin'),
        (r'alt|alanine\s*transaminase', 'ALT'),
        (r'ast|aspartate\s*transaminase', 'AST'),
    ]

    # Medication patterns
    MEDICATION_KEYWORDS = [
        'metformin', 'insulin', 'tamoxifen', 'donepezil', 'sertraline',
        'lisinopril', 'amlodipine', 'atorvastatin', 'omeprazole',
        'albuterol', 'fluticasone', 'prednisone', 'warfarin', 'heparin',
        'aspirin', 'ibuprofen', 'acetaminophen', 'amoxicillin',
        'chemotherapy', 'immunotherapy', 'radiation', 'biologic',
        'corticosteroid', 'anticoagulant', 'statin', 'beta-blocker',
        'ace inhibitor', 'arb', 'diuretic', 'ssri', 'snri',
    ]

    def __init__(self):
        self.nlp = None
        self.ner_pipeline = None
        self._load_spacy()
        self._load_biobert()

    def _load_spacy(self):
        if not SPACY_AVAILABLE:
            return
        try:
            self.nlp = spacy.load('en_core_web_sm')
        except OSError:
            print("Warning: spaCy model en_core_web_sm not found.")

    def _load_biobert(self):
        """Load BioBERT NER model if transformers is available."""
        if not TRANSFORMERS_AVAILABLE:
            return
        try:
            self.ner_pipeline = hf_pipeline(
                'ner',
                model='dmis-lab/biobert-base-cased-v1.2',
                tokenizer='dmis-lab/biobert-base-cased-v1.2',
                aggregation_strategy='simple'
            )
        except Exception as e:
            print(f"Warning: BioBERT model not loaded: {e}")
            self.ner_pipeline = None

    # ── Public API ────────────────────────────────────────────────

    def parse(self, criteria_text: str) -> Dict[str, Any]:
        """
        Parse raw eligibility criteria text into structured JSON.

        Returns:
            {
                "inclusion": [ { "field": ..., "operator": ..., "value": ... }, ... ],
                "exclusion": [ ... ],
                "parse_confidence": float,
                "low_confidence_flags": [ ... ],
                "raw_text": str
            }
        """
        if not criteria_text or not criteria_text.strip():
            return {
                'inclusion': [],
                'exclusion': [],
                'parse_confidence': 0.0,
                'low_confidence_flags': ['Empty criteria text'],
                'raw_text': ''
            }

        # Step 1: Split into inclusion / exclusion sections
        inc_text, exc_text = self._split_sections(criteria_text)

        # Step 2: Segment into sentences
        inc_sentences = self._segment(inc_text)
        exc_sentences = self._segment(exc_text)

        # Step 3: Extract structured conditions
        inclusion = []
        exclusion = []
        flags = []

        for sent in inc_sentences:
            conditions, sent_flags = self._extract_conditions(sent)
            inclusion.extend(conditions)
            flags.extend(sent_flags)

        for sent in exc_sentences:
            conditions, sent_flags = self._extract_conditions(sent)
            exclusion.extend(conditions)
            flags.extend(sent_flags)

        # Step 4: Confidence
        total = len(inclusion) + len(exclusion)
        flagged = len(flags)
        confidence = max(0.0, min(1.0, 1.0 - (flagged / max(total + flagged, 1))))

        return {
            'inclusion': inclusion,
            'exclusion': exclusion,
            'parse_confidence': round(confidence, 3),
            'low_confidence_flags': flags,
            'raw_text': criteria_text
        }

    # ── Section splitting ─────────────────────────────────────────

    def _split_sections(self, text: str) -> Tuple[str, str]:
        """Split text into inclusion and exclusion sections."""
        text_clean = text.strip()

        # Try explicit section headers
        inc_pattern = re.compile(
            r'inclusion\s*criteria\s*:?\s*(.*?)(?=exclusion\s*criteria|$)',
            re.IGNORECASE | re.DOTALL
        )
        exc_pattern = re.compile(
            r'exclusion\s*criteria\s*:?\s*(.*?)(?=inclusion\s*criteria|$)',
            re.IGNORECASE | re.DOTALL
        )

        inc_match = inc_pattern.search(text_clean)
        exc_match = exc_pattern.search(text_clean)

        inc_text = inc_match.group(1).strip() if inc_match else text_clean
        exc_text = exc_match.group(1).strip() if exc_match else ''

        return inc_text, exc_text

    # ── Sentence segmentation ────────────────────────────────────

    def _segment(self, text: str) -> List[str]:
        """Break text into individual criteria sentences."""
        if not text:
            return []

        if self.nlp:
            doc = self.nlp(text)
            sentences = [sent.text.strip() for sent in doc.sents]
        else:
            sentences = re.split(r'[;.\n]', text)

        # Also split on bullet/semicolon patterns
        expanded = []
        for sent in sentences:
            parts = re.split(r';\s*', sent)
            expanded.extend(parts)

        return [s.strip() for s in expanded if s.strip() and len(s.strip()) > 5]

    # ── Condition extraction ─────────────────────────────────────

    def _extract_conditions(self, sentence: str) -> Tuple[List[Dict], List[str]]:
        """
        Extract structured conditions from a single sentence.
        Returns (conditions_list, low_confidence_flags).
        """
        conditions = []
        flags = []
        matched = False

        # 1. Age criteria
        age_conds = self._extract_age(sentence)
        if age_conds:
            conditions.extend(age_conds)
            matched = True

        # 2. Lab value criteria
        lab_conds = self._extract_labs(sentence)
        if lab_conds:
            conditions.extend(lab_conds)
            matched = True

        # 3. Diagnosis criteria
        diag_conds = self._extract_diagnoses(sentence)
        if diag_conds:
            conditions.extend(diag_conds)
            matched = True

        # 4. Medication criteria
        med_conds = self._extract_medications(sentence)
        if med_conds:
            conditions.extend(med_conds)
            matched = True

        # 5. Gender criteria
        gender_cond = self._extract_gender(sentence)
        if gender_cond:
            conditions.append(gender_cond)
            matched = True

        # 6. Time-bound criteria (e.g., "within last 6 months")
        time_conds = self._extract_time_constraints(sentence)
        if time_conds:
            conditions.extend(time_conds)
            matched = True

        # If nothing matched, flag for manual review
        if not matched and len(sentence) > 10:
            flags.append(f"Low confidence parse — manual review recommended: '{sentence[:120]}'")

        return conditions, flags

    # ── Age extraction ────────────────────────────────────────────

    def _extract_age(self, sentence: str) -> List[Dict]:
        results = []
        s = sentence.lower()

        # Range: "age 18-65", "aged 18 to 65", "18-75 years"
        range_patterns = [
            r'age[ds]?\s*(?:between\s*)?(\d+)\s*(?:to|-|and)\s*(\d+)',
            r'(\d+)\s*(?:to|-)\s*(\d+)\s*years?\s*(?:old|of\s*age)?',
        ]
        for pat in range_patterns:
            m = re.search(pat, s)
            if m:
                results.append({
                    'field': 'age',
                    'operator': 'between',
                    'value': [int(m.group(1)), int(m.group(2))]
                })
                return results

        # Single bound: "age >= 18", "age < 65"
        single_patterns = [
            (r'age[ds]?\s*(>=|≥|greater\s*than\s*or\s*equal)\s*(\d+)', '>='),
            (r'age[ds]?\s*(<=|≤|less\s*than\s*or\s*equal)\s*(\d+)', '<='),
            (r'age[ds]?\s*(>|greater\s*than|older\s*than)\s*(\d+)', '>'),
            (r'age[ds]?\s*(<|less\s*than|younger\s*than)\s*(\d+)', '<'),
            (r'at\s*least\s*(\d+)\s*years?', '>='),
            (r'older\s*than\s*(\d+)', '>'),
            (r'younger\s*than\s*(\d+)', '<'),
        ]
        for pat, op in single_patterns:
            m = re.search(pat, s)
            if m:
                val = int(m.group(2)) if m.lastindex >= 2 else int(m.group(1))
                results.append({'field': 'age', 'operator': op, 'value': val})
                return results

        return results

    # ── Lab value extraction ──────────────────────────────────────

    def _extract_labs(self, sentence: str) -> List[Dict]:
        results = []
        s = sentence.lower()

        for pattern, lab_name in self.LAB_PATTERNS:
            if re.search(pattern, s, re.IGNORECASE):
                # Find the operator and value near this lab mention
                # Pattern: "HbA1c >= 7.5%", "HbA1c between 7.0-10.5%"
                lab_re = re.compile(
                    r'(?:' + pattern + r')\s*(?:of\s*|level\s*|score\s*|value\s*|between\s*)?'
                    r'(>=|<=|>|<|≥|≤|=)?\s*'
                    r'(\d+\.?\d*)\s*%?\s*'
                    r'(?:(?:to|-)\s*(\d+\.?\d*))?',
                    re.IGNORECASE
                )
                m = lab_re.search(s)
                if m and m.group(2):
                    op = m.group(1) or '='
                    op = op.replace('≥', '>=').replace('≤', '<=')
                    val1 = float(m.group(2))
                    val2 = m.group(3)
                    if val2:
                        results.append({
                            'field': 'lab',
                            'name': lab_name,
                            'operator': 'between',
                            'value': [val1, float(val2)]
                        })
                    else:
                        results.append({
                            'field': 'lab',
                            'name': lab_name,
                            'operator': op,
                            'value': val1
                        })
                else:
                    # Lab mentioned but no value found
                    results.append({
                        'field': 'lab',
                        'name': lab_name,
                        'operator': 'present',
                        'value': None
                    })

        return results

    # ── Diagnosis extraction ──────────────────────────────────────

    def _extract_diagnoses(self, sentence: str) -> List[Dict]:
        results = []
        s = sentence.lower()

        for pattern, code, system, display in self.CONDITION_PATTERNS:
            if re.search(pattern, s, re.IGNORECASE):
                results.append({
                    'field': 'diagnosis',
                    'code': code,
                    'system': system,
                    'display': display,
                    'operator': 'has'
                })

        return results

    # ── Medication extraction ─────────────────────────────────────

    def _extract_medications(self, sentence: str) -> List[Dict]:
        results = []
        s = sentence.lower()

        for med in self.MEDICATION_KEYWORDS:
            if med in s:
                # Check for time constraint
                time_match = re.search(
                    med + r'.*?(?:within|in|past|last|previous)\s*(?:the\s*)?(?:last\s*)?(\d+)\s*(month|year|week|day)s?',
                    s, re.IGNORECASE
                )
                cond: Dict[str, Any] = {
                    'field': 'medication',
                    'name': med,
                    'operator': 'taking'
                }
                if time_match:
                    cond['within_months'] = self._to_months(
                        int(time_match.group(1)),
                        time_match.group(2)
                    )
                results.append(cond)

        # Also check for "no prior X therapy" patterns
        no_prior = re.findall(
            r'no\s+(?:prior|previous|history\s+of)\s+(\w+(?:\s+\w+)?)\s*(?:therapy|treatment|use)?',
            s, re.IGNORECASE
        )
        for med_name in no_prior:
            med_lower = med_name.lower().strip()
            if not any(r.get('name') == med_lower for r in results):
                results.append({
                    'field': 'medication',
                    'name': med_lower,
                    'operator': 'not_taking'
                })

        return results

    # ── Gender extraction ─────────────────────────────────────────

    def _extract_gender(self, sentence: str) -> Optional[Dict]:
        s = sentence.lower()
        if re.search(r'\bfemale\s*patients?\b|\bwomen\b', s) and not re.search(r'\bmale\b(?!\s*and)', s):
            return {'field': 'gender', 'operator': '=', 'value': 'female'}
        if re.search(r'\bmale\s*patients?\b|\bmen\b', s) and not re.search(r'\bfemale\b', s):
            return {'field': 'gender', 'operator': '=', 'value': 'male'}
        return None

    # ── Time constraint extraction ────────────────────────────────

    def _extract_time_constraints(self, sentence: str) -> List[Dict]:
        results = []
        s = sentence.lower()

        # "stable medications for 3 months"
        stable = re.search(r'stable\s+(?:on\s+)?(?:current\s+)?medications?\s*(?:for\s*)?(\d+)\s*(month|year|week)s?', s)
        if stable:
            results.append({
                'field': 'medication_stability',
                'operator': '>=',
                'value': self._to_months(int(stable.group(1)), stable.group(2)),
                'unit': 'months'
            })

        # "diagnosed for at least X months/years"
        diag_dur = re.search(r'diagnosed\s+(?:with\s+\w+\s+)?(?:for\s+)?(?:at\s+least\s+)?(\d+)\s*(month|year)s?', s)
        if diag_dur:
            results.append({
                'field': 'diagnosis_duration',
                'operator': '>=',
                'value': self._to_months(int(diag_dur.group(1)), diag_dur.group(2)),
                'unit': 'months'
            })

        # "life expectancy < 2 years"
        life_exp = re.search(r'life\s*expectancy\s*(>=|<=|>|<)\s*(\d+)\s*(month|year)s?', s)
        if life_exp:
            results.append({
                'field': 'life_expectancy',
                'operator': life_exp.group(1),
                'value': self._to_months(int(life_exp.group(2)), life_exp.group(3)),
                'unit': 'months'
            })

        return results

    # ── Utilities ─────────────────────────────────────────────────

    def _to_months(self, value: int, unit: str) -> int:
        unit = unit.lower()
        if 'year' in unit:
            return value * 12
        if 'week' in unit:
            return max(1, value // 4)
        if 'day' in unit:
            return max(1, value // 30)
        return value
