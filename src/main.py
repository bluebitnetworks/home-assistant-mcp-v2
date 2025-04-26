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
from pathlib import Path

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
    Load configuration from the config.yaml file.
    
    Args:
        config_path (str, optional): Path to the config file. Defaults to None,
                                     which will use the default config.yaml.
    
    Returns:
        dict: Configuration dictionary
    """
    if config_path is None:
        config_path = root_dir / "config.yaml"
    
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {config_path}")
        logger.info("Please create a config.yaml file from the template")
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

def main():
    """
    Main entry point for the Home Assistant MCP.
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
    
    return mcp

if __name__ == "__main__":
    main()