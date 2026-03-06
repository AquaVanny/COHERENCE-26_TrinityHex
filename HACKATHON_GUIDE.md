# 🏥 AI-Powered Clinical Trial Matching Engine - Hackathon MVP

## 🎯 Problem Statement Solution
**Track 1: Health & Digital Wellbeing - AI-Powered Clinical Trial Eligibility & Matching Engine**

This system addresses the challenge of matching anonymized patient health records to suitable clinical trials using AI and machine learning techniques.

## ✨ Key Features Implemented

### 🔒 **Patient Anonymization**
- Advanced anonymization preserving clinical relevance
- Hash-based consistent ID generation
- Age range generalization (pediatric, 18-29, 30-44, 45-64, 65+)
- Geographic region mapping
- Temporal data generalization

### 🤖 **AI-Powered Matching**
- Rule-based eligibility checking
- ML-powered similarity scoring using scikit-learn
- TF-IDF vectorization for text analysis
- Confidence scoring for each match

### 📊 **Explainable AI**
- Detailed explanations for each match decision
- Confidence scores with transparency
- Criteria-by-criteria analysis
- Clear reasoning for inclusion/exclusion

### 🌍 **Geographic Filtering**
- Location-based trial filtering
- Regional anonymization
- Multi-location trial support

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Python API     │    │   Sample Data   │
│   (React+Vite)  │◄──►│   (Flask+ML)     │◄──►│   (JSON Files)  │
│   Port: 5173    │    │   Port: 5000     │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start Guide

### 1. Start the AI Matching Engine
```bash
cd python-api
python app.py
```
**Status:** ✅ Running on http://localhost:5000

### 2. Start the Frontend Dashboard
```bash
cd frontend
npm run dev
```
**Status:** ✅ Running on http://localhost:5173

### 3. Access the System
- **Dashboard:** http://localhost:5173
- **Patient Matcher:** http://localhost:5173/matcher
- **Trial Explorer:** http://localhost:5173/trials

## 🔧 API Endpoints

### Core Matching Endpoints
- `GET /api/health` - System health check
- `POST /api/anonymize-patient` - Anonymize patient data
- `POST /api/match-trials` - Match patient to trials
- `POST /api/parse-criteria` - Parse eligibility criteria
- `GET /api/demo-match` - Run demo matching
- `GET /api/sample-data` - Get sample datasets

### File Upload Endpoints
- `POST /api/upload-patients` - Upload and process JSON/CSV patient files
- `POST /api/upload-and-match` - Upload patient files and immediately match to trials

## 📋 Demo Scenarios

### Scenario 1: Diabetes Patient Matching
**Patient Profile:**
- Age: 45, Male, Type 2 Diabetes + Hypertension
- Medications: Metformin, Lisinopril
- HbA1c: 8.2

**Expected Matches:**
1. **NCT12345678** - Phase III Diabetes Study (High Match)
2. **NCT99887766** - Cardiovascular Prevention (Medium Match)

### Scenario 2: Cancer Patient Matching
**Patient Profile:**
- Age: 32, Female, Breast Cancer Stage II
- Medications: Tamoxifen

**Expected Matches:**
1. **NCT87654321** - Immunotherapy Study (High Match)

## 🎨 Frontend Features

### Dashboard
- Live demo results with real-time AI matching
- System statistics and performance metrics
- Visual match confidence indicators
- Explainable AI reasoning display

### Patient Matcher
- JSON patient data input
- Real-time anonymization
- Ranked trial recommendations
- Detailed eligibility explanations

### Trial Explorer
- Browse all available trials
- Advanced filtering (phase, condition, location)
- Search functionality
- Detailed trial information

## 🔬 Technical Implementation

### File Upload & Processing
- **JSON/CSV Support** - Upload patient data in multiple formats
- **Drag & Drop Interface** - Modern file upload with validation
- **Automatic Parsing** - Smart column mapping for CSV files
- **Batch Processing** - Handle multiple patients simultaneously

### Machine Learning Components
- **Scikit-learn** for classification and similarity
- **TF-IDF Vectorization** for text analysis
- **Random Forest** for complex eligibility rules
- **Pandas/NumPy** for data processing

### Anonymization Algorithm
```python
# Hash-based consistent anonymization
anonymous_id = f"ANON_{hash(original_id)[:12]}"

# Age range generalization
age_ranges = {
    "pediatric": (0, 17),
    "18-29": (18, 29),
    "30-44": (30, 44),
    "45-64": (45, 64),
    "65+": (65, 100)
}
```

### Matching Algorithm
1. **Parse Eligibility Criteria** - Extract structured rules
2. **Anonymize Patient Data** - Preserve clinical relevance
3. **Rule-Based Matching** - Age, gender, condition checks
4. **ML Similarity Scoring** - Advanced pattern matching
5. **Confidence Calculation** - Data completeness assessment
6. **Explanation Generation** - Transparent reasoning

## 📊 Sample Data

### Patients (4 samples)
- Diabetes + Hypertension (Male, 45)
- Breast Cancer (Female, 32)
- Alzheimer's + Depression (Male, 67)
- Asthma + Allergies (Female, 28)

### Clinical Trials (5 samples)
- Phase III Diabetes Treatment
- Phase II Breast Cancer Immunotherapy
- Phase II Alzheimer's Cognitive Enhancement
- Phase III Severe Asthma Biologic Therapy
- Phase IV Cardiovascular Prevention

## 🛡️ Ethical Safeguards

### Privacy Protection
- No PII stored or transmitted
- Hash-based anonymization
- Regional location generalization
- Temporal data obfuscation

### Transparency
- Explainable AI decisions
- Confidence score disclosure
- Clear matching criteria
- Audit trail capability

## 🏆 Hackathon Deliverables

### ✅ **Working Prototype**
- Fully functional web application
- Real-time patient-trial matching
- AI-powered recommendations

### ✅ **Patient Data Ingestion**
- JSON format support
- Automatic anonymization
- Validation and error handling

### ✅ **Eligibility Parsing**
- Natural language processing
- Structured criteria extraction
- Rule-based logic conversion

### ✅ **ML-Powered Matching**
- Scikit-learn implementation
- Confidence scoring
- Similarity analysis

### ✅ **Explainable Results**
- Detailed match explanations
- Criteria-by-criteria analysis
- Confidence indicators

### ✅ **Geographic Filtering**
- Location-based matching
- Regional anonymization
- Multi-site trial support

## 🚀 Next Steps for Production

1. **Enhanced ML Models**
   - Deep learning for complex patterns
   - Medical ontology integration
   - Advanced NLP with spaCy/transformers

2. **Database Integration**
   - PostgreSQL for patient data
   - Redis for caching
   - Real-time trial updates

3. **Security Enhancements**
   - OAuth authentication
   - Audit logging
   - HIPAA compliance

4. **Scalability**
   - Microservices architecture
   - Container deployment
   - Load balancing

## 📈 Impact & Innovation

### Healthcare Research Acceleration
- Automated patient-trial matching
- Reduced recruitment time
- Improved trial diversity

### AI Transparency
- Explainable matching decisions
- Confidence-based recommendations
- Ethical AI implementation

### Privacy-First Design
- Advanced anonymization
- Clinical relevance preservation
- Regulatory compliance ready

---

**🎉 Hackathon MVP Status: COMPLETE**

The AI-Powered Clinical Trial Matching Engine successfully demonstrates intelligent patient-trial matching with explainable AI, robust anonymization, and a modern web interface. Ready for demo and further development!
