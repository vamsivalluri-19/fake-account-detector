# Fake Account Detector

[![Python](https://img.shields.io/badge/Python-3.14%2B-FFB300?style=for-the-badge&logo=python&logoColor=111111)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-111111?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.8-FF6F00?style=for-the-badge&logo=scikitlearn&logoColor=white)](https://scikit-learn.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.58-00C853?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev/python/)
[![Model Accuracy](https://img.shields.io/badge/Model_Accuracy-97.07%25-00ACC1?style=for-the-badge)](model/metrics.json)
[![Last Updated](https://img.shields.io/badge/Last_Updated-2026--03--27-FF5722?style=for-the-badge&logo=github&logoColor=white)](README.md)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-2962FF?style=for-the-badge)](README.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-FDD835?style=for-the-badge)](LICENSE)

Detect suspicious Instagram accounts using a trained machine learning model and a simple Flask web app.

## What This Project Does

- Predicts whether an account is `Fake` or `Real` based on account metadata.
- Generates a practical verdict (`High Risk Fake`, `Suspicious`, `Likely Genuine`, or `Needs Review`) with a risk score.
- Supports both:
  - manual input from the UI
  - optional profile fetch from Instagram by username

## Core Features

- Flask API + frontend dashboard
- RandomForest-based classifier
- Feature engineering for account signals (username pattern, bio length, follower/following ratio, etc.)
- Training pipeline with saved model artifact and metrics


## Tech Stack

- Python 3.14+
- Flask
- scikit-learn
- pandas / numpy
- Playwright + BeautifulSoup4 (for profile fetch)


## Quick Start

### 1. Create and activate a virtual environment

Windows (PowerShell):

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

Using `uv` (recommended for this project setup):

```bash
uv sync
```



### 3. Install Playwright browser binaries

```bash
python -m playwright install
```

### 4. Train model (if missing or if retraining)

```bash
python model.py
```

This generates:

- `model/account_model.pkl`
- `model/metrics.json`

### 5. Run the app

```bash
python app.py
```

Open: `http://127.0.0.1:5000`

## Model Performance

Current metrics in `model/metrics.json`:

- Accuracy: `0.9707`
- Precision: `0.9714`
- Recall: `0.8500`
- F1: `0.9067`

## Notes and Limitations

- This is a screening aid, not a definitive identity verification system.
- Scraping-based Instagram fetch can fail due to private profiles, anti-bot protections, rate limits, or layout changes.
- Prediction confidence is model certainty, not ground truth.
- Use manual review before moderation or policy decisions.
