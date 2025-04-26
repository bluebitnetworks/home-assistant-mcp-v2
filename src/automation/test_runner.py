"""
Home Assistant Automation Test Runner.

This module provides functionality for testing automations before deploying them.
"""

import logging
import yaml
import tempfile
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set

from src.connection.api import HomeAssistantAPI
from src.testing.validator import ConfigValidator

logger = logging.getLogger(__name__)

class AutomationTestRunner:
    """Class for testing Home Assistant automations."""
    
    def __init__(self, config: Dict[str, Any], api: HomeAssistantAPI = None):
        """
        Initialize the automation test runner.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
            api (HomeAssistantAPI, optional): Home Assistant API instance
        """
        self.config = config
        self.api = api or HomeAssistantAPI(config)
        self.validator = ConfigValidator(config)
    
    async def validate_automation_yaml(self, automation_yaml: str) -> Dict[str, Any]:
        """
        Validate automation YAML syntax and check for common issues.
        
        Args:
            automation_yaml (str): Automation YAML content
            
        Returns:
            Dict[str, Any]: Validation results
        """
        results = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'entities': []
        }
        
        # Basic validation
        valid, error = self.validator.validate_automation_config(automation_yaml)
        results['valid'] = valid
        
        if not valid:
            results['errors'].append(error)
            return results
        
        # Advanced validation using the validator API
        try:
            validation_results = await self.validator.validate_config_against_api('automation', automation_yaml)
            results['valid'] = validation_results.get('valid', False)
            results['errors'].extend(validation_results.get('errors', []))
            results['warnings'].extend(validation_results.get('warnings', []))
            
            # Extract referenced entities
            if 'referenced_entities' in validation_results:
                results['entities'] = validation_results['referenced_entities']
            
            # Check for invalid entities
            if 'invalid_entities' in validation_results and validation_results['invalid_entities']:
                for entity in validation_results['invalid_entities']:
                    results['warnings'].append(f"Referenced entity '{entity}' doesn't exist")
            
            # Check for invalid services
            if 'invalid_services' in validation_results and validation_results['invalid_services']:
                for service in validation_results['invalid_services']:
                    results['warnings'].append(f"Referenced service '{service}' doesn't exist")
        
        except Exception as e:
            logger.error(f"Error validating automation against API: {e}")
            results['warnings'].append(f"Could not perform advanced validation: {str(e)}")
        
        return results
    
    async def dry_run_automation(self, automation_yaml: str) -> Dict[str, Any]:
        """
        Perform a dry run of an automation to predict what would happen.
        
        Args:
            automation_yaml (str): Automation YAML content
            
        Returns:
            Dict[str, Any]: Dry run results
        """
        results = {
            'success': False,
            'actions': [],
            'entities_affected': [],
            'warnings': [],
            'error': None
        }
        
        try:
            # Parse the automation
            automation = yaml.safe_load(automation_yaml)
            
            # Handle single automation or list
            if isinstance(automation, list):
                if len(automation) == 0:
                    results['error'] = "Empty automation list"
                    return results
                automation = automation[0]
            
            if not isinstance(automation, dict):
                results['error'] = "Invalid automation format"
                return results
            
            # Analyze trigger
            trigger = automation.get('trigger', [])
            if not isinstance(trigger, list):
                trigger = [trigger]
            
            trigger_description = self._analyze_trigger(trigger)
            results['trigger_description'] = trigger_description
            
            # Analyze action
            action = automation.get('action', [])
            if not isinstance(action, list):
                action = [action]
            
            action_results = self._analyze_action(action)
            results['actions'] = action_results['actions']
            results['entities_affected'] = action_results['entities']
            results['warnings'].extend(action_results['warnings'])
            
            # Additional warnings
            if 'condition' not in automation or not automation['condition']:
                results['warnings'].append("Automation has no conditions, which may lead to unnecessary triggering.")
            
            if 'mode' not in automation:
                results['warnings'].append("No mode specified, defaults to 'single'. Consider setting mode explicitly.")
            
            results['success'] = True
            
        except Exception as e:
            logger.error(f"Error in dry run: {e}")
            results['error'] = str(e)
        
        return results
    
    async def simulate_automation_execution(self, automation_yaml: str) -> Dict[str, Any]:
        """
        Simulate the execution of an automation to see what states would be changed.
        
        Args:
            automation_yaml (str): Automation YAML content
            
        Returns:
            Dict[str, Any]: Simulation results
        """
        results = {
            'success': False,
            'steps': [],
            'warning': None,
            'error': None
        }
        
        try:
            # Get current states of all entities
            try:
                entity_states = await self.api.get_states()
                current_states = {entity['entity_id']: entity.get('state', 'unknown') for entity in entity_states}
            except Exception as e:
                logger.warning(f"Could not get entity states from API: {e}")
                current_states = {}
                results['warning'] = "Could not get current entity states. Using placeholders."
            
            # Create a temporary file for the automation
            with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp_file:
                temp_file.write(automation_yaml.encode('utf-8'))
                temp_file_path = temp_file.name
            
            # Simulate execution
            dry_run = await self.dry_run_automation(automation_yaml)
            
            if not dry_run['success']:
                results['error'] = dry_run.get('error', "Dry run failed")
                return results
            
            # Build simulation steps
            simulation_steps = []
            
            # Add trigger step
            simulation_steps.append({
                'type': 'trigger',
                'description': dry_run.get('trigger_description', "Trigger activated")
            })
            
            # Add action steps
            for action in dry_run.get('actions', []):
                action_type = action.get('type', 'unknown')
                
                if action_type == 'service_call':
                    service = action.get('service', '')
                    entity_id = action.get('entity_id', '')
                    
                    # Determine the effect of the service call
                    effect = "unknown"
                    new_state = "unknown"
                    
                    if service.endswith('.turn_on'):
                        effect = "turn on"
                        new_state = "on"
                    elif service.endswith('.turn_off'):
                        effect = "turn off"
                        new_state = "off"
                    elif 'set_' in service:
                        effect = f"set to {action.get('data', {})}"
                        
                        # Try to determine the new state for common services
                        if service == 'climate.set_hvac_mode' and 'hvac_mode' in action.get('data', {}):
                            new_state = action['data']['hvac_mode']
                        elif service == 'light.turn_on' and 'brightness' in action.get('data', {}):
                            new_state = f"on (brightness: {action['data']['brightness']})"
                    
                    # Get current state
                    old_state = current_states.get(entity_id, "unknown")
                    
                    simulation_steps.append({
                        'type': 'action',
                        'service': service,
                        'entity_id': entity_id,
                        'effect': effect,
                        'old_state': old_state,
                        'new_state': new_state
                    })
                
                elif action_type == 'delay':
                    simulation_steps.append({
                        'type': 'delay',
                        'delay': action.get('delay', '0')
                    })
                
                else:
                    simulation_steps.append({
                        'type': action_type,
                        'description': f"Execute {action_type} action"
                    })
            
            results['steps'] = simulation_steps
            results['success'] = True
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
        except Exception as e:
            logger.error(f"Error in simulation: {e}")
            results['error'] = str(e)
        
        return results
    
    async def test_automation_trigger(self, automation_yaml: str) -> Dict[str, Any]:
        """
        Test if an automation trigger can be activated.
        
        Args:
            automation_yaml (str): Automation YAML content
            
        Returns:
            Dict[str, Any]: Trigger test results
        """
        results = {
            'success': False,
            'trigger_type': 'unknown',
            'can_test': False,
            'test_instructions': None,
            'warning': None,
            'error': None
        }
        
        try:
            # Parse the automation
            automation = yaml.safe_load(automation_yaml)
            
            # Handle single automation or list
            if isinstance(automation, list):
                if len(automation) == 0:
                    results['error'] = "Empty automation list"
                    return results
                automation = automation[0]
            
            if not isinstance(automation, dict):
                results['error'] = "Invalid automation format"
                return results
            
            # Get the trigger
            trigger = automation.get('trigger', [])
            if not isinstance(trigger, list):
                trigger = [trigger]
            
            if not trigger:
                results['error'] = "No trigger defined"
                return results
            
            # Analyze the first trigger
            first_trigger = trigger[0]
            if not isinstance(first_trigger, dict):
                results['error'] = "Invalid trigger format"
                return results
            
            platform = first_trigger.get('platform', 'unknown')
            results['trigger_type'] = platform
            
            # Check if we can test this trigger
            if platform == 'state':
                entity_id = first_trigger.get('entity_id', '')
                to_state = first_trigger.get('to', '')
                
                if entity_id and to_state:
                    results['can_test'] = True
                    results['test_entity'] = entity_id
                    results['test_state'] = to_state
                    results['test_instructions'] = f"Change {entity_id} to state '{to_state}'"
                
            elif platform == 'time':
                time_at = first_trigger.get('at', '')
                
                if time_at:
                    now = datetime.now()
                    target_time = datetime.strptime(time_at, '%H:%M:%S').replace(
                        year=now.year, month=now.month, day=now.day)
                    
                    # If target time is in the past today, add a day
                    if target_time < now:
                        target_time += timedelta(days=1)
                    
                    # Calculate time until trigger
                    time_diff = target_time - now
                    hours, remainder = divmod(time_diff.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    
                    results['can_test'] = False  # Can't directly test time triggers
                    results['test_instructions'] = (
                        f"This automation will trigger at {time_at}, which is in "
                        f"{hours} hours, {minutes} minutes, and {seconds} seconds."
                    )
            
            elif platform == 'numeric_state':
                entity_id = first_trigger.get('entity_id', '')
                above = first_trigger.get('above')
                below = first_trigger.get('below')
                
                condition = []
                if above is not None:
                    condition.append(f"above {above}")
                if below is not None:
                    condition.append(f"below {below}")
                
                if entity_id and condition:
                    results['can_test'] = True
                    results['test_entity'] = entity_id
                    results['test_instructions'] = f"Change {entity_id} to a value {' and '.join(condition)}"
            
            elif platform == 'template':
                template = first_trigger.get('value_template', '')
                
                if template:
                    results['can_test'] = False  # Templates require manual testing
                    results['test_instructions'] = f"This automation uses a template trigger: {template}"
            
            elif platform == 'webhook':
                webhook_id = first_trigger.get('webhook_id', '')
                
                if webhook_id:
                    webhook_url = f"{self.config['home_assistant']['url']}/api/webhook/{webhook_id}"
                    results['can_test'] = True
                    results['test_webhook_url'] = webhook_url
                    results['test_instructions'] = f"Send a POST request to {webhook_url}"
            
            else:
                results['can_test'] = False
                results['test_instructions'] = f"Cannot automatically test '{platform}' triggers."
            
            results['success'] = True
            
        except Exception as e:
            logger.error(f"Error testing trigger: {e}")
            results['error'] = str(e)
        
        return results
    
    async def validate_automation_templates(self, automation_yaml: str) -> Dict[str, Any]:
        """
        Validate templates used in an automation.
        
        Args:
            automation_yaml (str): Automation YAML content
            
        Returns:
            Dict[str, Any]: Template validation results
        """
        results = {
            'valid': True,
            'templates': [],
            'errors': [],
            'warnings': []
        }
        
        try:
            # Parse the automation
            automation = yaml.safe_load(automation_yaml)
            
            # Handle single automation or list
            if isinstance(automation, list):
                if not automation:
                    return results
                automation = automation[0]
            
            if not isinstance(automation, dict):
                results['errors'].append("Invalid automation format")
                results['valid'] = False
                return results
            
            # Extract templates from the automation
            templates = self._find_templates_in_object(automation)
            
            # Validate each template
            for location, template in templates:
                try:
                    # Try to render the template (works only with API)
                    # await self.api.render_template(template)
                    
                    # For now, just do basic syntax checking
                    self._validate_template_syntax(template)
                    
                    results['templates'].append({
                        'location': location,
                        'template': template,
                        'valid': True
                    })
                    
                except Exception as e:
                    results['templates'].append({
                        'location': location,
                        'template': template,
                        'valid': False,
                        'error': str(e)
                    })
                    
                    results['errors'].append(f"Template error in {location}: {str(e)}")
                    results['valid'] = False
            
            # Add warnings for unescaped curly braces
            for location, template in templates:
                if '{{' not in template and '{' in template:
                    results['warnings'].append(
                        f"Possible unescaped curly brace in {location}: {template}"
                    )
            
        except Exception as e:
            logger.error(f"Error validating templates: {e}")
            results['errors'].append(str(e))
            results['valid'] = False
        
        return results
    
    def _analyze_trigger(self, triggers: List[Dict[str, Any]]) -> str:
        """
        Create a human-readable description of the triggers.
        
        Args:
            triggers (List[Dict[str, Any]]): List of trigger configurations
            
        Returns:
            str: Human-readable description
        """
        if not triggers:
            return "No triggers defined"
        
        descriptions = []
        
        for trigger in triggers:
            if not isinstance(trigger, dict):
                continue
                
            platform = trigger.get('platform', 'unknown')
            
            if platform == 'state':
                entity_id = trigger.get('entity_id', 'unknown')
                to_state = trigger.get('to', 'any')
                from_state = trigger.get('from', 'any')
                
                if to_state != 'any' and from_state != 'any':
                    desc = f"When {entity_id} changes from '{from_state}' to '{to_state}'"
                elif to_state != 'any':
                    desc = f"When {entity_id} changes to '{to_state}'"
                elif from_state != 'any':
                    desc = f"When {entity_id} changes from '{from_state}'"
                else:
                    desc = f"When {entity_id} changes state"
                
                descriptions.append(desc)
                
            elif platform == 'time':
                at_time = trigger.get('at', 'unknown')
                descriptions.append(f"At {at_time}")
                
            elif platform == 'numeric_state':
                entity_id = trigger.get('entity_id', 'unknown')
                above = trigger.get('above')
                below = trigger.get('below')
                
                if above is not None and below is not None:
                    desc = f"When {entity_id} is between {above} and {below}"
                elif above is not None:
                    desc = f"When {entity_id} goes above {above}"
                elif below is not None:
                    desc = f"When {entity_id} goes below {below}"
                else:
                    desc = f"When {entity_id} changes numeric state"
                
                descriptions.append(desc)
                
            elif platform == 'template':
                template = trigger.get('value_template', 'unknown')
                descriptions.append(f"When template condition is met: {template}")
                
            elif platform == 'webhook':
                webhook_id = trigger.get('webhook_id', 'unknown')
                descriptions.append(f"When webhook {webhook_id} is called")
                
            else:
                descriptions.append(f"When {platform} trigger is activated")
        
        if len(descriptions) == 1:
            return descriptions[0]
        else:
            return "Multiple triggers: " + ", ".join(descriptions)
    
    def _analyze_action(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze the actions of an automation.
        
        Args:
            actions (List[Dict[str, Any]]): List of action configurations
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        results = {
            'actions': [],
            'entities': [],
            'warnings': []
        }
        
        for action in actions:
            if not isinstance(action, dict):
                continue
            
            # Service call action
            if 'service' in action:
                service = action['service']
                
                # Extract entity ID
                entity_id = None
                
                if 'entity_id' in action:
                    entity_id = action['entity_id']
                elif 'target' in action and 'entity_id' in action['target']:
                    entity_id = action['target']['entity_id']
                
                # Extract additional data
                data = action.get('data', {})
                
                action_info = {
                    'type': 'service_call',
                    'service': service,
                    'entity_id': entity_id,
                    'data': data
                }
                
                results['actions'].append(action_info)
                
                # Track affected entities
                if entity_id:
                    if isinstance(entity_id, list):
                        results['entities'].extend(entity_id)
                    else:
                        results['entities'].append(entity_id)
            
            # Delay action
            elif 'delay' in action:
                delay = action['delay']
                
                if isinstance(delay, (int, float)):
                    delay_str = f"{delay} seconds"
                else:
                    delay_str = str(delay)
                
                action_info = {
                    'type': 'delay',
                    'delay': delay_str
                }
                
                results['actions'].append(action_info)
            
            # Scene action
            elif 'scene' in action:
                scene = action['scene']
                
                action_info = {
                    'type': 'scene',
                    'scene': scene
                }
                
                results['actions'].append(action_info)
                results['entities'].append(f"scene.{scene}")
            
            # Wait template action
            elif 'wait_template' in action:
                template = action['wait_template']
                
                action_info = {
                    'type': 'wait_template',
                    'template': template
                }
                
                results['actions'].append(action_info)
            
            # Condition action
            elif 'condition' in action:
                condition = action['condition']
                
                action_info = {
                    'type': 'condition',
                    'condition': condition
                }
                
                results['actions'].append(action_info)
            
            # Other action types
            else:
                # Try to identify the action type
                for key in ['device_id', 'event', 'repeat', 'choose', 'variables']:
                    if key in action:
                        action_info = {
                            'type': key,
                            'details': action[key]
                        }
                        
                        results['actions'].append(action_info)
                        break
                else:
                    # Unknown action type
                    results['actions'].append({
                        'type': 'unknown',
                        'details': action
                    })
                    
                    results['warnings'].append("Unknown action type detected")
        
        # Check for issues
        if not actions:
            results['warnings'].append("No actions defined in automation")
        
        return results
    
    def _find_templates_in_object(self, obj: Any, path: str = '') -> List[Tuple[str, str]]:
        """
        Recursively find all template strings in an object.
        
        Args:
            obj (Any): Object to search
            path (str, optional): Current path in the object
            
        Returns:
            List[Tuple[str, str]]: List of (path, template) tuples
        """
        templates = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                
                # Check if this is a template key
                if key in ['value_template', 'template', 'wait_template'] and isinstance(value, str):
                    templates.append((new_path, value))
                
                # Recursively check nested objects
                templates.extend(self._find_templates_in_object(value, new_path))
                
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                new_path = f"{path}[{idx}]"
                templates.extend(self._find_templates_in_object(item, new_path))
        
        return templates
    
    def _validate_template_syntax(self, template: str) -> None:
        """
        Perform basic validation of template syntax.
        
        Args:
            template (str): Template string to validate
            
        Raises:
            ValueError: If the template has syntax errors
        """
        # Check for balanced {{ }}
        open_count = template.count('{{')
        close_count = template.count('}}')
        
        if open_count != close_count:
            raise ValueError(f"Unbalanced braces: {open_count} opening '{{{{' vs {close_count} closing '}}}}'")
        
        # Check for unclosed quotes
        in_quotes = False
        quote_char = None
        
        for char in template:
            if char in ['"', "'"]:
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
        
        if in_quotes:
            raise ValueError(f"Unclosed {quote_char} quotes")
        
        # Additional checks could be added for more complex validation
        # But those would require a full template parser