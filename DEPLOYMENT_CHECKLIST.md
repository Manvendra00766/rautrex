# Deployment Checklist - Render & Vercel

## Pre-Deployment (Local)

- [x] Code pushed to GitHub
- [x] All tests passing
- [x] `.env` example created
- [x] `requirements.txt` updated
- [x] `vercel.json` configured
- [x] `render.yaml` (if needed)

## Backend Deployment - Render

### 1. Create Render Account
- [ ] Go to https://render.com
- [ ] Sign up with GitHub account
- [ ] Connect GitHub repository
- [ ] Authorize Render to access repo

### 2. Create PostgreSQL Database
- [ ] Click "New +" → "PostgreSQL"
- [ ] Set Name: `rautrex-db`
- [ ] Set Database: `rautrex`
- [ ] Set Region: (closest to users)
- [ ] Select Free Plan
- [ ] Click "Create Database"
- [ ] Copy Database URL
- [ ] Save credentials securely
- [ ] Wait for database to start (~2 min)

### 3. Create Web Service
- [ ] Click "New +" → "Web Service"
- [ ] Select `rautrex` repository
- [ ] Click "Connect"

### 4. Configure Web Service
- [ ] Name: `rautrex-api`
- [ ] Region: (same as database)
- [ ] Branch: `main`
- [ ] Root Directory: (leave empty)
- [ ] Build Command: `pip install -r requirements.txt`
- [ ] Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- [ ] Plan: Free

### 5. Add Environment Variables
In Settings → Environment:
- [ ] `DATABASE_URL` = (paste from database)
- [ ] `ENVIRONMENT` = `production`
- [ ] `CORS_ORIGINS` = `https://rautrex.vercel.app` (update later)
- [ ] `SECRET_KEY` = (generate 32+ char random)
- [ ] `ALGORITHM` = `HS256`
- [ ] `ACCESS_TOKEN_EXPIRE_MINUTES` = `1440`
- [ ] `REFRESH_TOKEN_EXPIRE_DAYS` = `7`

### 6. Deploy Backend
- [ ] Scroll to bottom
- [ ] Click "Create Web Service"
- [ ] Wait for deployment (~2-5 min)
- [ ] Check for success message
- [ ] Note the URL: `https://rautrex-api.onrender.com`

### 7. Verify Backend
- [ ] Open `https://rautrex-api.onrender.com/docs`
- [ ] Should see Swagger API documentation
- [ ] Try test endpoint
- [ ] Check Logs for errors

## Frontend Deployment - Vercel

### 1. Create Vercel Account
- [ ] Go to https://vercel.com
- [ ] Sign up with GitHub account
- [ ] Authorize Vercel to access GitHub

### 2. Import Project
- [ ] Click "New Project"
- [ ] Search for `rautrex` repository
- [ ] Click "Import"

### 3. Configure Project
- [ ] Framework Preset: `Next.js`
- [ ] Root Directory: `./frontend`
- [ ] Node Version: `18.x`
- [ ] Build Command: (default Next.js)
- [ ] Output Directory: (default `.next`)

### 4. Add Environment Variables
- [ ] `NEXT_PUBLIC_API_URL` = `https://rautrex-api.onrender.com`
- [ ] Apply to: Production, Preview, Development

### 5. Deploy Frontend
- [ ] Click "Deploy"
- [ ] Wait for build (~1-3 min)
- [ ] Check for success message
- [ ] Note the URL: `https://rautrex.vercel.app`

### 6. Verify Frontend
- [ ] Open `https://rautrex.vercel.app`
- [ ] Should load dashboard
- [ ] Try creating portfolio
- [ ] Check console for errors

## Post-Deployment

### 1. Update Backend CORS
- [ ] Go to Render Dashboard
- [ ] Open `rautrex-api` settings
- [ ] Update `CORS_ORIGINS`:
  ```
  https://rautrex.vercel.app,https://rautrex-frontend.vercel.app
  ```
- [ ] Save and wait for redeploy

### 2. Test End-to-End
- [ ] Open `https://rautrex.vercel.app/dashboard`
- [ ] Try to create portfolio
- [ ] Enter tickers: AAPL, MSFT, GOOGL
- [ ] Click Create
- [ ] Should see real metrics from Yahoo Finance
- [ ] Should show portfolio value, P&L, volatility, VaR

