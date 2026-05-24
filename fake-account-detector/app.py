from flask import Flask, render_template, request, jsonify
from pathlib import Path
import pandas as pd
import joblib
from utils.features import extract_features
from utils.verdict import compute_verdict
from utils.instagram_fetch import fetch_instagram_profile

app = Flask(__name__, template_folder='templates', static_folder='static')

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model" / "account_model.pkl"

# Load model at startup
try:
    data = joblib.load(MODEL_PATH)
    # The serialized artifact stores both model object and the training column order.
    MODEL = data["model"]
    FEATURE_COLUMNS = data["feature_columns"]
    print("Model loaded successfully")
except Exception as e:
    print(f"Error loading model: {e}")
    MODEL = None
    FEATURE_COLUMNS = []


# Serve the main HTML page
@app.route('/')
def index():
    return render_template('index.html')


# API: Analyze account
@app.route('/api/analyze', methods=['POST'])
def analyze_account():
    """Analyze account and return prediction"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Invalid or missing JSON body"}), 400
        
        # Extract optional profile enrichment if present
        profile = data.get('profile') or {}

        # Extract features from input (includes best-effort enrichment fields)
        # Defensive conversions for numeric fields
        def _int_or_zero(val):
            try:
                return int(val)
            except Exception:
                return 0

        features = extract_features(
            username=data.get('username', ''),
            bio=data.get('bio', ''),
            followers_count=_int_or_zero(data.get('followers_count', 0)),
            following_count=_int_or_zero(data.get('following_count', 0)),
            media_count=_int_or_zero(data.get('media_count', 0)),
            has_profile_pic=_int_or_zero(data.get('has_profile_pic', 0)),
            is_verified=bool(profile.get('is_verified', False)),
            external_url=profile.get('external_url') or profile.get('external_url', None),
            followers_list=profile.get('followers'),
            following_list=profile.get('following'),
            posts=profile.get('posts'),
        )
        
        # Make prediction
        used_fallback = True
        if MODEL is not None and FEATURE_COLUMNS:
            # Ensure feature vector contains all feature columns expected by the model
            for col in FEATURE_COLUMNS:
                if col not in features:
                    features[col] = 0.0

            feature_frame = pd.DataFrame([[features.get(col, 0.0) for col in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
            try:
                # predict_proba()[1] is probability of the "Fake" class.
                probability = float(MODEL.predict_proba(feature_frame)[0][1])
                prediction = "Fake" if probability >= 0.5 else "Real"
                used_fallback = False
            except Exception as e:
                # If model prediction fails for any reason, fall back to heuristic
                print(f"Model prediction error, falling back to heuristic: {e}")

        if used_fallback:
            # Fallback heuristic when model artifact is not available or prediction failed
            prob = 0.5
            # more followers reduces fake probability
            prob -= min(0.3, float(features.get('followers_count', 0)) / 100000.0)
            # missing profile pic increases fake probability
            prob += 0.15 if features.get('has_profile_pic', 0.0) == 0.0 else -0.05
            # verified decreases fake probability strongly
            prob -= 0.25 if features.get('is_verified_flag', 0.0) == 1.0 else 0.0
            # many external links increases suspicion slightly
            prob += min(0.2, features.get('linked_external_profiles_count', 0.0) * 0.05)
            probability = float(max(0.01, min(0.99, prob)))
            prediction = "Fake" if probability >= 0.5 else "Real"
        
        # Compute verdict
        verdict_result = compute_verdict(
            account_prediction=prediction,
            account_confidence=probability,
        )
        
        # Include computed heuristic features for display (model uses FEATURE_COLUMNS only)
        display_features = {k: v for k, v in features.items() if k not in set(FEATURE_COLUMNS or [])}

        return jsonify({
            "success": True,
            "prediction": prediction,
            "confidence": round(probability, 4),
            "verdict": verdict_result.verdict,
            "risk_score": verdict_result.risk_score,
            "reasoning": verdict_result.reasoning,
            "features": display_features,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# API: Fetch Instagram profile
@app.route('/api/fetch-instagram', methods=['POST'])
def fetch_instagram():
    """Fetch profile data from Instagram using Playwright"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        headless = data.get('headless', True)
        
        if not username:
            return jsonify({"success": False, "error": "Username required"}), 400
        
        profile, error = fetch_instagram_profile(
                username,
                session_id=data.get('session_id'),
            fetch_details=data.get('fetch_details', False),
                headless=headless,
            )
        
        if profile is None:
            return jsonify({
                "success": False,
                "error": error or "Could not fetch Instagram profile. Profile may be private or not exist."
            }), 400
        
        profile_dict = profile.to_dict()
        # Limit followers/following lists to avoid huge responses
        if 'followers' in profile_dict and isinstance(profile_dict['followers'], list):
            profile_dict['followers'] = profile_dict['followers'][:300]
        if 'following' in profile_dict and isinstance(profile_dict['following'], list):
            profile_dict['following'] = profile_dict['following'][:300]
        # Keep a numeric flag for the form select control in the UI.
        profile_dict['has_profile_pic'] = 1 if profile_dict.get('profile_pic_url') else 0
        
        return jsonify({
            "success": True,
            "profile": profile_dict,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# Health check
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    app.run(debug=False, port=5000, threaded=True)
