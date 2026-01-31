# Environment Setup Guide

This guide explains how to configure environment variables for the Marketing Agent platform.

## Quick Start

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Generate a secure secret key:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. Add your API keys (see [Required Keys](#required-keys) below)

4. Start the application:
   ```bash
   cd backend && uvicorn app.main:app --reload
   ```

---

## Required vs Optional Keys

### Required Keys

These keys are **required** for the platform to function:

| Key | Purpose | Where to Get It |
|-----|---------|-----------------|
| `SECRET_KEY` | JWT authentication & session security | Generate locally (see below) |
| `OPENROUTER_API_KEY` | Primary LLM access (Claude, GPT-4, etc.) | [OpenRouter](https://openrouter.ai/keys) |

### Required for Specific Features

| Key | Feature | Where to Get It |
|-----|---------|-----------------|
| `PERPLEXITY_API_KEY` | Research & web search | [Perplexity](https://perplexity.ai/settings/api) |
| `FIRECRAWL_API_KEY` | Brand onboarding (website scraping) | [Firecrawl](https://firecrawl.dev/app/api-keys) |
| `AWS_*` keys | File uploads & asset storage | [AWS IAM Console](https://console.aws.amazon.com/iam/) |
| `SEGMIND_API_KEY` | AI image generation | [Segmind](https://www.segmind.com/api-keys) |
| `ELEVENLABS_API_KEY` | AI voice generation | [ElevenLabs](https://elevenlabs.io/app/settings/api-keys) |
| `OPENAI_API_KEY` | Audio transcription (Whisper) | [OpenAI](https://platform.openai.com/api-keys) |
| `XAI_API_KEY` | Video analysis | [xAI Console](https://console.x.ai/) |

### Optional Enterprise Keys

| Key | Feature | Where to Get It |
|-----|---------|-----------------|
| `SALESFORCE_*` | Salesforce CRM integration | [Salesforce Setup](https://login.salesforce.com/) |
| `HUBSPOT_*` | HubSpot CRM integration | [HubSpot Developers](https://developers.hubspot.com/) |
| `DYNAMICS_*` | Microsoft Dynamics integration | [Azure Portal](https://portal.azure.com/) |
| `SNOWFLAKE_*` | Snowflake data warehouse | [Snowflake](https://app.snowflake.com/) |
| `BIGQUERY_*` | Google BigQuery | [Google Cloud Console](https://console.cloud.google.com/) |
| `SEGMENT_*` | Segment CDP | [Segment](https://app.segment.com/) |
| `MPARTICLE_*` | mParticle CDP | [mParticle](https://app.mparticle.com/) |
| `CLEARBIT_API_KEY` | Company/contact enrichment | [Clearbit](https://dashboard.clearbit.com/) |
| `ZEROBOUNCE_API_KEY` | Email verification | [ZeroBounce](https://www.zerobounce.net/) |

---

## Generating Secure Keys

### SECRET_KEY

The `SECRET_KEY` is used for JWT token signing and session security. **Never use the default value in production.**

Generate a secure key:

```bash
# Python (recommended)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL alternative
openssl rand -base64 32

# Node.js alternative
node -e "console.log(require('crypto').randomBytes(32).toString('base64url'))"
```

### ENCRYPTION_KEY

For encrypting sensitive data at rest:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### WEBHOOK_SECRET

For verifying webhook signatures:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Environment-Specific Configuration

### Development

```env
DEBUG=true
ENVIRONMENT=development
DATABASE_URL=sqlite:///local
DATABASE_SSL=false
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Staging

```env
DEBUG=false
ENVIRONMENT=staging
DATABASE_URL=postgresql://user:pass@staging-db:5432/marketing_agent
DATABASE_SSL=true
CORS_ORIGINS=https://staging.your-domain.com
```

### Production

```env
DEBUG=false
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@prod-db:5432/marketing_agent
DATABASE_SSL=true
CORS_ORIGINS=https://your-domain.com
ALLOWED_ORIGINS=https://app.your-domain.com,https://admin.your-domain.com
```

---

## Security Best Practices

### 1. Never Commit Secrets

- ✅ `.env` is in `.gitignore`
- ✅ Use `.env.example` with placeholder values
- ❌ Never commit real API keys or secrets

### 2. Use Strong Secret Keys

- Minimum 32 characters
- Use cryptographically secure random generation
- Different keys for each environment

### 3. Rotate Keys Regularly

- Rotate `SECRET_KEY` every 90 days in production
- Rotate API keys if compromised
- Use key versioning for zero-downtime rotation

### 4. Limit API Key Permissions

- Use least-privilege principle
- Create separate keys for different environments
- Enable IP restrictions where available

### 5. Monitor Key Usage

- Enable logging for API key usage
- Set up alerts for unusual activity
- Review access logs regularly

---

## AWS S3 Setup

### Creating an S3 Bucket

1. Go to [AWS S3 Console](https://s3.console.aws.amazon.com/)
2. Click "Create bucket"
3. Choose a unique bucket name
4. Select your region
5. Configure CORS for your bucket:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
    "AllowedOrigins": ["https://your-domain.com"],
    "ExposeHeaders": ["ETag"]
  }
]
```

### Creating IAM Credentials

1. Go to [IAM Console](https://console.aws.amazon.com/iam/)
2. Create a new user with programmatic access
3. Attach a policy with S3 permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket-name",
        "arn:aws:s3:::your-bucket-name/*"
      ]
    }
  ]
}
```

---

## Convex Setup

1. Create an account at [Convex](https://convex.dev/)
2. Create a new project
3. Get your deployment URL and deploy key from the dashboard
4. Add to your `.env`:

```env
CONVEX_URL=https://your-deployment.convex.cloud
CONVEX_DEPLOY_KEY=prod:xxxxxxxxxxxx
```

---

## Troubleshooting

### "Insecure SECRET_KEY detected"

This error occurs when using a default or weak secret key in production/staging:

```
SECURITY ERROR: Insecure SECRET_KEY detected in production environment.
```

**Solution:** Generate a new secure key and update your environment.

### "Missing required API key"

Check that you've set the required API keys for the features you're using:

```bash
# Verify your .env file
cat .env | grep -E "^(OPENROUTER|PERPLEXITY|FIRECRAWL)_API_KEY"
```

### Database Connection Issues

For PostgreSQL:
- Verify `DATABASE_URL` format: `postgresql://user:password@host:5432/dbname`
- Check `DATABASE_SSL=true` for cloud databases
- Ensure your IP is whitelisted

For SQLite (development):
- Use `DATABASE_URL=sqlite:///local` or leave empty
- Set `DATABASE_SSL=false`

---

## File Reference

| File | Purpose |
|------|---------|
| `.env` | Your actual environment variables (not committed) |
| `.env.example` | Comprehensive template with all keys documented |
| `.env.template` | Quick-start template for common configurations |
| `backend/.env.example` | Backend-specific configuration template |

---

## Support

If you encounter issues with environment configuration:

1. Check this guide for common solutions
2. Verify your API keys are valid and have correct permissions
3. Review the application logs for specific error messages
4. Ensure all required keys are set for the features you're using