### 3. Monitor Deployment
- [ ] Check Render Logs for errors
- [ ] Check Vercel Logs for errors
- [ ] Test API endpoints
- [ ] Create test portfolios
- [ ] Verify real data displays

### 4. Share URLs
- [ ] Dashboard: `https://rautrex.vercel.app/dashboard`
- [ ] API Docs: `https://rautrex-api.onrender.com/docs`
- [ ] Backend: `https://rautrex-api.onrender.com`

## Common Issues & Solutions

### Backend Won't Start
**Symptoms:** Deployment fails, "No module named..."
**Solution:**
- [ ] Check `requirements.txt` has all packages
- [ ] Verify Python version compatibility
- [ ] Check build logs in Render
- [ ] Redeploy manually

### CORS Errors
**Symptoms:** "Access to XMLHttpRequest blocked by CORS policy"
**Solution:**
- [ ] Check `CORS_ORIGINS` includes frontend URL
- [ ] Verify `NEXT_PUBLIC_API_URL` is correct
- [ ] Check network tab in browser DevTools
- [ ] Restart backend

### Database Connection Failed
**Symptoms:** "could not connect to database" in logs
**Solution:**
- [ ] Verify `DATABASE_URL` is correct
- [ ] Check database is running in Render
- [ ] Verify credentials
- [ ] Test connection string locally

### Frontend Can't Reach API
**Symptoms:** "Failed to fetch" or timeout
**Solution:**
- [ ] Check `NEXT_PUBLIC_API_URL` in Vercel settings
- [ ] Verify Render backend URL is correct
- [ ] Check backend is running
- [ ] Test API directly in browser

### Real Data Not Loading
**Symptoms:** Portfolio shows empty metrics
**Solution:**
- [ ] Check yfinance in requirements.txt
- [ ] Test with simple ticker (AAPL)
- [ ] Check Render logs for yfinance errors
- [ ] Verify internet connection on Render

## Rollback Procedure

If something goes wrong:

### Render Rollback
1. Go to Render Dashboard
2. Open `rautrex-api` → Logs
3. Click on previous successful deployment
4. Click "Redeploy at this version"

### Vercel Rollback
1. Go to Vercel Dashboard
2. Click Deployments
3. Find previous working deployment
4. Click "..."  → "Promote to Production"

## Maintenance Checklist

- [ ] Monitor Render logs weekly
- [ ] Monitor Vercel logs weekly
- [ ] Check database storage (Render)
- [ ] Update dependencies monthly
- [ ] Test new portfolio creation monthly
- [ ] Verify real data still loading
- [ ] Check for security updates

## Performance Optimization (Optional)

### Reduce Cold Starts
- [ ] Upgrade Render from Free to Starter (~$7/month)
- [ ] Keeps backend always running

### Improve Database Performance
- [ ] Upgrade Render PostgreSQL (~$15/month)
- [ ] Provides better resources

### Enhance Frontend
- [ ] Upgrade Vercel Pro (~$20/month)
- [ ] Additional analytics and features

## Monitoring & Alerts

### Set Up Monitoring (Optional)
- [ ] Add Render error email notifications
- [ ] Add Vercel Slack notifications
- [ ] Enable Sentry for error tracking
- [ ] Set up uptime monitoring

## Success Criteria

✅ Deployment successful when:
- [ ] Backend API responds to requests
- [ ] Frontend loads without errors
- [ ] API documentation displays at /docs
- [ ] Portfolio creation works
- [ ] Real metrics display from yfinance
- [ ] Charts render correctly
- [ ] No CORS errors in console
- [ ] No database connection errors
- [ ] Performance is acceptable
- [ ] Users can access at public URLs

## Final Notes

- **Cost:** $0/month (free tiers)
- **Auto-Sleep:** Backend sleeps after 15 min inactivity (free tier)
- **Cold Start:** First request may take 30-50 seconds
- **Uptime:** ~99% available
- **Scaling:** Can upgrade anytime if needed

## URLs to Bookmark

```
Render Dashboard:        https://dashboard.render.com
Vercel Dashboard:        https://vercel.com/dashboard
GitHub Repository:       https://github.com/Manvendra00766/rautrex
Deployed API:           https://rautrex-api.onrender.com
Deployed Frontend:      https://rautrex.vercel.app
API Docs:              https://rautrex-api.onrender.com/docs
Dashboard:             https://rautrex.vercel.app/dashboard
```

---

**Status:** Ready to deploy! 🚀
