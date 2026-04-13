# Deploy Rautrex to Render (Backend) & Vercel (Frontend)

## Quick Summary

```
Frontend (Next.js):  Deploy to Vercel
Backend (FastAPI):  Deploy to Render
Database:          PostgreSQL on Render
Real Data:         Yahoo Finance API
```

---

## Part 1: Deploy Backend to Render

### Step 1: Create Render Account
1. Go to https://render.com
2. Sign up with GitHub account
3. Connect your GitHub repository

### Step 2: Create PostgreSQL Database

**In Render Dashboard:**
1. Click "New +" → "PostgreSQL"
2. Configure:
   - Name: `rautrex-db`
   - Database: `rautrex`
   - User: `rautrex_user`
   - Region: Choose closest to you
   - Plan: **Free tier** (available)
3. Click "Create Database"
4. Wait for provisioning (~2 minutes)
5. Copy the database URL (you'll need this)

**Database URL format:**
```
postgresql://rautrex_user:PASSWORD@host:5432/rautrex
```

### Step 3: Create Web Service for Backend

**In Render Dashboard:**
1. Click "New +" → "Web Service"
2. Connect GitHub repository:
   - Find `rautrex` repository
   - Click "Connect"

**Configure Web Service:**

**Name:**
```
rautrex-api
```

**Region:**
```
Choose closest to you (same as database)
```

**Branch:**
```
main
```

**Build Command:**
```
pip install -r requirements.txt
```

**Start Command:**
```
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Root Directory:**
```
(leave empty - root of repo)
```

**Plan:**
```
Free
```

### Step 4: Add Environment Variables

**In Render Web Service Settings → Environment:**

Add these variables:

```
DATABASE_URL=postgresql://rautrex_user:PASSWORD@host:5432/rautrex
```

(Replace PASSWORD and host with your actual database credentials)

```
ENVIRONMENT=production
CORS_ORIGINS=https://rautrex-frontend.vercel.app,https://yourdomain.com
SECRET_KEY=your-secret-key-here-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7
```

**Get SECRET_KEY:** Generate a random string:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 5: Deploy

1. Scroll to bottom
2. Click "Create Web Service"
3. Wait for deployment (2-5 minutes)
4. You'll see a live URL like:
   ```
   https://rautrex-api.onrender.com
   ```

**Test Backend:**
```
https://rautrex-api.onrender.com/docs
```

---

## Part 2: Deploy Frontend to Vercel

### Step 1: Create Vercel Account
1. Go to https://vercel.com
2. Sign up with GitHub account
3. Connect your GitHub repository

### Step 2: Import Project

**In Vercel Dashboard:**
1. Click "New Project"
2. Select `rautrex` repository
3. Click "Import"

**Project Settings:**

**Framework Preset:**
```
Next.js
```

**Root Directory:**
```
./frontend
```

**Node Version:**
```
18.x (or latest)
```

### Step 3: Add Environment Variables

**In Vercel Project Settings → Environment Variables:**

Add:
```
NEXT_PUBLIC_API_URL=https://rautrex-api.onrender.com
```

(Replace with your actual Render backend URL)

**Save these variables for:**
- Production
- Preview
- Development

### Step 4: Deploy

1. Click "Deploy"
2. Wait for build (1-3 minutes)
3. You'll get a URL like:
   ```
   https://rautrex.vercel.app
   ```

**Access Frontend:**
```
https://rautrex.vercel.app/dashboard
```

---

## Step 5: Update Backend CORS

Now that you have frontend URL, update backend environment variable:

**In Render Dashboard → rautrex-api settings:**

Update:
```
CORS_ORIGINS=https://rautrex.vercel.app,https://rautrex-frontend.vercel.app
```

(Add your actual Vercel URL)

Click "Save" and Render will redeploy.

---

## Verify Deployment

### Backend Health Check
```bash
curl https://rautrex-api.onrender.com/docs
```

Should show Swagger API documentation.

### Frontend Health Check
```bash
curl https://rautrex.vercel.app
```

Should return HTML for the dashboard.

### Test API Connection
1. Open https://rautrex.vercel.app/dashboard
2. Create a portfolio
3. Should fetch real data from Yahoo Finance
4. Should display metrics on dashboard

---

## Production Checklist

- [x] Database connected and migrated
- [x] Backend deployed to Render
- [x] Frontend deployed to Vercel
- [x] CORS configured correctly
- [x] Environment variables set
- [x] API health check passing
- [x] Frontend can access backend
- [x] Real data displaying
- [x] Portfolio creation working
- [x] Dashboard metrics showing

---

## Troubleshooting

### Backend not starting
**Error:** `ModuleNotFoundError`

**Solution:**
1. Check `requirements.txt` has all dependencies
2. Check build command runs properly
3. Check Python version is 3.9+

**In Render logs:**
```
Render → rautrex-api → Logs
```

### Frontend can't reach backend
**Error:** CORS error or API not responding

**Solutions:**
1. Check `NEXT_PUBLIC_API_URL` is correct
2. Check `CORS_ORIGINS` in backend includes frontend URL
3. Test backend directly: `https://rautrex-api.onrender.com/docs`

### Database connection failing
**Error:** `could not connect to database`

**Solutions:**
1. Verify `DATABASE_URL` is correct
2. Check database is running in Render
3. Verify credentials are correct
4. Make sure database region matches

### Real data not loading
**Error:** Portfolio metrics return empty

**Solutions:**
1. Check yfinance is in requirements.txt
2. Verify backend logs for errors
3. Test with simple ticker (AAPL)
4. Check internet connection on Render

---

## Environment Variables Reference

### Backend (.env or Render settings)
```
DATABASE_URL=postgresql://user:pass@host:5432/db
ENVIRONMENT=production
CORS_ORIGINS=https://rautrex.vercel.app
SECRET_KEY=your-secret-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Frontend (.env.local or Vercel settings)
```
NEXT_PUBLIC_API_URL=https://rautrex-api.onrender.com
```

---

## Cost Estimation

### Render
- **PostgreSQL**: Free tier ($0/month)
- **Web Service**: Free tier with auto-sleep ($0/month)
- **Total**: $0/month (with auto-sleep)

### Vercel
- **Frontend**: Free tier ($0/month)
- **Total**: $0/month

**Total Cost: $0/month** (completely free!)

---

## Important Notes

### Free Tier Limitations

**Render (Web Service):**
- Auto-sleeps after 15 min of inactivity
- First request takes 30-50 seconds (cold start)
- Limited resources
- No uptime SLA

**Render (PostgreSQL):**
- Free tier limited to small datasets
- No backups
- Limited storage

**Vercel:**
- Auto-deploys on git push
- No backend needed (static hosting)
- Limited to 1 GB per function

### For Production Scale

**Upgrade options:**
1. **Render Web Service**: Pay-as-you-go (~$7/month for always-on)
2. **Render PostgreSQL**: Standard tier (~$15/month)
3. **Vercel Pro**: $20/month (optional, for more features)

---

## Redeploy After Code Changes

### Automatic
1. Push code to GitHub: `git push origin main`
2. Vercel automatically redeploys frontend
3. Render automatically redeploys backend
4. New deployment live in 2-5 minutes

### Manual Redeploy

**On Render:**
1. Dashboard → rautrex-api → Manual Deploy

**On Vercel:**
1. Dashboard → Deployments → Redeploy

---

## Monitor Deployments

### Render Dashboard
- Check logs: Render → Service → Logs
- Check status: Dashboard shows build status
- View metrics: Real-time CPU/memory usage

### Vercel Dashboard
- Check logs: Deployments → Build logs
- Check status: Real-time build progress
- View analytics: Real-time requests/errors

---

## Quick Reference URLs

After deployment, save these URLs:

```
API Base:       https://rautrex-api.onrender.com
API Docs:       https://rautrex-api.onrender.com/docs
Frontend:       https://rautrex.vercel.app
Dashboard:      https://rautrex.vercel.app/dashboard
Database:       (Managed by Render - not public)
```

---

## Next Steps

1. ✅ Deploy backend to Render
2. ✅ Deploy frontend to Vercel
3. Test the deployed system
4. Share URL with users
5. Monitor logs for issues
6. Scale up if needed

---

## Support

**Render Support:**
- https://render.com/docs
- https://render.com/help

**Vercel Support:**
- https://vercel.com/docs
- https://vercel.com/support

**Your GitHub:**
- https://github.com/Manvendra00766/rautrex
