"""
Home Assistant Advanced Configuration Validator.

This module provides advanced validation functionality for Home Assistant configurations.
"""

import logging
import yaml
import json
import requests
import tempfile
import subprocess
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union, Set

from src.connection.api import HomeAssistantAPI

logger = logging.getLogger(__name__)

class AdvancedValidator:
    """Class for advanced validation of Home Assistant configurations."""
    
    def __init__(self, config: Dict[str, Any], api: HomeAssistantAPI):
        """
        Initialize the advanced validator.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
            api (HomeAssistantAPI): HomeAssistantAPI instance
        """
        self.config = config
        self.api = api
        self.ha_url = config['home_assistant']['url']
        self.ha_token = config['home_assistant']['token']
        
        # Card type definitions for Lovelace dashboards
        self.valid_card_types = {
            'alarm-panel', 'button', 'calendar', 'entities', 'entity', 'entity-filter',
            'gauge', 'glance', 'grid', 'history-graph', 'horizontal-stack', 'humidifier',
            'iframe', 'light', 'logbook', 'map', 'markdown', 'media-control', 'picture',
            'picture-elements', 'picture-entity', 'picture-glance', 'plant-status',
            'sensor', 'shopping-list', 'statistic', 'statistics-graph', 'thermostat',
            'tile', 'vertical-stack', 'weather-forecast'
        }
        
        # Valid automation trigger platforms
        self.valid_trigger_platforms = {
            'state', 'numeric_state', 'template', 'time', 'time_pattern', 'webhook',
            'sun', 'device', 'calendar', 'event', 'homeassistant', 'mqtt', 'tag',
            'zone', 'geo_location', 'conversation'
        }
        
        # Valid action types
        self.valid_action_types = {
            'service', 'device_id', 'delay', 'wait_template', 'condition', 'event',
            'repeat', 'choose', 'wait_for_trigger', 'variables', 'stop', 'parallel'
        }
    
    async def validate_entity_references(self, yaml_content: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate entity references in a YAML configuration.
        
        Args:
            yaml_content (str): YAML content to validate
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, result_dict)
                result_dict contains:
                - 'valid': bool
                - 'errors': list of error messages
                - 'warnings': list of warning messages
                - 'referenced_entities': list of entity IDs referenced
                - 'invalid_entities': list of invalid entity IDs referenced
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'referenced_entities': set(),
            'invalid_entities': set()
        }
        
        try:
            # Get all existing entities from Home Assistant
            existing_entities = await self.api.get_states()
            existing_entity_ids = {entity['entity_id'] for entity in existing_entities}
            
            # Extract entity references from the YAML content
            entity_pattern = r'entity(?:_id)?:\s*([a-z]+\.[a-z0-9_]+)'
            entities_pattern = r'entities:\s*(?:-\s*([a-z]+\.[a-z0-9_]+)|(?:\n\s*-\s*([a-z]+\.[a-z0-9_]+)))'
            
            # Find all entity: and entity_id: references
            for match in re.finditer(entity_pattern, yaml_content, re.IGNORECASE):
                entity_id = match.group(1)
                result['referenced_entities'].add(entity_id)
                
                if entity_id not in existing_entity_ids:
                    result['invalid_entities'].add(entity_id)
                    result['warnings'].append(f"Referenced entity '{entity_id}' doesn't exist in Home Assistant")
            
            # Find all entities: list references
            for match in re.finditer(entities_pattern, yaml_content, re.IGNORECASE):
                entity_id = match.group(1) or match.group(2)
                if entity_id:
                    result['referenced_entities'].add(entity_id)
                    
                    if entity_id not in existing_entity_ids:
                        result['invalid_entities'].add(entity_id)
                        result['warnings'].append(f"Referenced entity '{entity_id}' doesn't exist in Home Assistant")
            
            # If we found invalid entities, it's a warning but not an error
            if result['invalid_entities']:
                logger.warning(f"Found {len(result['invalid_entities'])} invalid entity references")
                
            return True, result
            
        except Exception as e:
            error_msg = f"Error validating entity references: {str(e)}"
            logger.error(error_msg)
            result['valid'] = False
            result['errors'].append(error_msg)
            return False, result
    
    async def validate_service_references(self, yaml_content: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate service references in a YAML configuration.
        
        Args:
            yaml_content (str): YAML content to validate
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, result_dict)
                result_dict contains:
                - 'valid': bool
                - 'errors': list of error messages
                - 'warnings': list of warning messages
                - 'referenced_services': list of services referenced
                - 'invalid_services': list of invalid services referenced
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'referenced_services': set(),
            'invalid_services': set()
        }
        
        try:
            # Get all available services from Home Assistant
            services = await self.api.get_services()
            available_services = set()
            
            # Build a set of available services as "domain.service"
            for domain, domain_services in services.items():
                for service in domain_services:
                    available_services.add(f"{domain}.{service}")
            
            # Extract service references from the YAML content
            service_pattern = r'service:\s*([a-z]+\.[a-z0-9_]+)'
            
            # Find all service: references
            for match in re.finditer(service_pattern, yaml_content, re.IGNORECASE):
                service_ref = match.group(1)
                result['referenced_services'].add(service_ref)
                
                if service_ref not in available_services:
                    result['invalid_services'].add(service_ref)
                    result['warnings'].append(f"Referenced service '{service_ref}' doesn't exist in Home Assistant")
            
            # If we found invalid services, it's a warning but not an error
            if result['invalid_services']:
                logger.warning(f"Found {len(result['invalid_services'])} invalid service references")
                
            return True, result
            
        except Exception as e:
            error_msg = f"Error validating service references: {str(e)}"
            logger.error(error_msg)
            result['valid'] = False
            result['errors'].append(error_msg)
            return False, result
    
    def validate_dashboard_card_types(self, dashboard_yaml: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate card types in a Lovelace dashboard configuration.
        
        Args:
            dashboard_yaml (str): Dashboard YAML content
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, result_dict)
                result_dict contains:
                - 'valid': bool
                - 'errors': list of error messages
                - 'warnings': list of warning messages
                - 'card_types': list of card types used
                - 'invalid_card_types': list of invalid card types used
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'card_types': set(),
            'invalid_card_types': set()
        }
        
        try:
            # Parse the YAML
            dashboard = yaml.safe_load(dashboard_yaml)
            
            if not isinstance(dashboard, dict) or 'views' not in dashboard:
                result['errors'].append("Invalid dashboard structure: missing 'views' key")
                result['valid'] = False
                return False, result
            
            # Iterate through views and cards
            for view_idx, view in enumerate(dashboard['views']):
                if not isinstance(view, dict):
                    result['errors'].append(f"View {view_idx} is not a dictionary")
                    result['valid'] = False
                    continue
                
                if 'cards' not in view:
                    # Views don't require cards, but it's unusual
                    result['warnings'].append(f"View '{view.get('title', view_idx)}' has no cards")
                    continue
                
                if not isinstance(view['cards'], list):
                    result['errors'].append(f"'cards' in view '{view.get('title', view_idx)}' is not a list")
                    result['valid'] = False
                    continue
                
                # Check each card
                for card_idx, card in enumerate(view['cards']):
                    if not isinstance(card, dict):
                        result['errors'].append(f"Card {card_idx} in view '{view.get('title', view_idx)}' is not a dictionary")
                        result['valid'] = False
                        continue
                    
                    if 'type' not in card:
                        result['errors'].append(f"Card {card_idx} in view '{view.get('title', view_idx)}' has no 'type'")
                        result['valid'] = False
                        continue
                    
                    card_type = card['type']
                    result['card_types'].add(card_type)
                    
                    if card_type not in self.valid_card_types:
                        result['invalid_card_types'].add(card_type)
                        result['warnings'].append(f"Card type '{card_type}' in view '{view.get('title', view_idx)}' is not a standard Lovelace card type")
            
            # If we found invalid card types, it's a warning but not an error
            if result['invalid_card_types']:
                logger.warning(f"Found {len(result['invalid_card_types'])} non-standard card types")
            
            return result['valid'], result
            
        except Exception as e:
            error_msg = f"Error validating dashboard card types: {str(e)}"
            logger.error(error_msg)
            result['valid'] = False
            result['errors'].append(error_msg)
            return False, result
    
    def validate_automation_triggers(self, automation_yaml: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate trigger configurations in an automation.
        
        Args:
            automation_yaml (str): Automation YAML content
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, result_dict)
                result_dict contains:
                - 'valid': bool
                - 'errors': list of error messages
                - 'warnings': list of warning messages
                - 'trigger_platforms': list of trigger platforms used
                - 'invalid_trigger_platforms': list of invalid trigger platforms
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'trigger_platforms': set(),
            'invalid_trigger_platforms': set()
        }
        
        try:
            # Parse the YAML
            automation = yaml.safe_load(automation_yaml)
            
            # Handle single automation or list of automations
            automations = automation if isinstance(automation, list) else [automation]
            
            for auto_idx, auto in enumerate(automations):
                if not isinstance(auto, dict):
                    result['errors'].append(f"Automation {auto_idx} is not a dictionary")
                    result['valid'] = False
                    continue
                
                if 'trigger' not in auto:
                    result['errors'].append(f"Automation {auto_idx} has no 'trigger'")
                    result['valid'] = False
                    continue
                
                # Get the triggers
                triggers = auto['trigger'] if isinstance(auto['trigger'], list) else [auto['trigger']]
                
                # Check each trigger
                for trigger_idx, trigger in enumerate(triggers):
                    if not isinstance(trigger, dict):
                        result['errors'].append(f"Trigger {trigger_idx} in automation {auto_idx} is not a dictionary")
                        result['valid'] = False
                        continue
                    
                    if 'platform' not in trigger:
                        result['errors'].append(f"Trigger {trigger_idx} in automation {auto_idx} has no 'platform'")
                        result['valid'] = False
                        continue
                    
                    platform = trigger['platform']
                    result['trigger_platforms'].add(platform)
                    
                    if platform not in self.valid_trigger_platforms:
                        result['invalid_trigger_platforms'].add(platform)
                        result['warnings'].append(f"Trigger platform '{platform}' in automation {auto_idx} is not a standard platform")
                    
                    # Validate platform-specific fields
                    if platform == 'state':
                        if 'entity_id' not in trigger:
                            result['errors'].append(f"State trigger {trigger_idx} in automation {auto_idx} has no 'entity_id'")
                            result['valid'] = False
                    elif platform == 'time':
                        if 'at' not in trigger:
                            result['errors'].append(f"Time trigger {trigger_idx} in automation {auto_idx} has no 'at'")
                            result['valid'] = False
            
            # If we found invalid platforms, it's a warning but not an error
            if result['invalid_trigger_platforms']:
                logger.warning(f"Found {len(result['invalid_trigger_platforms'])} non-standard trigger platforms")
            
            return result['valid'], result
            
        except Exception as e:
            error_msg = f"Error validating automation triggers: {str(e)}"
            logger.error(error_msg)
            result['valid'] = False
            result['errors'].append(error_msg)
            return False, result
    
    async def validate_config_against_api(self, config_type: str, yaml_content: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate a configuration against the Home Assistant API.
        
        Args:
            config_type (str): Type of configuration (dashboard, automation, etc.)
            yaml_content (str): YAML content to validate
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, result_dict)
                result_dict contains validation results
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'config_type': config_type
        }
        
        try:
            # Call specific validators based on config type
            if config_type == 'dashboard':
                # Validate card types
                card_valid, card_result = self.validate_dashboard_card_types(yaml_content)
                if not card_valid:
                    result['valid'] = False
                
                result['errors'].extend(card_result['errors'])
                result['warnings'].extend(card_result['warnings'])
                result['card_types'] = card_result['card_types']
                result['invalid_card_types'] = card_result['invalid_card_types']
                
                # Validate entity references
                entity_valid, entity_result = await self.validate_entity_references(yaml_content)
                if not entity_valid:
                    result['valid'] = False
                
                result['errors'].extend(entity_result['errors'])
                result['warnings'].extend(entity_result['warnings'])
                result['referenced_entities'] = entity_result['referenced_entities']
                result['invalid_entities'] = entity_result['invalid_entities']
                
            elif config_type == 'automation':
                # Validate trigger configurations
                trigger_valid, trigger_result = self.validate_automation_triggers(yaml_content)
                if not trigger_valid:
                    result['valid'] = False
                
                result['errors'].extend(trigger_result['errors'])
                result['warnings'].extend(trigger_result['warnings'])
                result['trigger_platforms'] = trigger_result['trigger_platforms']
                result['invalid_trigger_platforms'] = trigger_result['invalid_trigger_platforms']
                
                # Validate entity references
                entity_valid, entity_result = await self.validate_entity_references(yaml_content)
                if not entity_valid:
                    result['valid'] = False
                
                result['errors'].extend(entity_result['errors'])
                result['warnings'].extend(entity_result['warnings'])
                result['referenced_entities'] = entity_result['referenced_entities']
                result['invalid_entities'] = entity_result['invalid_entities']
                
                # Validate service references
                service_valid, service_result = await self.validate_service_references(yaml_content)
                if not service_valid:
                    result['valid'] = False
                
                result['errors'].extend(service_result['errors'])
                result['warnings'].extend(service_result['warnings'])
                result['referenced_services'] = service_result['referenced_services']
                result['invalid_services'] = service_result['invalid_services']
            
            else:
                # For other configuration types, just check entity references
                entity_valid, entity_result = await self.validate_entity_references(yaml_content)
                if not entity_valid:
                    result['valid'] = False
                
                result['errors'].extend(entity_result['errors'])
                result['warnings'].extend(entity_result['warnings'])
                result['referenced_entities'] = entity_result['referenced_entities']
                result['invalid_entities'] = entity_result['invalid_entities']
            
            # Convert sets to lists for JSON serialization
            for key in result:
                if isinstance(result[key], set):
                    result[key] = list(result[key])
            
            return result['valid'], result
            
        except Exception as e:
            error_msg = f"Error validating configuration against API: {str(e)}"
            logger.error(error_msg)
            result['valid'] = False
            result['errors'].append(error_msg)
            
            # Convert sets to lists for JSON serialization
            for key in result:
                if isinstance(result[key], set):
                    result[key] = list(result[key])
                    
            return False, result