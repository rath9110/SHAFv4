# eBay API Integration Setup Guide

## Overview
This guide will help you integrate eBay's Finding API into the Second-Hand Finder extension.

## Prerequisites
- eBay Developer Program account (registration takes 1-2 days for approval)
- Python 3.11+
- Chrome browser for extension testing

## Step 1: Get eBay API Credentials

1. **Register for eBay Developer Program**
   - Visit: https://developer.ebay.com/
   - Create a free developer account
   - Wait for account approval (typically 1-2 days)

2. **Create Application Keys**
   - Log into Developer Portal
   - Navigate to "My Account" → "Application Keys"
   - Create a new application
   - Copy your **App ID (Client ID)** and **Cert ID (Client Secret)**

3. **Select API Environment**
   - Use **Production** environment for live eBay data
   - Use **Sandbox** for testing (optional)

## Step 2: Configure Environment Variables

1. Navigate to `backend/` directory
2. Create a `.env` file (if it doesn't exist)
3. Add your eBay credentials:

```env
# eBay API Configuration
EBAY_APP_ID=your_app_id_here
EBAY_CERT_ID=your_cert_id_here
EBAY_SITE_ID=71
```

> **Note:** `EBAY_SITE_ID=71` targets eBay Sweden. Change to `0` for US, `3` for UK, etc.

## Step 3: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This will install the `ebaysdk` library needed for eBay API calls.

## Step 4: Test Configuration

Start the backend server:
```bash
uvicorn fetching_service:app --reload
```

Visit health endpoint:
```
http://localhost:8000/health
```

Expected response should include:
```json
{
  "status": "healthy",
  "ebay_configured": true,
  ...
}
```

## Step 5: Next Steps

After completing these initial preparations:
1. The backend code will be updated to integrate eBay Finding API
2. Product searches will include eBay results alongside Tradera, Blocket, and Vinted
3. Extension popup will display eBay listings

## API Rate Limits

eBay Finding API has the following limits:
- **Free tier:** 5,000 calls/day
- **Rate:** ~3 calls/second

Consider implementing caching if you expect high usage.

## Troubleshooting

**Issue:** `ebay_configured: false`
- Verify `.env` file exists in `backend/` directory
- Check that `EBAY_APP_ID` and `EBAY_CERT_ID` are set
- Ensure no extra spaces in credential values

**Issue:** API calls fail with authentication error
- Verify credentials are from eBay Production environment (not Sandbox)
- Ensure App ID and Cert ID are copied correctly
- Check that your developer account is approved

## Resources

- [eBay Developer Portal](https://developer.ebay.com/)
- [eBay Finding API Documentation](https://developer.ebay.com/devzone/finding/Concepts/FindingAPIGuide.html)
- [ebaysdk-python GitHub](https://github.com/timotheus/ebaysdk-python)
