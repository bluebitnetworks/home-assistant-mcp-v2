"""
Claude Integration Tools for Home Assistant MCP.

This module defines the tools that Claude can use to interact with Home Assistant.
"""

import logging
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from src.connection.api import HomeAssistantAPI
from src.yaml_generator.dashboard import DashboardGenerator
from src.testing.validator import ConfigValidator
from src.automation.generator import AutomationGenerator

logger = logging.getLogger(__name__)

# Global instances for tool access
api_client = None
dashboard_generator = None
config_validator = None
automation_generator = None

def register_tools(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Register MCP tools for Claude to use with Home Assistant.
    
    Args:
        config (Dict[str, Any]): Configuration dictionary
        
    Returns:
        Dict[str, Any]: Tool schema definitions
    """
    global api_client, dashboard_generator, config_validator, automation_generator
    
    # Initialize API client
    api_client = HomeAssistantAPI(config)
    
    # Initialize other components
    dashboard_generator = DashboardGenerator(config)
    config_validator = ConfigValidator(config)
    automation_generator = AutomationGenerator(config)
    
    # Define tool schemas for Claude
    tools = {
        "get_entities": {
            "description": "Get a list of all entities from Home Assistant",
            "parameters": {},
            "function": get_entities
        },
        "get_entity_state": {
            "description": "Get the state of a specific entity from Home Assistant",
            "parameters": {
                "entity_id": {
                    "type": "string",
                    "description": "The entity ID to get the state for"
                }
            },
            "function": get_entity_state
        },
        "control_entity": {
            "description": "Control a Home Assistant entity",
            "parameters": {
                "entity_id": {
                    "type": "string",
                    "description": "The entity ID to control"
                },
                "action": {
                    "type": "string",
                    "description": "The action to perform (e.g., 'turn_on', 'turn_off', 'set_temperature')"
                },
                "parameters": {
                    "type": "object",
                    "description": "Optional parameters for the action"
                }
            },
            "function": control_entity
        },
        "create_dashboard": {
            "description": "Create a Home Assistant dashboard",
            "parameters": {
                "title": {
                    "type": "string",
                    "description": "The title of the dashboard"
                },
                "views": {
                    "type": "array",
                    "description": "Views configuration for the dashboard"
                },
                "output_path": {
                    "type": "string",
                    "description": "Optional output path for the dashboard YAML"
                }
            },
            "function": create_dashboard
        },
        "validate_yaml": {
            "description": "Validate Home Assistant YAML configuration",
            "parameters": {
                "yaml_content": {
                    "type": "string",
                    "description": "YAML content to validate"
                },
                "config_type": {
                    "type": "string",
                    "description": "Type of configuration (dashboard, automation)"
                }
            },
            "function": validate_yaml
        },
        "suggest_automations": {
            "description": "Suggest automations based on entity history",
            "parameters": {
                "history_data": {
                    "type": "array",
                    "description": "Entity history data for analysis"
                }
            },
            "function": suggest_automations
        },
        "generate_automation": {
            "description": "Generate an automation YAML based on a pattern",
            "parameters": {
                "pattern": {
                    "type": "object",
                    "description": "Automation pattern to generate YAML for"
                },
                "output_path": {
                    "type": "string",
                    "description": "Optional output path for the automation YAML"
                }
            },
            "function": generate_automation
        }
    }
    
    logger.info(f"Registered {len(tools)} Claude integration tools")
    return tools

# Tool implementations

def get_entities() -> Dict[str, Any]:
    """
    Get a list of all entities from Home Assistant.
    
    Returns:
        Dict[str, Any]: Response with entity list
    """
    try:
        entities = api_client.get_entities_sync()
        return {
            "success": True,
            "entities": entities
        }
    except Exception as e:
        logger.error(f"Failed to get entities: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def get_entity_state(entity_id: str) -> Dict[str, Any]:
    """
    Get the state of a specific entity from Home Assistant.
    
    Args:
        entity_id (str): The entity ID to get the state for
        
    Returns:
        Dict[str, Any]: Response with entity state
    """
    try:
        entities = api_client.get_entities_sync()
        entity = next((e for e in entities if e.get('entity_id') == entity_id), None)
        
        if not entity:
            return {
                "success": False,
                "error": f"Entity {entity_id} not found"
            }
        
        return {
            "success": True,
            "entity": entity
        }
    except Exception as e:
        logger.error(f"Failed to get entity state: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def control_entity(entity_id: str, action: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Control a Home Assistant entity.
    
    Args:
        entity_id (str): The entity ID to control
        action (str): The action to perform
        parameters (Optional[Dict[str, Any]]): Optional parameters for the action
        
    Returns:
        Dict[str, Any]: Response with result
    """
    try:
        if parameters is None:
            parameters = {}
        
        # Determine domain and service
        domain = entity_id.split('.')[0]
        service = f"{domain}.{action}"
        
        # Add entity_id to service data
        service_data = {
            "entity_id": entity_id,
            **parameters
        }
        
        result = api_client.call_service_sync(domain, action, service_data)
        
        return {
            "success": result,
            "message": f"Successfully called {service}" if result else f"Failed to call {service}"
        }
    except Exception as e:
        logger.error(f"Failed to control entity: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def create_dashboard(title: str, views: List[Dict[str, Any]], 
                    output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a Home Assistant dashboard.
    
    Args:
        title (str): The title of the dashboard
        views (List[Dict[str, Any]]): Views configuration for the dashboard
        output_path (Optional[str]): Optional output path for the dashboard YAML
        
    Returns:
        Dict[str, Any]: Response with dashboard YAML
    """
    try:
        yaml_content = dashboard_generator.create_lovelace_dashboard(title, views, output_path)
        
        # Validate the generated YAML
        is_valid, error = config_validator.validate_dashboard_config(yaml_content)
        
        if not is_valid:
            return {
                "success": False,
                "error": error,
                "yaml": yaml_content
            }
        
        return {
            "success": True,
            "yaml": yaml_content,
            "file_path": output_path if output_path else None
        }
    except Exception as e:
        logger.error(f"Failed to create dashboard: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def validate_yaml(yaml_content: str, config_type: str) -> Dict[str, Any]:
    """
    Validate Home Assistant YAML configuration.
    
    Args:
        yaml_content (str): YAML content to validate
        config_type (str): Type of configuration (dashboard, automation)
        
    Returns:
        Dict[str, Any]: Response with validation result
    """
    try:
        if config_type.lower() == 'dashboard':
            is_valid, error = config_validator.validate_dashboard_config(yaml_content)
        elif config_type.lower() == 'automation':
            is_valid, error = config_validator.validate_automation_config(yaml_content)
        else:
            return {
                "success": False,
                "error": f"Unsupported configuration type: {config_type}"
            }
        
        return {
            "success": is_valid,
            "error": error if not is_valid else None
        }
    except Exception as e:
        logger.error(f"Failed to validate YAML: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def suggest_automations(history_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Suggest automations based on entity history.
    
    Args:
        history_data (List[Dict[str, Any]]): Entity history data for analysis
        
    Returns:
        Dict[str, Any]: Response with automation suggestions
    """
    try:
        patterns = automation_generator.analyze_entity_usage(history_data)
        
        return {
            "success": True,
            "suggestions": patterns
        }
    except Exception as e:
        logger.error(f"Failed to suggest automations: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def generate_automation(pattern: Dict[str, Any], 
                       output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate an automation YAML based on a pattern.
    
    Args:
        pattern (Dict[str, Any]): Automation pattern to generate YAML for
        output_path (Optional[str]): Optional output path for the automation YAML
        
    Returns:
        Dict[str, Any]: Response with automation YAML
    """
    try:
        yaml_content = automation_generator.generate_automation_yaml(pattern)
        
        # Validate the generated YAML
        is_valid, error = config_validator.validate_automation_config(yaml_content)
        
        if not is_valid:
            return {
                "success": False,
                "error": error,
                "yaml": yaml_content
            }
        
        # Write to file if output_path is provided
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(yaml_content)
        
        return {
            "success": True,
            "yaml": yaml_content,
            "file_path": output_path if output_path else None
        }
    except Exception as e:
        logger.error(f"Failed to generate automation: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }