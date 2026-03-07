"""
NLP Embedding Extractor for Clinical Trial Descriptions
Uses sentence-transformers to generate semantic embeddings from trial text.
Supports medical domain models like BioBERT and general models like all-MiniLM.
"""

import numpy as np
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class TrialEmbeddingExtractor:
    """
    Extracts semantic embeddings from clinical trial descriptions.
    Uses pre-trained sentence transformers for medical/scientific text.
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize embedding model.
        
        Args:
            model_name: HuggingFace model name. Options:
                - 'all-MiniLM-L6-v2' (fast, general purpose, 384 dims)
                - 'all-mpnet-base-v2' (better quality, 768 dims)
                - 'pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb' (medical)
        """
        self.model = None
        self.model_name = model_name
        self.embedding_dim = 384  # Default for MiniLM
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                print(f"🔄 Loading embedding model: {model_name}")
                self.model = SentenceTransformer(model_name)
                self.embedding_dim = self.model.get_sentence_embedding_dimension()
                print(f"✓ Loaded embedding model (dim={self.embedding_dim})")
            except Exception as e:
                print(f"⚠ Failed to load {model_name}: {e}")
                print("  Embeddings will be disabled")
                self.model = None
        else:
            print("⚠ sentence-transformers not available. Install with: pip install sentence-transformers")
    
    def extract_trial_embedding(self, trial: Dict) -> np.ndarray:
        """
        Extract semantic embedding from trial description.
        Combines title, condition, and eligibility criteria.
        
        Returns:
            Embedding vector (384-dim or 768-dim depending on model)
        """
        if self.model is None:
            return np.zeros(self.embedding_dim)
        
        # Combine relevant trial text
        text_parts = []
        
        if trial.get('title'):
            text_parts.append(trial['title'])
        
        if trial.get('condition'):
            text_parts.append(f"Condition: {trial['condition']}")
        
        if trial.get('eligibility_criteria'):
            # Truncate long criteria to avoid token limits
            criteria = trial['eligibility_criteria'][:500]
            text_parts.append(criteria)
        
        combined_text = " ".join(text_parts)
        
        try:
            embedding = self.model.encode(combined_text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            print(f"⚠ Failed to encode trial {trial.get('trial_id', 'unknown')}: {e}")
            return np.zeros(self.embedding_dim)
    
    def extract_patient_embedding(self, patient: Dict) -> np.ndarray:
        """
        Extract semantic embedding from patient profile.
        Combines diagnosis, medications, and conditions.
        
        Returns:
            Embedding vector (same dimension as trial embeddings)
        """
        if self.model is None:
            return np.zeros(self.embedding_dim)
        
        # Combine relevant patient text
        text_parts = []
        
        # Diagnoses
        diagnoses = patient.get('diagnosis', [])
        if isinstance(diagnoses, list) and diagnoses:
            text_parts.append("Diagnoses: " + ", ".join(str(d) for d in diagnoses[:5]))
        
        # Medications
        medications = patient.get('medications', [])
        if isinstance(medications, list) and medications:
            text_parts.append("Medications: " + ", ".join(str(m) for m in medications[:5]))
        
        # Age and gender
        age = patient.get('age') or patient.get('age_range', '')
        gender = patient.get('gender', '')
        if age or gender:
            text_parts.append(f"Patient: {age} years old, {gender}")
        
        combined_text = " ".join(text_parts)
        
        if not combined_text.strip():
            return np.zeros(self.embedding_dim)
        
        try:
            embedding = self.model.encode(combined_text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            print(f"⚠ Failed to encode patient: {e}")
            return np.zeros(self.embedding_dim)
    
    def compute_similarity(self, patient_embedding: np.ndarray, 
                          trial_embedding: np.ndarray) -> float:
        """
        Compute cosine similarity between patient and trial embeddings.
        
        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Cosine similarity
        dot_product = np.dot(patient_embedding, trial_embedding)
        norm_patient = np.linalg.norm(patient_embedding)
        norm_trial = np.linalg.norm(trial_embedding)
        
        if norm_patient == 0 or norm_trial == 0:
            return 0.0
        
        similarity = dot_product / (norm_patient * norm_trial)
        
        # Normalize to 0-1 range (cosine similarity is -1 to 1)
        normalized = (similarity + 1) / 2
        
        return float(np.clip(normalized, 0.0, 1.0))
    
    def extract_embedding_features(self, patient: Dict, trial: Dict) -> Dict[str, float]:
        """
        Extract embedding-based features for ML model.
        
        Returns:
            Dictionary with:
            - semantic_similarity: Overall cosine similarity
            - embedding_dim_N: Top N principal components (optional)
        """
        patient_emb = self.extract_patient_embedding(patient)
        trial_emb = self.extract_trial_embedding(trial)
        
        similarity = self.compute_similarity(patient_emb, trial_emb)
        
        features = {
            'semantic_similarity': round(similarity, 4)
        }
        
        # Optionally add top embedding dimensions as features
        # (Uncomment if you want to use raw embedding dimensions)
        # for i in range(min(10, self.embedding_dim)):
        #     features[f'patient_emb_{i}'] = float(patient_emb[i])
        #     features[f'trial_emb_{i}'] = float(trial_emb[i])
        
        return features


# Global singleton instance
_embedding_extractor = None


def get_embedding_extractor(model_name: str = 'all-MiniLM-L6-v2') -> TrialEmbeddingExtractor:
    """Get or create global embedding extractor instance."""
    global _embedding_extractor
    if _embedding_extractor is None:
        _embedding_extractor = TrialEmbeddingExtractor(model_name)
    return _embedding_extractor
