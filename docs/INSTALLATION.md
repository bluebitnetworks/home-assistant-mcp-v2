# Home Assistant MCP Installation Guide

This guide provides detailed instructions for installing and configuring the Home Assistant Multi-agent Contextual Protocol (MCP) for integration with Claude desktop.

## Prerequisites

Before installing Home Assistant MCP, ensure you have the following:

- **Python 3.8+**: Required to run the application
- **Home Assistant instance**: Running and accessible via network
- **Home Assistant Long-Lived Access Token**: For API authentication
- **Claude desktop with MCP capability**: For using the MCP tools

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/hass-mcp.git
cd hass-mcp
```

### 2. Create a Virtual Environment (Recommended)

Creating a virtual environment is recommended to avoid dependency conflicts.

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

If you encounter any dependency issues, try installing individual packages:

```bash
pip install homeassistant-api>=4.0.0 pyyaml>=6.0 requests>=2.28.1 aiohttp>=3.8.3 jinja2>=3.1.2
```

For development or testing, install additional dependencies:

```bash
pip install pytest>=7.2.0 pytest-asyncio>=0.20.0
```

### 4. Configure Home Assistant Connection

1. Create your configuration file by copying the template:

```bash
cp config.yaml.template config.yaml
```

2. Edit the `config.yaml` file with your Home Assistant details:

```yaml
# Home Assistant connection settings
home_assistant:
  url: "http://your-home-assistant-url:8123"  # Your Home Assistant URL
  token: "your_long_lived_access_token"       # Your Long-Lived Access Token
  verify_ssl: true                            # Set to false if using self-signed certificates
```

#### Obtaining a Long-Lived Access Token

1. Log in to your Home Assistant instance
2. Click on your profile (bottom left corner)
3. Scroll down to the "Long-Lived Access Tokens" section
4. Click "Create Token"
5. Give it a meaningful name (e.g., "Home Assistant MCP")
6. Copy the generated token immediately (it won't be shown again)
7. Paste it into your `config.yaml` file

### 5. Configure Additional Settings (Optional)

You can customize additional settings in your `config.yaml` file:

```yaml
# Dashboard generation settings
dashboard:
  default_theme: "default"                # Theme for generated dashboards
  default_icon: "mdi:home-assistant"      # Default icon for cards without icons
  
# Automation settings
automation:
  suggestion_threshold: 3                 # Min occurrences before suggesting automations
  max_suggestions: 5                      # Maximum number of suggestions
  
# Logging settings
logging:
  level: "INFO"                           # DEBUG, INFO, WARNING, ERROR
  file: "hass_mcp.log"                    # Log file location
```

### 6. Verify Installation

Run the main application to verify that it can connect to your Home Assistant instance:

```bash
python src/main.py
```

You should see output indicating successful initialization and connection to Home Assistant.

### 7. Integration with Claude

The MCP schemas for Claude integration will be generated and saved to `mcp_schemas.json` when you run the application. This file contains the schema definitions that Claude will use to interact with Home Assistant.

## Troubleshooting

### Connection Issues

If you're having trouble connecting to Home Assistant:

1. Verify your Home Assistant is running and accessible at the URL specified
2. Check that your access token is valid
3. If using HTTPS with a self-signed certificate, set `verify_ssl: false`
4. Check firewall settings that might block the connection
5. Verify that the Home Assistant API is enabled

### Dependency Issues

If you encounter dependency errors:

1. Make sure you're using Python 3.8 or later
2. Try creating a fresh virtual environment
3. Install dependencies one by one to identify problematic packages
4. Check for version conflicts between packages

### Permission Issues

If you encounter permission errors:

1. Check file permissions for the `config.yaml` and log files
2. Ensure your user has permission to write to the installation directory
3. On Linux/macOS, you may need to use `sudo` for system-wide installation

## Next Steps

Once installation is complete, refer to the [User Guide](USER_GUIDE.md) for detailed instructions on using Home Assistant MCP with Claude.

For specific usage scenarios, see the [Examples](EXAMPLES.md) documentation.
