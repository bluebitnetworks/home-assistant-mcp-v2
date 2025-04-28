# Deploying Home Assistant MCP to Railway

This guide explains how to deploy your Home Assistant Model Context Protocol (MCP) backend to Railway and connect it to your Vercel frontend.

## Prerequisites

- A Railway account (https://railway.app/)
- Your Home Assistant MCP codebase (this repository)
- A Vercel account with your frontend deployed

## Deployment Steps

### 1. Prepare Your Repository

Make sure your repository includes:
- `requirements.txt` - Lists all Python dependencies
- `Procfile` - Tells Railway how to run your application
- `.env.example` - Template for environment variables

### 2. Deploy to Railway

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click "New Project" > "Deploy from GitHub repo"
3. Select your repository
4. Configure the environment variables (see below)
5. Deploy the project

### 3. Configure Environment Variables

In the Railway dashboard, add these environment variables:

- `HA_URL` - Your Home Assistant URL (e.g., http://your-home-assistant.local:8123)
- `HA_TOKEN` - Your long-lived access token from Home Assistant
- `HA_VERIFY_SSL` - Set to "true" or "false" depending on your setup
- `API_KEY` - Create a secure API key for your frontend to use
- `PORT` - Railway will set this automatically
- `CORS_ORIGINS` - Add your Vercel frontend URL (e.g., https://your-app.vercel.app)

### 4. Connect Your Vercel Frontend

1. In your Vercel project settings, add these environment variables:
   - `NEXT_PUBLIC_MCP_API_URL` - Your Railway app URL (e.g., https://your-app.railway.app)
   - `NEXT_PUBLIC_MCP_API_KEY` - The same API_KEY you set in Railway

2. Update your frontend code to use these environment variables when making API calls.

### 5. API Endpoints

Your MCP API will have these endpoints available:
- `/api/entities` - Control and view Home Assistant entities
- `/api/dashboards` - Create and validate dashboards
- `/api/automations` - Manage automations
- `/api/config` - Test and validate configurations

## Troubleshooting

- **Context Deadline Exceeded**: This usually means your API request is timing out. Check your Home Assistant connection.
- **404 Not Found**: Ensure your API endpoints are correct and your Railway app is running.
- **401 Unauthorized**: Check that your API key is correctly set in both Railway and Vercel.

## Security Notes

- Never commit your `.env` file with real credentials
- Use HTTPS for all connections
- Consider restricting CORS to only your frontend domain in production
