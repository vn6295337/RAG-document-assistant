# Deploy RAG PoC to Streamlit Cloud

**Repository:** https://github.com/vn6295337/poc-rag

## Step-by-Step Deployment Guide

### 1. Go to Streamlit Cloud

Visit: **https://share.streamlit.io**

### 2. Sign In with GitHub

- Click "Sign in with GitHub"
- Authorize Streamlit Cloud to access your repositories

### 3. Deploy New App

Click **"New app"** or **"Deploy an app"**

### 4. Configure Deployment

Fill in the following details:

**Repository:**
- Repository: `vn6295337/poc-rag`
- Branch: `main`
- Main file path: `ui/app.py`

### 5. Add Secrets (Environment Variables)

Click **"Advanced settings"** > **"Secrets"**

Copy and paste this configuration (replace with your actual API keys):

```toml
# Pinecone (Required)
PINECONE_API_KEY = "your_pinecone_api_key_here"
PINECONE_INDEX_NAME = "rag-semantic-384"

# LLM Providers (at least one required)
GEMINI_API_KEY = "your_gemini_api_key_here"
GEMINI_MODEL = "gemini-2.5-flash"

GROQ_API_KEY = "your_groq_api_key_here"
GROQ_MODEL = "llama-3.1-8b-instant"

OPENROUTER_API_KEY = "your_openrouter_api_key_here"
OPENROUTER_MODEL = "mistralai/mistral-7b-instruct:free"
```

**Where to get your API keys:**

You should have these stored in `~/secrets/`:
```bash
cat ~/secrets/pinecone.key     # Pinecone API key
cat ~/secrets/gemini.key       # Gemini API key
cat ~/secrets/groq.key         # Groq API key
cat ~/secrets/openrouter.key   # OpenRouter API key
```

### 6. Deploy!

Click **"Deploy"** button

**What happens next:**
- Streamlit Cloud will clone your repository
- Install dependencies from `requirements.txt`
- Start the app on their servers
- Provide you with a public URL

**Expected deployment time:** 2-5 minutes

### 7. Access Your App

Once deployed, you'll get a URL like:
```
https://your-app-name.streamlit.app
```

### 8. Test the Deployment

1. Open the URL in your browser
2. Enter a test query: "what is GDPR"
3. Click "Run Query"
4. Verify you get:
   - ✅ Answer with GDPR information
   - ✅ Citations with document references
   - ✅ Debug view with pipeline details

## Managing Your Deployment

### View Logs

In Streamlit Cloud dashboard:
- Click on your app
- Go to "Logs" tab to see real-time application logs

### Update Environment Variables

- Click on your app in the dashboard
- Go to "Settings" > "Secrets"
- Edit and save

### Redeploy

Streamlit Cloud automatically redeploys when you push to GitHub:
```bash
# Make changes locally
git add .
git commit -m "update: your changes"
git push origin main

# Streamlit Cloud will auto-deploy
```

### Manual Reboot

If needed, click **"Reboot app"** in the app menu (⋮)

## Troubleshooting

### Build Fails

**Issue:** Dependencies installation timeout

**Solution:** Streamlit Cloud sometimes has timeout issues with PyTorch. If this happens:
1. The build might succeed on retry (click "Reboot app")
2. Or use Railway/Heroku instead

### App Won't Start

**Issue:** Missing or incorrect secrets

**Solution:**
- Check "Logs" tab for specific error
- Verify all required environment variables are set
- Make sure API keys are valid (no quotes or extra spaces)

### Retrieval Errors

**Issue:** "Pinecone index not found"

**Solution:**
- Verify `PINECONE_INDEX_NAME = "rag-semantic-384"` in secrets
- Check that the index exists in your Pinecone dashboard
- Verify Pinecone API key is correct

### LLM Generation Fails

**Issue:** All LLM providers fail

**Solution:**
- Check at least one LLM API key is valid
- Verify model names are correct
- Check logs for specific error messages

## Features

✅ **Free tier includes:**
- Unlimited public apps
- Community support
- Automatic SSL/HTTPS
- Auto-deployment on git push
- Basic analytics

❌ **Free tier limitations:**
- Apps sleep after inactivity (auto-wake on request)
- Limited resources (1GB RAM)
- Public apps only (no private apps)

## Cold Start Performance

**Expected behavior:**
- First request after sleep: ~15-30 seconds (waking up + model loading)
- Subsequent requests: ~2-5 seconds
- App sleeps after ~7 days of inactivity

## Cost

**$0** - Completely free for public apps!

## Next Steps After Deployment

1. ✅ Test with multiple queries
2. ✅ Share the public URL
3. ✅ Update README with deployment URL
4. ✅ Add to portfolio/resume

## Quick Reference

**Streamlit Cloud Dashboard:** https://share.streamlit.io
**Documentation:** https://docs.streamlit.io/streamlit-community-cloud
**Status Page:** https://streamlitstatus.com
