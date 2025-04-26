"""
Home Assistant MCP (Multimodal Contextual Protocol) Interface.

This module provides the Multimodal Contextual Protocol interface for Claude
to interact with Home Assistant. It defines all the MCP schemas, response formats,
and integration points necessary for Claude to access Home Assistant functionality.
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional, Union

from src.connection.api import HomeAssistantAPI
from src.yaml_generator.dashboard import DashboardGenerator
from src.testing.validator import ConfigValidator
from src.automation.manager import AutomationManager
from src.automation.generator import AutomationGenerator
from src.automation.suggestion_engine import SuggestionEngine
from src.automation.test_runner import AutomationTestRunner
from src.claude_integration.tools import register_tools
from src.claude_integration.automation_tools import AutomationTools

logger = logging.getLogger(__name__)

class HomeAssistantMCP:
    """
    Home Assistant MCP (Multimodal Contextual Protocol) Interface.
    
    This class provides the main interface for Claude to interact with
    Home Assistant using the MCP protocol.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Home Assistant MCP interface.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
        """
        self.config = config
        self.api = HomeAssistantAPI(config)
        self.dashboard_generator = DashboardGenerator(config)
        self.config_validator = ConfigValidator(config)
        self.automation_tools = AutomationTools(config)
        
        # Register all tools
        self.tools = register_tools(config)
        
        logger.info("Home Assistant MCP interface initialized")
    
    def get_schemas(self) -> Dict[str, Any]:
        """
        Get the MCP tool schemas for Claude.
        
        Returns:
            Dict[str, Any]: MCP tool schemas
        """
        mcp_schemas = {
            "home_assistant_entity_control": {
                "description": "Control Home Assistant entities and view their states",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["get_entities", "get_entity_state", "control_entity"],
                            "description": "Action to perform on Home Assistant entities"
                        },
                        "entity_id": {
                            "type": "string",
                            "description": "Entity ID for get_entity_state and control_entity actions"
                        },
                        "control_action": {
                            "type": "string",
                            "description": "Control action for control_entity (e.g., 'turn_on', 'turn_off', 'set_temperature')"
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Optional parameters for the control action"
                        }
                    },
                    "required": ["action"]
                }
            },
            "home_assistant_dashboard": {
                "description": "Create and validate Home Assistant dashboards",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["create_dashboard", "validate_dashboard"],
                            "description": "Action to perform with dashboards"
                        },
                        "title": {
                            "type": "string",
                            "description": "Dashboard title for create_dashboard"
                        },
                        "views": {
                            "type": "array",
                            "description": "Dashboard views configuration for create_dashboard"
                        },
                        "yaml_content": {
                            "type": "string",
                            "description": "YAML content to validate for validate_dashboard"
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Optional output path for the dashboard YAML"
                        }
                    },
                    "required": ["action"]
                }
            },
            "home_assistant_automation": {
                "description": "Manage Home Assistant automations, including suggestions, creation, and testing",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["get_automations", "get_automation_details", "create_automation", 
                                    "update_automation", "delete_automation", "test_automation", 
                                    "suggest_automations", "get_entity_automations"],
                            "description": "Action to perform with automations"
                        },
                        "automation_id": {
                            "type": "string",
                            "description": "Automation ID for specific automation actions"
                        },
                        "entity_id": {
                            "type": "string",
                            "description": "Entity ID for get_entity_automations"
                        },
                        "automation_yaml": {
                            "type": "string",
                            "description": "Automation YAML content for create/update/test"
                        },
                        "days": {
                            "type": "integer",
                            "description": "Number of days of history to analyze for suggestions"
                        }
                    },
                    "required": ["action"]
                }
            },
            "home_assistant_config": {
                "description": "Test and validate Home Assistant configurations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["validate_config", "test_config", "check_config_dependencies"],
                            "description": "Action to perform with configurations"
                        },
                        "config_type": {
                            "type": "string",
                            "enum": ["dashboard", "automation", "script", "sensor"],
                            "description": "Type of configuration to validate/test"
                        },
                        "config_yaml": {
                            "type": "string",
                            "description": "Configuration YAML content to validate/test"
                        }
                    },
                    "required": ["action", "config_type"]
                }
            }
        }
        
        return mcp_schemas
    
    def process_request(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an MCP request from Claude.
        
        Args:
            tool_name (str): The name of the MCP tool
            parameters (Dict[str, Any]): Tool parameters
            
        Returns:
            Dict[str, Any]: Response to Claude
        """
        try:
            if tool_name == "home_assistant_entity_control":
                return self._process_entity_control(parameters)
            
            elif tool_name == "home_assistant_dashboard":
                return self._process_dashboard(parameters)
            
            elif tool_name == "home_assistant_automation":
                return self._process_automation(parameters)
            
            elif tool_name == "home_assistant_config":
                return self._process_config(parameters)
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool name: {tool_name}"
                }
                
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _process_entity_control(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Home Assistant entity control requests.
        
        Args:
            parameters (Dict[str, Any]): Request parameters
            
        Returns:
            Dict[str, Any]: Response
        """
        action = parameters.get("action")
        
        if action == "get_entities":
            return self.tools["get_entities"]["function"]()
            
        elif action == "get_entity_state":
            entity_id = parameters.get("entity_id")
            if not entity_id:
                return {"success": False, "error": "entity_id is required"}
            
            return self.tools["get_entity_state"]["function"](entity_id)
            
        elif action == "control_entity":
            entity_id = parameters.get("entity_id")
            control_action = parameters.get("control_action")
            action_params = parameters.get("parameters", {})
            
            if not entity_id:
                return {"success": False, "error": "entity_id is required"}
            if not control_action:
                return {"success": False, "error": "control_action is required"}
                
            return self.tools["control_entity"]["function"](entity_id, control_action, action_params)
            
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
    
    def _process_dashboard(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Home Assistant dashboard requests.
        
        Args:
            parameters (Dict[str, Any]): Request parameters
            
        Returns:
            Dict[str, Any]: Response
        """
        action = parameters.get("action")
        
        if action == "create_dashboard":
            title = parameters.get("title")
            views = parameters.get("views")
            output_path = parameters.get("output_path")
            
            if not title:
                return {"success": False, "error": "title is required"}
            if not views:
                return {"success": False, "error": "views is required"}
                
            return self.tools["create_dashboard"]["function"](title, views, output_path)
            
        elif action == "validate_dashboard":
            yaml_content = parameters.get("yaml_content")
            
            if not yaml_content:
                return {"success": False, "error": "yaml_content is required"}
                
            return self.tools["validate_yaml"]["function"](yaml_content, "dashboard")
            
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
    
    def _process_automation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Home Assistant automation requests.
        
        Args:
            parameters (Dict[str, Any]): Request parameters
            
        Returns:
            Dict[str, Any]: Response
        """
        action = parameters.get("action")
        
        if action == "get_automations":
            import asyncio
            return asyncio.run(self.automation_tools.get_automations())
            
        elif action == "get_automation_details":
            automation_id = parameters.get("automation_id")
            if not automation_id:
                return {"success": False, "error": "automation_id is required"}
                
            import asyncio
            return asyncio.run(self.automation_tools.get_automation_details(automation_id))
            
        elif action == "create_automation":
            automation_yaml = parameters.get("automation_yaml")
            if not automation_yaml:
                return {"success": False, "error": "automation_yaml is required"}
                
            import asyncio
            return asyncio.run(self.automation_tools.create_automation(automation_yaml))
            
        elif action == "update_automation":
            automation_id = parameters.get("automation_id")
            automation_yaml = parameters.get("automation_yaml")
            
            if not automation_id:
                return {"success": False, "error": "automation_id is required"}
            if not automation_yaml:
                return {"success": False, "error": "automation_yaml is required"}
                
            import asyncio
            return asyncio.run(self.automation_tools.update_automation(automation_id, automation_yaml))
            
        elif action == "delete_automation":
            automation_id = parameters.get("automation_id")
            if not automation_id:
                return {"success": False, "error": "automation_id is required"}
                
            import asyncio
            return asyncio.run(self.automation_tools.delete_automation(automation_id))
            
        elif action == "test_automation":
            automation_yaml = parameters.get("automation_yaml")
            if not automation_yaml:
                return {"success": False, "error": "automation_yaml is required"}
                
            import asyncio
            return asyncio.run(self.automation_tools.test_automation(automation_yaml))
            
        elif action == "suggest_automations":
            days = parameters.get("days", 7)
            
            import asyncio
            return asyncio.run(self.automation_tools.suggest_automations(days))
            
        elif action == "get_entity_automations":
            entity_id = parameters.get("entity_id")
            if not entity_id:
                return {"success": False, "error": "entity_id is required"}
                
            import asyncio
            return asyncio.run(self.automation_tools.get_entity_automations(entity_id))
            
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
    
    def _process_config(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Home Assistant configuration requests.
        
        Args:
            parameters (Dict[str, Any]): Request parameters
            
        Returns:
            Dict[str, Any]: Response
        """
        action = parameters.get("action")
        config_type = parameters.get("config_type")
        config_yaml = parameters.get("config_yaml")
        
        if not config_type:
            return {"success": False, "error": "config_type is required"}
        
        if action == "validate_config":
            if not config_yaml:
                return {"success": False, "error": "config_yaml is required"}
                
            return self.tools["validate_yaml"]["function"](config_yaml, config_type)
            
        elif action == "test_config":
            if not config_yaml:
                return {"success": False, "error": "config_yaml is required"}
                
            # Use appropriate test method based on config_type
            if config_type == "automation":
                import asyncio
                return asyncio.run(self.automation_tools.test_runner.test_automation_config(config_yaml))
            else:
                return {"success": False, "error": f"Testing for {config_type} is not implemented"}
                
        elif action == "check_config_dependencies":
            if not config_yaml:
                return {"success": False, "error": "config_yaml is required"}
                
            # Check dependencies based on config_type
            if config_type == "automation":
                import asyncio
                return asyncio.run(self.automation_tools.test_runner.check_automation_dependencies(config_yaml))
            else:
                return {"success": False, "error": f"Dependency checking for {config_type} is not implemented"}
                
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
