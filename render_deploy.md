# Deploying `fake-account-detector` to Render — notes

This repository is prepared for Render deployment. Follow the steps below.

1. Render service settings
- **Name:** fake-account-detector
- **Branch:** main
- **Region:** choose nearest (e.g., Singapore)
- **Root Directory:** (leave empty)
- **Build Command:**
```
pip install -r requirements.txt
```
- **Start Command:**
```
gunicorn wsgi:app --bind 0.0.0.0:$PORT
```

2. Environment variables
- Add secrets and config via the Render dashboard → Environment. Example variables:
  - `FLASK_ENV=production`
  - `IG_USERNAME` (if used)
  - `IG_PASSWORD` (if used)

3. Playwright / Instagram scraping
- Playwright was removed from `requirements.txt` because installing Playwright's browser binaries on Render's free instances requires root privileges and often fails during build.
- Options:
  - Keep the current setup (no Playwright): the `/api/fetch-instagram` endpoint will not work on Render. Use local scraping or a separate scraping service.
  - Use a paid Render instance or a VM where you can run `playwright install --with-deps` (root) during build.
  - Replace scraping with an external API (e.g., a paid Instagram data provider) and set credentials via environment variables.

4. Model files and storage
- If `model/account_model.pkl` is large, consider storing it in S3 or GitHub Releases and download at runtime using an environment variable `MODEL_URL`.

5. Troubleshooting
- Check Logs in Render dashboard for build/run errors.
- If you see browser install failures, remove Playwright and re-deploy (this repo does that by default).

6. Quick test commands
```
curl https://<your-service>.onrender.com/health
curl -X POST https://<your-service>.onrender.com/api/analyze -H "Content-Type: application/json" -d '{"username":"test","followers_count":10}'
```

If you want, I can add a small change to the code to return a friendly message when Playwright is unavailable. Ask me to implement that.
