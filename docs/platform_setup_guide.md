# Platform Setup Guide: TikTok, YouTube & Instagram

This guide walks you through creating accounts and configuring API access for all three publishing platforms used by the Mootoshi pipeline. Follow each section in order.

**Time estimate**: Plan for 2-4 hours total, spread across multiple days (some steps require waiting for approvals).

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Create a Dedicated Email](#2-create-a-dedicated-email)
3. [Platform 1: TikTok](#3-platform-1-tiktok)
4. [Platform 2: YouTube](#4-platform-2-youtube)
5. [Platform 3: Instagram](#5-platform-3-instagram)
6. [Configure Your .env File](#6-configure-your-env-file)
7. [Enable Platforms in Config](#7-enable-platforms-in-config)
8. [Test Your Setup](#8-test-your-setup)
9. [Troubleshooting](#9-troubleshooting)
10. [Platform Comparison Table](#10-platform-comparison-table)

---

## 1. Prerequisites

Before you begin, make sure you have:

- [ ] A phone number that can receive SMS verification codes
- [ ] A computer with a web browser (Chrome recommended)
- [ ] Your project's `.env` file ready to edit (located at the project root)
- [ ] About 30 minutes of uninterrupted time per platform

**Important**: You do NOT need to decide your brand name yet. You can change display names on all platforms later. For now, you can use a temporary name like "MyProject" or similar.

---

## 2. Create a Dedicated Email

It is strongly recommended to create a separate email for this project rather than using your personal email. This keeps everything organized and secure.

### Steps:

1. Go to https://accounts.google.com/signup
2. Click **"Create account"** > **"For my personal use"**
3. Fill in:
   - **First name**: Your name (or project name)
   - **Last name**: Your last name (or "Studio" / "Media")
   - **Username**: Something like `yourprojectname.media@gmail.com`
   - **Password**: A strong, unique password
4. Add your phone number for verification
5. Complete the setup

**Why Gmail specifically?** You already have a Google account (for YouTube), but a dedicated one keeps project credentials separate. Plus, this same Google account will be used for the YouTube/Google Cloud setup later.

> **Write this down**: Save your new email and password somewhere safe. You'll use this email for ALL three platform signups below.

---

## 3. Platform 1: TikTok

### 3A. Create a TikTok Account

1. Go to https://www.tiktok.com/signup on your computer
2. Click **"Use email"**
3. Enter your **dedicated project email** from Step 2
4. Set a password
5. Verify your email by entering the code sent to your inbox
6. Complete the profile setup (you can skip most optional fields)

> **Note**: You do NOT need a TikTok Business Account for API access. A regular account works. However, a Business Account gives you analytics — you can switch later in Settings > Account > "Switch to Business Account".

### 3B. Create a TikTok Developer Account

1. Go to https://developers.tiktok.com/
2. Click **"Log in"** in the top right
3. Log in with the **same TikTok account** you just created
4. You'll be prompted to agree to the TikTok Developer Terms of Service
5. Click **"Agree"** to complete developer registration

### 3C. Create an App

1. After logging in to the developer portal, click **"Manage apps"** in the top navigation
2. Click **"Create app"** (or "Connect an app")
3. Fill in the required fields:
   - **App name**: Your project name (e.g., "Mootoshi Publisher" — can change later)
   - **App description**: Describe what your app does. Example:
     > "Automated video publishing tool for our animated series. Uploads short-form video content (30-45 second animated episodes) to TikTok on a daily schedule."
   - **App icon**: Upload any square image (at least 100x100px) — can update later
   - **Category**: Select **"Entertainment"** or **"Content & Publishing"**
   - **Platform**: Select **"Web"**
   - **Website URL**: If you have one, enter it. Otherwise enter your GitHub repo URL
   - **Terms of Service URL**: Use the URL to your hosted Terms of Service (see `docs/legal/terms_of_service.md` in the project — you'll need to host this at a public URL)
   - **Privacy Policy URL**: Use the URL to your hosted Privacy Policy (see `docs/legal/privacy_policy.md` in the project — you'll need to host this at a public URL)
4. Click **"Submit"** / **"Create"**

### 3D. Add the Content Posting API Product

1. In your app dashboard, find the **"Products"** or **"Add products"** section
2. Look for **"Content Posting API"** and click **"Add"** or **"Enable"**
3. Within the Content Posting API settings, enable **"Direct Post"** — this allows your app to post videos directly to user accounts
4. Under **Scopes**, request the following:
   - `video.publish` — **Required**: Allows uploading and posting videos
   - `user.info.basic` — **Required**: Read basic user profile info

### 3E. Get Your Client Key and Client Secret

1. After creating your app, go to your app's **"Settings"** or **"Configuration"** page
2. You'll see:
   - **Client Key** — a long alphanumeric string (e.g., `aw1234abcdef567890`)
   - **Client Secret** — another long string (keep this SECRET, never share it)
3. Copy both values — you'll need them for your `.env` file later

### 3F. Submit for Review (Audit)

**This is critical**: Until your app passes TikTok's audit, all videos posted through the API will be **private** (only visible to the poster). You must pass the audit for videos to be publicly visible.

1. In your app dashboard, look for **"Submit for review"** or **"Request audit"**
2. You'll need to provide:
   - A **video demo** showing your app in action (screen recording is fine)
   - A **written description** of how you use the API
   - Proof that your app follows TikTok's Terms of Service
3. Submit and wait for review

**What to expect**:
- TikTok does NOT give a specific timeline for approval
- It can take anywhere from **a few days to several weeks**
- You may receive follow-up questions or requests for more information
- Check your developer portal and email regularly for updates

**While you wait**: You can still test the integration! Videos will just be posted as private (SELF_ONLY visibility). Unaudited apps can have up to **5 users post within a 24-hour window**.

### 3G. OAuth 2.0 Flow (Getting Access Tokens)

Once your app is approved (or for testing before approval):

1. **Authorization URL**: Your app redirects users to:
   ```
   https://www.tiktok.com/v2/auth/authorize/
     ?client_key=YOUR_CLIENT_KEY
     &scope=user.info.basic,video.publish
     &response_type=code
     &redirect_uri=YOUR_REDIRECT_URI
     &state=RANDOM_STRING
   ```

2. **User Consent**: The user (you, for your own account) sees a consent screen and clicks "Authorize"

3. **Authorization Code**: TikTok redirects back to your app with a temporary code in the URL

4. **Token Exchange**: Your app exchanges this code for an access token by calling:
   ```
   POST https://open.tiktokapis.com/v2/oauth/token/
   ```
   With your `client_key`, `client_secret`, `code`, and `redirect_uri`

5. **Result**: You receive:
   - `access_token` — used for API calls (expires periodically)
   - `refresh_token` — used to get new access tokens without re-authorizing
   - `open_id` — unique identifier for the authorized user

6. Copy the `access_token` value — this goes in your `.env` file as `TIKTOK_ACCESS_TOKEN`

> **Important**: Access tokens expire. Your app will need to use the refresh token to get new ones. The pipeline code will need to handle this (covered in Phase 7 implementation).

### TikTok Summary

| Item | Value |
|---|---|
| Developer Portal | https://developers.tiktok.com/ |
| Account type needed | Regular TikTok account (Business optional) |
| Required scopes | `video.publish`, `user.info.basic` |
| Audit required? | Yes — videos are private until audit passes |
| Unaudited limits | 5 users per 24 hours, private videos only |
| Cost | Free |
| Approval timeline | Days to weeks (no guarantee) |

---

## 4. Platform 2: YouTube

You already have a Google account. You'll use it to set up Google Cloud and the YouTube Data API.

### 4A. Create a YouTube Channel

If you don't already have a YouTube channel for this project:

1. Go to https://www.youtube.com/ and sign in with your Google account
2. Click your profile icon in the top right
3. Click **"Create a channel"**
4. Enter a channel name (your project name — can change later)
5. Click **"Create channel"**

> **Note**: You can create a "Brand Account" channel that is separate from your personal Google identity. This is recommended so your project has its own identity. To do this: go to YouTube Settings > "Add or manage your channel(s)" > "Create a new channel".

### 4B. Create a Google Cloud Project

1. Go to https://console.cloud.google.com/
2. Sign in with your Google account
3. You'll see the Google Cloud Console dashboard
4. Click the **project dropdown** at the top of the page (it might say "Select a project" or show your existing project)
5. Click **"New Project"** in the popup
6. Fill in:
   - **Project name**: e.g., "Mootoshi Publisher" or "My Video Pipeline"
   - **Organization**: Leave as "No organization" if you don't have one
   - **Location**: Leave as default
7. Click **"Create"**
8. Wait a few seconds, then select your new project from the project dropdown

### 4C. Enable the YouTube Data API v3

1. In the Google Cloud Console, click the hamburger menu (three horizontal lines, top left)
2. Go to **"APIs & Services"** > **"Library"**
3. In the search bar, type **"YouTube Data API v3"**
4. Click on **"YouTube Data API v3"** in the results
5. Click the blue **"Enable"** button
6. Wait for it to enable (takes a few seconds)

### 4D. Set Up the OAuth Consent Screen

Before you can create credentials, you must configure what users see when they authorize your app.

1. In the left sidebar, go to **"APIs & Services"** > **"OAuth consent screen"**
2. Select **"External"** as the user type (unless you have a Google Workspace organization)
3. Click **"Create"**
4. Fill in the consent screen form:
   - **App name**: Your project name
   - **User support email**: Your project email
   - **App logo**: Optional (can add later)
   - **App domain**: Leave blank if you don't have a website
   - **Developer contact email**: Your project email
5. Click **"Save and Continue"**

6. **Scopes page**: Click **"Add or Remove Scopes"**
   - Search for and add: `https://www.googleapis.com/auth/youtube.upload`
   - This allows your app to upload videos to YouTube
   - Click **"Update"** then **"Save and Continue"**

7. **Test users page**: Click **"Add Users"**
   - Enter your Google account email (the one that owns the YouTube channel)
   - Click **"Add"** then **"Save and Continue"**

8. Review the summary and click **"Back to Dashboard"**

> **Important about Test Mode**: Your app starts in "Testing" mode. This means:
> - Only the test users you added can authorize the app
> - Authorization tokens expire after **7 days** (you'll need to re-authorize)
> - You can have up to **100 test users**
> - This is fine for your use case (you're the only user)
> - To remove the 7-day limit, you'd need to "Publish" the app and go through Google's verification — but this is NOT necessary for personal use

### 4E. Create OAuth 2.0 Credentials

1. In the left sidebar, go to **"APIs & Services"** > **"Credentials"**
2. Click **"+ Create Credentials"** at the top
3. Select **"OAuth client ID"**
4. For **Application type**, select **"Web application"** (required for the OAuth Playground in the next step)
5. **Name**: e.g., "Mootoshi Pipeline"
6. **Authorized JavaScript origins** — leave this section empty (do not add anything)
7. **Authorized redirect URIs** — click **"+ Add URI"** and enter:
   `https://developers.google.com/oauthplayground`
8. Click **"Create"**
9. A popup appears showing:
   - **Client ID** — a long string ending in `.apps.googleusercontent.com`
   - **Client Secret** — another string
10. Copy the Client ID and Client Secret — you'll need these for your `.env` file

### 4F. Get Your Refresh Token

This is the trickiest part. You need to authorize your app once to get a long-lived refresh token.

**Option A: Using the OAuth Playground (Easiest)**

1. Go to https://developers.google.com/oauthplayground/
2. Click the **gear icon** (top right) to open settings
3. Check **"Use your own OAuth credentials"**
4. Enter your **Client ID** and **Client Secret** from Step 4E
5. Close the settings panel
6. In the left panel, find **"YouTube Data API v3"** and expand it
7. Check the box next to `https://www.googleapis.com/auth/youtube.upload`
8. Click the blue **"Authorize APIs"** button
9. Sign in with your Google account (the one with the YouTube channel)
10. You'll see a consent screen — click **"Continue"** (it may warn about the app not being verified — click "Advanced" > "Go to [app name]" to proceed)
11. After authorization, you'll be redirected back to the Playground
12. Click **"Exchange authorization code for tokens"**
13. You'll see:
    - **Access token** — expires in ~1 hour
    - **Refresh token** — this is what you need! It does NOT expire (unless you revoke it)
14. Copy the **Refresh token** — this goes in your `.env` file as `GOOGLE_REFRESH_TOKEN`

**Option B: Using a Python script**

If the Playground doesn't work, you can use the `google-auth-oauthlib` library:

```python
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    'client_secret_XXXX.json',  # The file you downloaded in Step 4E
    scopes=['https://www.googleapis.com/auth/youtube.upload']
)
credentials = flow.run_local_server(port=8080)

print(f"Access Token: {credentials.token}")
print(f"Refresh Token: {credentials.refresh_token}")
```

Run this script, authorize in the browser that opens, and copy the refresh token.

### 4G. Quota Information

- **Default quota**: 10,000 units per day (resets at midnight Pacific Time)
- **Video upload cost**: 1,600 units per upload (videos.insert)
- **This means**: You can upload approximately **6 videos per day** with the default quota
- **For Mootoshi**: You only upload 1 video per day, so the default quota is MORE than enough
- **Cost**: Completely **free** — no charges for API usage
- **Quota increase**: Available for free by request through Google Cloud Console if ever needed

### YouTube Summary

| Item | Value |
|---|---|
| Google Cloud Console | https://console.cloud.google.com/ |
| Account type needed | Regular Google account with a YouTube channel |
| Required scope | `youtube.upload` |
| Approval needed? | No (app stays in "Testing" mode for personal use) |
| Daily quota | 10,000 units (~6 uploads/day) |
| Token expiry | Access token: 1 hour. Refresh token: indefinite. **In Testing mode**: re-authorize every 7 days |
| Cost | Free |

---

## 5. Platform 3: Instagram

Instagram API access requires a Meta (Facebook) developer account and an Instagram Business or Creator account linked to a Facebook Page. This is the most complex setup of the three.

### 5A. Create a Facebook Account

If you don't already have a Facebook account:

1. Go to https://www.facebook.com/
2. Click **"Create new account"**
3. Enter:
   - Your name
   - Your **dedicated project email** from Step 2
   - A password
   - Date of birth
   - Gender
4. Click **"Sign Up"**
5. Verify your email

### 5B. Create a Facebook Page

Your Instagram Business account needs to be linked to a Facebook Page. This is required by Meta.

1. Log in to Facebook
2. Click the **"+"** icon or go to https://www.facebook.com/pages/create
3. Select **"Business or Brand"**
4. Fill in:
   - **Page name**: Your project name (can change later)
   - **Category**: Select **"Entertainment"** or **"Media/News Company"**
   - **Description**: Brief description of your animated series
5. Click **"Create Page"**
6. You can skip adding a profile photo and cover photo for now

### 5C. Create an Instagram Account

1. Download the Instagram app on your phone (or go to https://www.instagram.com/)
2. Click **"Sign Up"**
3. Use your **dedicated project email** from Step 2
4. Choose a username (your project name — can change later)
5. Set a password
6. Complete your profile setup

### 5D. Convert to a Business or Creator Account

You MUST have a Business or Creator account for API access. Either type works for publishing Reels.

**Recommended: Creator Account** (better music access for animated content)

1. Open Instagram app > go to your profile
2. Tap the **hamburger menu** (three lines, top right)
3. Tap **"Settings and privacy"**
4. Scroll down and tap **"Account type and tools"**
5. Tap **"Switch to professional account"**
6. Choose **"Creator"** (recommended) or **"Business"**
7. Select a category: **"Digital Creator"** or **"Artist"**
8. Tap **"Done"**

### 5E. Link Instagram to Your Facebook Page

1. On Instagram, go to **Settings** > **"Account type and tools"** > **"Linked accounts"** (or **"Sharing to other apps"**)
2. Select **"Facebook"**
3. Log in to Facebook if prompted
4. Select the **Facebook Page** you created in Step 5B
5. Confirm the connection

> **Verify the link worked**: Go to your Facebook Page > Settings > Instagram. You should see your Instagram account connected.

### 5F. Create a Meta Developer Account

1. Go to https://developers.facebook.com/
2. Click **"Get Started"** or **"Log In"**
3. Log in with your **Facebook account**
4. Accept the Meta Platform Terms of Service
5. Verify your account (may require phone number or email verification)
6. Complete the developer registration

### 5G. Create a Meta App

1. On the Meta for Developers dashboard, click **"Create App"**
2. Select **"Other"** as the use case (or "Business" if available)
3. Select app type: **"Business"**
4. Fill in:
   - **App name**: e.g., "Mootoshi Publisher"
   - **App contact email**: Your project email
   - **Business Account**: Select your Facebook Page's business account, or click "Create new" if prompted
5. Click **"Create App"**

### 5H. Add Instagram Graph API to Your App

1. In your app dashboard, scroll down to **"Add Products"**
2. Find **"Instagram Graph API"** (or "Instagram" in the product list)
3. Click **"Set Up"**
4. This adds the Instagram Graph API product to your app

### 5I. Configure Permissions

1. In your app settings, go to **"App Review"** > **"Permissions and Features"**
2. Request these permissions:
   - `instagram_basic` — Read profile info and media
   - `instagram_content_publish` — **Required**: Publish content (Reels, feed posts, stories)
   - `pages_show_list` — Access list of Pages you manage
   - `pages_read_engagement` — Read Page engagement data

   > **Note on newer apps**: If you see permissions like `instagram_business_basic` and `instagram_business_content_publish` instead, use those — Meta has been migrating to new permission names.

3. For some permissions, you may need to provide a **screen recording** showing how your app uses the permission and submit for **App Review** by Meta

### 5J. Get Your Access Token

**Step 1: Get a Short-Lived Token**

1. In the Meta developer dashboard, go to your app
2. Go to **"Tools"** > **"Graph API Explorer"**
3. In the **"Meta App"** dropdown, select your app
4. Click **"Generate Access Token"**
5. Select the permissions listed above
6. Click **"Generate Access Token"**
7. Authorize with your Facebook/Instagram account
8. You'll receive a short-lived token (expires in ~1 hour)

**Step 2: Exchange for a Long-Lived Token**

Short-lived tokens are useless for automation. You need a long-lived token (60 days).

1. Open a browser tab and go to this URL (replace the placeholders):

   ```
   https://graph.facebook.com/v21.0/oauth/access_token
     ?grant_type=fb_exchange_token
     &client_id=YOUR_META_APP_ID
     &client_secret=YOUR_META_APP_SECRET
     &fb_exchange_token=YOUR_SHORT_LIVED_TOKEN
   ```

2. The response will contain your long-lived access token
3. Copy this token — it goes in your `.env` file as `INSTAGRAM_ACCESS_TOKEN`

> **Important**: Long-lived tokens expire after **60 days**. You'll need to refresh them before they expire. The pipeline will need a token refresh mechanism (covered in Phase 7 implementation).

**Step 3: Get Your Instagram Business Account ID**

1. Using the Graph API Explorer (or a browser), call:
   ```
   GET /me/accounts?access_token=YOUR_LONG_LIVED_TOKEN
   ```
2. Find your Facebook Page in the results and note its `id`
3. Then call:
   ```
   GET /PAGE_ID?fields=instagram_business_account&access_token=YOUR_LONG_LIVED_TOKEN
   ```
4. The response contains your `instagram_business_account.id`
5. Copy this ID — it goes in your `.env` file as `INSTAGRAM_BUSINESS_ACCOUNT_ID`

### 5K. App Review (For Production)

Your Meta app starts in **Development Mode**. In this mode:
- Only users with a role in the app (Admin, Developer, Tester) can use it
- **This is fine for your use case** since you're the only one publishing
- You can publish Reels to your own account without going through full App Review

To go live for other users (not needed for Mootoshi):
- Submit for App Review in the developer dashboard
- Provide a screencast demo and detailed descriptions
- Timeline: typically 1-5 business days

### Instagram Summary

| Item | Value |
|---|---|
| Developer Portal | https://developers.facebook.com/ |
| Account types needed | Facebook account + Facebook Page + Instagram Business/Creator account |
| Required permissions | `instagram_content_publish`, `instagram_basic`, `pages_show_list` |
| App Review needed? | No (Development Mode is fine for personal use) |
| Token expiry | Short-lived: 1 hour. Long-lived: 60 days (must refresh) |
| Reels length limit | Up to 90 seconds (some accounts: 60 seconds) |
| Cost | Free |

---

## 6. Configure Your .env File

Now that you have credentials from all three platforms, update your project's `.env` file.

Open the file at: `<project_root>/.env`

Add/update these values with the credentials you collected:

```bash
# TikTok
TIKTOK_CLIENT_KEY=<your Client Key from Step 3E>
TIKTOK_CLIENT_SECRET=<your Client Secret from Step 3E>
TIKTOK_ACCESS_TOKEN=<your access token from Step 3G>

# YouTube / Google
GOOGLE_CLIENT_ID=<your Client ID from Step 4E>
GOOGLE_CLIENT_SECRET=<your Client Secret from Step 4E>
GOOGLE_REFRESH_TOKEN=<your Refresh Token from Step 4F>

# Instagram / Meta
META_APP_ID=<your Meta App ID from Step 5G - found in app dashboard>
META_APP_SECRET=<your Meta App Secret from Step 5G - found in app Settings > Basic>
INSTAGRAM_ACCESS_TOKEN=<your long-lived token from Step 5J>
INSTAGRAM_BUSINESS_ACCOUNT_ID=<your IG Business Account ID from Step 5J>
```

> **Security warning**: NEVER commit your `.env` file to Git. Make sure `.env` is listed in your `.gitignore` file (it already should be).

---

## 7. Enable Platforms in Config

Once your `.env` is configured, enable each platform in the config file.

Open: `config/platforms.yaml`

Change `enabled: false` to `enabled: true` for each platform you've set up:

```yaml
platforms:
  tiktok:
    enabled: true    # <-- change from false to true
    # ... rest stays the same

  youtube:
    enabled: true    # <-- change from false to true
    # ... rest stays the same

  instagram:
    enabled: true    # <-- change from false to true
    # ... rest stays the same
```

> **Tip**: You can enable platforms one at a time. Start with the one you're most comfortable with, test it, then enable the next.

---

## 8. Test Your Setup

After configuring everything, verify each platform works:

### Quick Smoke Test

Run the pipeline's built-in platform check (when implemented):

```bash
python -m src.publisher.test_connection
```

### Manual Verification Checklist

- [ ] **TikTok**: Can you log in to https://developers.tiktok.com/ and see your app?
- [ ] **TikTok**: Does your app show "Content Posting API" as an added product?
- [ ] **YouTube**: Can you visit https://console.cloud.google.com/ and see your project?
- [ ] **YouTube**: Is the "YouTube Data API v3" shown as enabled in APIs & Services?
- [ ] **YouTube**: Did you get a refresh token from the OAuth Playground?
- [ ] **Instagram**: Can you log in to https://developers.facebook.com/ and see your app?
- [ ] **Instagram**: Is your Instagram account a Business or Creator account?
- [ ] **Instagram**: Is your Instagram linked to your Facebook Page?
- [ ] **Instagram**: Did you get a long-lived access token?
- [ ] **.env file**: Are all credential fields filled in (no empty values)?
- [ ] **platforms.yaml**: Are all three platforms set to `enabled: true`?

---

## 9. Troubleshooting

### TikTok

| Problem | Solution |
|---|---|
| "App not found" | Make sure you're logged in with the correct TikTok account on the developer portal |
| Videos post as private | Your app hasn't passed the audit yet. Submit for audit in Step 3F |
| "Invalid redirect URI" | The redirect URI in your OAuth request must exactly match what's configured in your app settings |
| Access token expired | Use the refresh token to get a new access token (automated in pipeline) |

### YouTube

| Problem | Solution |
|---|---|
| "Access Not Configured" | Make sure YouTube Data API v3 is enabled in your Google Cloud project (Step 4C) |
| "The user has not granted the app" | Re-authorize: go through the OAuth Playground flow again (Step 4F) |
| "Quota exceeded" | You've uploaded too many videos today. Wait until midnight Pacific Time. Default limit is ~6 uploads/day |
| Consent screen shows "unverified app" warning | This is normal in Testing mode. Click "Advanced" > "Go to [app name]" to proceed |
| Token expires every 7 days | This is normal in Testing mode. Re-run the OAuth flow to get a new refresh token. To avoid this, you'd need to "Publish" the app (requires Google verification) |

### Instagram

| Problem | Solution |
|---|---|
| "Invalid OAuth access token" | Your token expired. Exchange for a new long-lived token (repeat Step 5J) |
| "The user has not authorized application" | Make sure you have the correct permissions and your IG account is a Business/Creator account |
| Can't find Instagram Business Account ID | Make sure your IG account is linked to a Facebook Page first (Step 5E) |
| "Application does not have permission" | Request the `instagram_content_publish` permission in App Review (Step 5I) |
| "Media type not supported" | Your video must be MP4 format, H.264 codec, max 90 seconds, 9:16 aspect ratio |

### General

| Problem | Solution |
|---|---|
| `.env` changes not taking effect | Restart the pipeline / bot after changing `.env` values |
| "Platform not enabled" error | Check `config/platforms.yaml` — make sure `enabled: true` is set |

---

## 10. Platform Comparison Table

| Feature | TikTok | YouTube | Instagram |
|---|---|---|---|
| **Developer Portal** | developers.tiktok.com | console.cloud.google.com | developers.facebook.com |
| **Account Type** | Regular TikTok | Google + YouTube channel | Facebook + FB Page + IG Business/Creator |
| **Auth Method** | OAuth 2.0 | OAuth 2.0 | OAuth 2.0 (via Meta) |
| **Required Scopes** | `video.publish` | `youtube.upload` | `instagram_content_publish` |
| **Audit/Review** | Required for public posts | Not needed (Testing mode) | Not needed (Dev mode) |
| **Token Expiry** | Varies (use refresh token) | 7 days in Testing mode | 60 days (long-lived) |
| **Daily Limits** | 5 users unaudited | ~6 uploads (10K quota) | 25 content publishes/day |
| **Video Format** | MP4, H.264 | MP4 (up to 256GB) | MP4, H.264, max 90s |
| **Aspect Ratio** | 9:16 | 9:16 for Shorts | 9:16 for Reels |
| **Cost** | Free | Free | Free |
| **Setup Difficulty** | Medium | Medium | Hard (most steps) |
| **Approval Time** | Days-weeks | Instant | Instant (Dev mode) |

---

## Token Refresh Schedule

Since tokens expire, here's what to plan for:

| Platform | What Expires | When | What To Do |
|---|---|---|---|
| TikTok | Access Token | Periodically | Pipeline uses refresh token automatically |
| YouTube | OAuth consent | Every 7 days (Testing mode) | Re-run OAuth Playground flow |
| Instagram | Long-lived Token | Every 60 days | Exchange for new token before expiry |

> **Future improvement**: Phase 7 of the pipeline implementation will add automatic token refresh for all platforms, so you won't need to do this manually.

---

## What's Next?

After completing this guide:

1. All three `.env` credentials are filled in
2. All three platforms are enabled in `config/platforms.yaml`
3. The pipeline can attempt to publish to each platform

The actual publishing code (Phase 7/8 of the PRD) still needs to be implemented — the current code has skeleton/stub functions that check for credentials but don't actually upload yet. This guide ensures that when the publishing code is built, all the accounts and credentials are ready to go.

---

*Guide created for the Mootoshi project. Last updated: February 2026.*

Sources used for this guide:
- [TikTok Content Posting API Docs](https://developers.tiktok.com/doc/content-posting-api-get-started)
- [TikTok Developer Portal](https://developers.tiktok.com/)
- [TikTok API Guide 2026](https://getlate.dev/blog/tiktok-api)
- [YouTube Data API - Uploading a Video](https://developers.google.com/youtube/v3/guides/uploading_a_video)
- [YouTube OAuth 2.0 Guide](https://developers.google.com/youtube/v3/guides/authentication)
- [YouTube Quota Calculator](https://developers.google.com/youtube/v3/determine_quota_cost)
- [Instagram Graph API Developer Guide 2026](https://elfsight.com/blog/instagram-graph-api-complete-developer-guide-for-2026/)
- [Instagram Reels API Guide](https://www.getphyllo.com/post/a-complete-guide-to-the-instagram-reels-api)
- [Google OAuth Consent Screen Docs](https://developers.google.com/workspace/guides/configure-oauth-consent)
