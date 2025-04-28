#!/usr/bin/env python3
"""
Home Assistant MCP - Main entry point.

This module serves as the entry point for the Home Assistant MCP,
providing the main interfaces for Claude to interact with Home Assistant.
"""

import os
import sys
import logging
import json
import yaml
import time
import signal
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add root directory to path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

def load_config(config_path=None):
    """
    Load configuration from the config.yaml file or environment variables.
    
    Args:
        config_path (str, optional): Path to the config file. Defaults to None,
                                     which will use the default config.yaml.
    
    Returns:
        dict: Configuration dictionary
    """
    # Initialize default config structure
    config = {
        "home_assistant": {
            "url": os.getenv("HA_URL"),
            "token": os.getenv("HA_TOKEN"),
            "verify_ssl": os.getenv("HA_VERIFY_SSL", "true").lower() == "true"
        }
    }
    
    # If all required env vars are set, use them
    if config["home_assistant"]["url"] and config["home_assistant"]["token"]:
        logger.info("Configuration loaded from environment variables")
        return config
        
    # Otherwise try to load from config file
    if config_path is None:
        config_path = root_dir / "config.yaml"
    
    try:
        with open(config_path, 'r') as file:
            file_config = yaml.safe_load(file)
            # Merge with any env vars that might be set
            if "home_assistant" in file_config:
                if not config["home_assistant"]["url"]:
                    config["home_assistant"]["url"] = file_config["home_assistant"].get("url")
                if not config["home_assistant"]["token"]:
                    config["home_assistant"]["token"] = file_config["home_assistant"].get("token")
                if "HA_VERIFY_SSL" not in os.environ and "verify_ssl" in file_config["home_assistant"]:
                    config["home_assistant"]["verify_ssl"] = file_config["home_assistant"]["verify_ssl"]
            
        logger.info(f"Configuration loaded from {config_path} and environment variables")
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {config_path} and environment variables are incomplete")
        logger.info("Please create a config.yaml file from the template or set environment variables")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Error parsing configuration file: {e}")
        sys.exit(1)

def save_mcp_schemas(schemas, output_path=None):
    """
    Save MCP schemas to a file for Claude integration.
    
    Args:
        schemas (dict): MCP schemas
        output_path (str, optional): Path to save schemas. Defaults to None,
                                     which will use the default mcp_schemas.json.
    """
    if output_path is None:
        output_path = root_dir / "mcp_schemas.json"
    
    try:
        with open(output_path, 'w') as file:
            json.dump(schemas, file, indent=2)
        logger.info(f"MCP schemas saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save MCP schemas: {e}")

# Global variable to track shutdown signal
shutdown_requested = False

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    global shutdown_requested
    logger.info(f"Received signal {sig}, initiating shutdown...")
    shutdown_requested = True

async def keep_alive(mcp):
    """
    Keep the MCP service running and handle periodic tasks
    """
    global shutdown_requested
    
    logger.info("MCP service is now running continuously...")
    
    # Validate Home Assistant connection periodically
    while not shutdown_requested:
        try:
            # Check Home Assistant connection every 60 seconds
            is_valid, error = await mcp.api.validate_connection()
            if not is_valid:
                logger.warning(f"Home Assistant connection issue: {error}")
            else:
                logger.debug("Home Assistant connection validated")
                
            # Wait before checking again, but allow for interruption
            for _ in range(60):
                if shutdown_requested:
                    break
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in keep_alive loop: {e}")
            await asyncio.sleep(10)  # Wait a bit before retrying
    
    logger.info("Exiting keep_alive loop")
    # Cleanup
    await mcp.api.close()

async def async_main():
    """
    Async version of the main entry point
    """
    logger.info("Starting Home Assistant MCP")
    
    # Load configuration
    config = load_config()
    
    # Import modules here to avoid circular imports
    from src.claude_integration.mcp import HomeAssistantMCP
    
    # Initialize the MCP interface
    mcp = HomeAssistantMCP(config)
    
    # Get and save MCP schemas
    schemas = mcp.get_schemas()
    save_mcp_schemas(schemas)
    
    logger.info("Home Assistant MCP initialized and ready")
    logger.info("Use the following tools in Claude:")
    for tool_name in schemas.keys():
        logger.info(f"- {tool_name}")
    
    # Keep the service running
    await keep_alive(mcp)

def main():
    """
    Main entry point for the Home Assistant MCP.
    """
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the async main function
    asyncio.run(async_main())

if __name__ == "__main__":
    main()