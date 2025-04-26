"""
Home Assistant Automation Management Tools for Claude Integration.

This module provides the functions required for Claude to interact with
the Home Assistant Automation Management module.
"""

import logging
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set

from src.connection.api import HomeAssistantAPI
from src.automation.manager import AutomationManager
from src.automation.generator import AutomationGenerator
from src.automation.pattern_discovery import PatternDiscovery
from src.automation.suggestion_engine import SuggestionEngine
from src.automation.test_runner import AutomationTestRunner

logger = logging.getLogger(__name__)

class AutomationTools:
    """Class providing automation tools for Claude integration."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the automation tools.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
        """
        self.config = config
        self.api = HomeAssistantAPI(config)
        self.automation_manager = AutomationManager(config, self.api)
        self.automation_generator = AutomationGenerator(config)
        self.pattern_discovery = PatternDiscovery(config)
        self.suggestion_engine = SuggestionEngine(config)
        self.test_runner = AutomationTestRunner(config, self.api)
    
    async def get_automations(self) -> Dict[str, Any]:
        """
        Get all automations from Home Assistant.
        
        Returns:
            Dict[str, Any]: Dictionary with automations data
        """
        try:
            # Load automations from Home Assistant
            automations = await self.automation_manager.load_automations(refresh=True)
            
            # Format automations for display
            formatted_automations = {}
            for auto_id, auto in automations.items():
                formatted_automations[auto_id] = self.automation_manager.format_automation_for_display(auto)
            
            return {
                'success': True,
                'automations': formatted_automations,
                'count': len(formatted_automations)
            }
            
        except Exception as e:
            logger.error(f"Error getting automations: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_automation_details(self, automation_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific automation.
        
        Args:
            automation_id (str): Automation ID
            
        Returns:
            Dict[str, Any]: Automation details
        """
        try:
            # Load automation
            automations = await self.automation_manager.load_automations()
            
            if automation_id not in automations:
                return {
                    'success': False,
                    'error': f"Automation '{automation_id}' not found"
                }
            
            automation = automations[automation_id]
            
            # Get raw YAML
            raw_yaml = await self.automation_manager.get_raw_automation_yaml(automation_id)
            
            return {
                'success': True,
                'automation': automation,
                'yaml': raw_yaml
            }
            
        except Exception as e:
            logger.error(f"Error getting automation details: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_entity_automations(self, entity_id: str) -> Dict[str, Any]:
        """
        Get automations that reference a specific entity.
        
        Args:
            entity_id (str): Entity ID
            
        Returns:
            Dict[str, Any]: Automations related to the entity
        """
        try:
            # Get automations for the entity
            automations = await self.automation_manager.get_automation_by_entity(entity_id)
            
            # Format automations for display
            formatted_automations = []
            for auto in automations:
                auto_id = auto.get('id', '')
                formatted = self.automation_manager.format_automation_for_display(auto)
                formatted_automations.append(formatted)
            
            return {
                'success': True,
                'entity_id': entity_id,
                'automations': formatted_automations,
                'count': len(formatted_automations)
            }
            
        except Exception as e:
            logger.error(f"Error getting entity automations: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def create_automation(self, automation_yaml: str) -> Dict[str, Any]:
        """
        Create a new automation in Home Assistant.
        
        Args:
            automation_yaml (str): Automation YAML content
            
        Returns:
            Dict[str, Any]: Creation results
        """
        try:
            # Validate the automation YAML
            validation_results = await self.test_runner.validate_automation_yaml(automation_yaml)
            
            if not validation_results['valid']:
                return {
                    'success': False,
                    'validation': validation_results,
                    'error': "Automation validation failed"
                }
            
            # Parse the automation
            automation = yaml.safe_load(automation_yaml)
            
            # Handle single automation or list
            if isinstance(automation, list):
                if not automation:
                    return {
                        'success': False,
                        'error': "Empty automation list"
                    }
                automation = automation[0]
            
            # Save the automation
            success = await self.automation_manager.save_automation(automation)
            
            if not success:
                return {
                    'success': False,
                    'error': "Failed to save automation"
                }
            
            return {
                'success': True,
                'automation_id': automation.get('id', ''),
                'message': "Automation created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating automation: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def update_automation(self, automation_id: str, automation_yaml: str) -> Dict[str, Any]:
        """
        Update an existing automation in Home Assistant.
        
        Args:
            automation_id (str): Automation ID to update
            automation_yaml (str): Updated automation YAML content
            
        Returns:
            Dict[str, Any]: Update results
        """
        try:
            # Validate the automation YAML
            validation_results = await self.test_runner.validate_automation_yaml(automation_yaml)
            
            if not validation_results['valid']:
                return {
                    'success': False,
                    'validation': validation_results,
                    'error': "Automation validation failed"
                }
            
            # Parse the automation
            automation = yaml.safe_load(automation_yaml)
            
            # Handle single automation or list
            if isinstance(automation, list):
                if not automation:
                    return {
                        'success': False,
                        'error': "Empty automation list"
                    }
                automation = automation[0]
            
            # Ensure the ID matches
            automation['id'] = automation_id
            
            # Save the automation
            success = await self.automation_manager.save_automation(automation)
            
            if not success:
                return {
                    'success': False,
                    'error': "Failed to update automation"
                }
            
            return {
                'success': True,
                'automation_id': automation_id,
                'message': "Automation updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error updating automation: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def delete_automation(self, automation_id: str) -> Dict[str, Any]:
        """
        Delete an automation from Home Assistant.
        
        Args:
            automation_id (str): Automation ID to delete
            
        Returns:
            Dict[str, Any]: Deletion results
        """
        try:
            # Delete the automation
            success = await self.automation_manager.delete_automation(automation_id)
            
            if not success:
                return {
                    'success': False,
                    'error': f"Failed to delete automation '{automation_id}'"
                }
            
            return {
                'success': True,
                'automation_id': automation_id,
                'message': "Automation deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error deleting automation: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def enable_disable_automation(self, automation_id: str, enable: bool) -> Dict[str, Any]:
        """
        Enable or disable an automation in Home Assistant.
        
        Args:
            automation_id (str): Automation ID
            enable (bool): True to enable, False to disable
            
        Returns:
            Dict[str, Any]: Operation results
        """
        try:
            # Enable/disable the automation
            success = await self.automation_manager.enable_disable_automation(automation_id, enable)
            
            if not success:
                return {
                    'success': False,
                    'error': f"Failed to {'enable' if enable else 'disable'} automation '{automation_id}'"
                }
            
            return {
                'success': True,
                'automation_id': automation_id,
                'status': 'enabled' if enable else 'disabled',
                'message': f"Automation {'enabled' if enable else 'disabled'} successfully"
            }
            
        except Exception as e:
            logger.error(f"Error {'enabling' if enable else 'disabling'} automation: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def trigger_automation(self, automation_id: str) -> Dict[str, Any]:
        """
        Manually trigger an automation in Home Assistant.
        
        Args:
            automation_id (str): Automation ID to trigger
            
        Returns:
            Dict[str, Any]: Trigger results
        """
        try:
            # Trigger the automation
            success = await self.automation_manager.trigger_automation(automation_id)
            
            if not success:
                return {
                    'success': False,
                    'error': f"Failed to trigger automation '{automation_id}'"
                }
            
            return {
                'success': True,
                'automation_id': automation_id,
                'message': "Automation triggered successfully"
            }
            
        except Exception as e:
            logger.error(f"Error triggering automation: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def test_automation(self, automation_yaml: str) -> Dict[str, Any]:
        """
        Test an automation configuration without deploying it.
        
        Args:
            automation_yaml (str): Automation YAML content
            
        Returns:
            Dict[str, Any]: Test results
        """
        try:
            # Validate the automation
            validation_results = await self.test_runner.validate_automation_yaml(automation_yaml)
            
            # Run a dry run simulation
            dry_run_results = await self.test_runner.dry_run_automation(automation_yaml)
            
            # Test trigger capability
            trigger_results = await self.test_runner.test_automation_trigger(automation_yaml)
            
            # Validate templates
            template_results = await self.test_runner.validate_automation_templates(automation_yaml)
            
            # Simulate execution
            simulation_results = await self.test_runner.simulate_automation_execution(automation_yaml)
            
            return {
                'success': True,
                'validation': validation_results,
                'dry_run': dry_run_results,
                'trigger': trigger_results,
                'templates': template_results,
                'simulation': simulation_results
            }
            
        except Exception as e:
            logger.error(f"Error testing automation: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def suggest_automations(self, days: int = 7) -> Dict[str, Any]:
        """
        Generate automation suggestions based on entity usage patterns.
        
        Args:
            days (int, optional): Number of days of history to analyze
            
        Returns:
            Dict[str, Any]: Automation suggestions
        """
        try:
            # Get entity history for the specified days
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            # Format timestamps for the API
            start_str = start_time.isoformat()
            end_str = end_time.isoformat()
            
            # Get entity history
            entity_history = {}
            
            # Get all entities
            entities = await self.api.get_states()
            
            # Get history for each entity
            for entity in entities:
                entity_id = entity['entity_id']
                domain = entity_id.split('.')[0]
                
                # Skip uninteresting entities
                if domain in ['automation', 'script', 'scene', 'group', 'persistent_notification']:
                    continue
                
                try:
                    history = await self.api.get_history(entity_id, start_str, end_str)
                    if history:
                        entity_history[entity_id] = history
                except Exception as e:
                    logger.warning(f"Error getting history for {entity_id}: {e}")
            
            # Generate suggestions
            suggestions = await self.suggestion_engine.generate_suggestions(entity_history)
            
            # Group suggestions by category
            categorized = self.suggestion_engine.get_suggestion_categories(suggestions)
            
            return {
                'success': True,
                'suggestions': suggestions,
                'categorized': categorized,
                'count': len(suggestions),
                'analyzed_days': days,
                'analyzed_entities': len(entity_history)
            }
            
        except Exception as e:
            logger.error(f"Error generating automation suggestions: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def generate_automation_from_suggestion(self, suggestion_id: str, suggestions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate an automation from a suggestion.
        
        Args:
            suggestion_id (str): Suggestion ID
            suggestions (List[Dict[str, Any]]): List of available suggestions
            
        Returns:
            Dict[str, Any]: Generated automation
        """
        try:
            # Find the suggestion
            suggestion = None
            for s in suggestions:
                if s.get('id') == suggestion_id:
                    suggestion = s
                    break
            
            if not suggestion:
                return {
                    'success': False,
                    'error': f"Suggestion '{suggestion_id}' not found"
                }
            
            # Get the YAML from the suggestion
            yaml_content = suggestion.get('yaml', '')
            
            if not yaml_content:
                return {
                    'success': False,
                    'error': "No YAML content in suggestion"
                }
            
            # Test the automation
            test_results = await self.test_automation(yaml_content)
            
            return {
                'success': True,
                'suggestion_id': suggestion_id,
                'suggestion': suggestion,
                'yaml': yaml_content,
                'test_results': test_results
            }
            
        except Exception as e:
            logger.error(f"Error generating automation from suggestion: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_entity_based_automation_suggestions(self, entity_id: str) -> Dict[str, Any]:
        """
        Get automation suggestions specific to an entity.
        
        Args:
            entity_id (str): Entity ID
            
        Returns:
            Dict[str, Any]: Entity-specific automation suggestions
        """
        try:
            # Get all suggestions
            suggestions_result = await self.suggest_automations()
            
            if not suggestions_result['success']:
                return suggestions_result
            
            suggestions = suggestions_result['suggestions']
            
            # Filter suggestions for this entity
            entity_suggestions = self.suggestion_engine.get_suggestions_by_entity(suggestions, entity_id)
            
            # Get existing automations for this entity
            existing_automations = await self.automation_manager.get_automation_by_entity(entity_id)
            
            return {
                'success': True,
                'entity_id': entity_id,
                'suggestions': entity_suggestions,
                'existing_automations': existing_automations,
                'count': len(entity_suggestions)
            }
            
        except Exception as e:
            logger.error(f"Error getting entity suggestions: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def create_template_automation(self, template_type: str, entities: List[str], options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create an automation from a template.
        
        Args:
            template_type (str): Type of template (time, state, etc.)
            entities (List[str]): List of entities to include
            options (Dict[str, Any], optional): Additional options
            
        Returns:
            Dict[str, Any]: Generated automation
        """
        try:
            options = options or {}
            
            # Create a pattern based on the template type
            if template_type == 'time':
                time_str = options.get('time', '08:00:00')
                state = options.get('state', 'on')
                
                patterns = []
                for entity_id in entities:
                    pattern = {
                        'type': 'daily',
                        'entity_id': entity_id,
                        'domain': entity_id.split('.')[0],
                        'trigger_time': time_str.split(':')[0],
                        'action_state': state,
                        'confidence': 1.0,
                        'occurrences': 1
                    }
                    patterns.append(pattern)
                
                # Generate YAML for each pattern
                yaml_contents = []
                for pattern in patterns:
                    yaml_content = self.suggestion_engine._generate_daily_automation_yaml(pattern)
                    yaml_contents.append(yaml_content)
                
            elif template_type == 'state':
                trigger_entity = options.get('trigger_entity', '')
                trigger_state = options.get('trigger_state', '')
                action_state = options.get('action_state', 'on')
                
                if not trigger_entity or not trigger_state:
                    return {
                        'success': False,
                        'error': "Trigger entity and state are required for state template"
                    }
                
                patterns = []
                for entity_id in entities:
                    pattern = {
                        'type': 'conditional',
                        'entity_id': entity_id,
                        'domain': entity_id.split('.')[0],
                        'condition_entity': trigger_entity,
                        'condition_state': trigger_state,
                        'target_state': action_state,
                        'confidence': 1.0,
                        'occurrences': 1
                    }
                    patterns.append(pattern)
                
                # Generate YAML for each pattern
                yaml_contents = []
                for pattern in patterns:
                    yaml_content = self.suggestion_engine._generate_conditional_automation_yaml(pattern)
                    yaml_contents.append(yaml_content)
                
            elif template_type == 'sequence':
                state = options.get('state', 'on')
                
                # Create a sequence pattern
                steps = []
                for entity_id in entities:
                    steps.append({
                        'entity_id': entity_id,
                        'state': state,
                        'domain': entity_id.split('.')[0]
                    })
                
                pattern = {
                    'type': 'sequence',
                    'steps': steps,
                    'confidence': 1.0,
                    'occurrences': 1
                }
                
                # Generate YAML for the pattern
                yaml_content = self.suggestion_engine._generate_sequence_automation_yaml(pattern)
                yaml_contents = [yaml_content]
                
            else:
                return {
                    'success': False,
                    'error': f"Unknown template type: {template_type}"
                }
            
            # Return the generated automations
            return {
                'success': True,
                'template_type': template_type,
                'entities': entities,
                'options': options,
                'yaml_contents': yaml_contents
            }
            
        except Exception as e:
            logger.error(f"Error creating template automation: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Claude-specific functions for automation management

def get_automations_list(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a list of all automations for Claude.
    
    Args:
        config (Dict[str, Any]): Configuration dictionary
        
    Returns:
        Dict[str, Any]: Automation list data
    """
    tools = AutomationTools(config)
    result = asyncio.run(tools.get_automations())
    return result

def get_automation_details_for_claude(config: Dict[str, Any], automation_id: str) -> Dict[str, Any]:
    """
    Get details about a specific automation for Claude.
    
    Args:
        config (Dict[str, Any]): Configuration dictionary
        automation_id (str): Automation ID
        
    Returns:
        Dict[str, Any]: Automation details
    """
    tools = AutomationTools(config)
    result = asyncio.run(tools.get_automation_details(automation_id))
    return result

def create_automation_for_claude(config: Dict[str, Any], automation_yaml: str) -> Dict[str, Any]:
    """
    Create a new automation for Claude.
    
    Args:
        config (Dict[str, Any]): Configuration dictionary
        automation_yaml (str): Automation YAML content
        
    Returns:
        Dict[str, Any]: Creation result
    """
    tools = AutomationTools(config)
    result = asyncio.run(tools.create_automation(automation_yaml))
    return result

def test_automation_for_claude(config: Dict[str, Any], automation_yaml: str) -> Dict[str, Any]:
    """
    Test an automation configuration for Claude.
    
    Args:
        config (Dict[str, Any]): Configuration dictionary
        automation_yaml (str): Automation YAML content
        
    Returns:
        Dict[str, Any]: Test results
    """
    tools = AutomationTools(config)
    result = asyncio.run(tools.test_automation(automation_yaml))
    return result

def suggest_automations_for_claude(config: Dict[str, Any], days: int = 7) -> Dict[str, Any]:
    """
    Generate automation suggestions for Claude.
    
    Args:
        config (Dict[str, Any]): Configuration dictionary
        days (int, optional): Number of days of history to analyze
        
    Returns:
        Dict[str, Any]: Automation suggestions
    """
    tools = AutomationTools(config)
    result = asyncio.run(tools.suggest_automations(days))
    return result