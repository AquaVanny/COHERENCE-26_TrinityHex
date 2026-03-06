# Contributing to Clinical Trial Matching Platform

Thank you for your interest in contributing to our AI-powered clinical trial matching platform!

## 🚀 Quick Start for Contributors

1. **Fork the repository**
2. **Clone your fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/COHERENCE-26_TrinityHex.git
   cd COHERENCE-26_TrinityHex
   ```
3. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Make your changes**
5. **Test thoroughly**
6. **Commit with descriptive messages**
7. **Push and create a Pull Request**

## 🏗️ Development Setup

### Backend (Python/Flask)
```bash
cd python-api
pip install -r requirements.txt
python app.py
```

### Frontend (React/TypeScript)
```bash
cd frontend
npm install
npm run dev
```

## 📝 Commit Message Guidelines

We follow conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

**Example:**
```
feat: add SHAP explanations to matching results

- Implemented SHAP feature importance calculation
- Added visualization to frontend dashboard
- Updated API response schema
```

## 🧪 Testing

Before submitting a PR:
- Test all API endpoints
- Verify frontend components render correctly
- Check that patient data anonymization works
- Ensure matching algorithm produces expected results

## 🔍 Code Review Process

1. All PRs require at least one review
2. CI/CD checks must pass
3. Code must follow existing style conventions
4. Documentation must be updated if needed

## 🎯 Areas for Contribution

### High Priority
- [ ] Add more clinical trial data sources
- [ ] Improve NLP criteria parsing accuracy
- [ ] Enhance ML model with more features
- [ ] Add unit and integration tests

### Medium Priority
- [ ] UI/UX improvements
- [ ] Performance optimizations
- [ ] Additional anonymization techniques
- [ ] Export functionality enhancements

### Good First Issues
- [ ] Documentation improvements
- [ ] Bug fixes
- [ ] UI polish
- [ ] Code cleanup

## 🔐 Security & Privacy

- **Never commit real patient data** (only synthetic/anonymized)
- **No API keys or secrets** in code
- Follow HIPAA-compliant anonymization practices
- Report security issues privately to maintainers

## 📚 Resources

- [Project README](README.md)
- [API Documentation](docs/API.md) (if exists)
- [Architecture Overview](README.md#system-architecture)

## 💬 Questions?

Open an issue or reach out to the maintainers!

---

**Happy Contributing! 🎉**
