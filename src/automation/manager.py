"""
Home Assistant Automation Manager.

This module handles managing Home Assistant automations, including
reading, creating, updating, and deleting automations.
"""

import logging
import yaml
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set

from src.connection.api import HomeAssistantAPI

logger = logging.getLogger(__name__)

class AutomationManager:
    """Class for managing Home Assistant automations."""
    
    def __init__(self, config: Dict[str, Any], api: HomeAssistantAPI = None):
        """
        Initialize the automation manager.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
            api (HomeAssistantAPI, optional): Home Assistant API instance
        """
        self.config = config
        self.api = api or HomeAssistantAPI(config)
        
        # Configuration paths
        self.ha_config_dir = self.config['home_assistant'].get('config_dir', '')
        self.automations_path = self._get_automations_path()
        
        # Cache for existing automations
        self.automation_cache = {}
        self.last_cache_refresh = None
    
    def _get_automations_path(self) -> str:
        """
        Get the path to the automations.yaml file.
        
        Returns:
            str: Path to the automations.yaml file
        """
        # Check if there's a specific automations path in config
        if 'automations_path' in self.config['home_assistant']:
            return self.config['home_assistant']['automations_path']
        
        # If we have a config directory, use that
        if self.ha_config_dir:
            # Check if there's an automations.yaml file
            path = Path(self.ha_config_dir) / 'automations.yaml'
            if path.exists():
                return str(path)
            
            # Check if there's an automation directory with yaml files
            auto_dir = Path(self.ha_config_dir) / 'automations'
            if auto_dir.exists() and auto_dir.is_dir():
                return str(auto_dir)
        
        # Default location
        return os.path.expanduser('~/automations.yaml')
    
    async def load_automations(self, refresh: bool = False) -> Dict[str, Any]:
        """
        Load automations from the Home Assistant configuration.
        
        Args:
            refresh (bool, optional): Force refresh from disk even if cached
            
        Returns:
            Dict[str, Any]: Dictionary of automation ID/alias to automation data
        """
        # Check if we need to refresh the cache
        if (not self.automation_cache or refresh or 
            not self.last_cache_refresh or 
            (datetime.now() - self.last_cache_refresh).total_seconds() > 300):
            
            automations = {}
            
            # Try to get automations from API first
            try:
                api_automations = await self.api.get_automations()
                if api_automations:
                    # Process automations from API
                    for automation in api_automations:
                        if 'id' in automation:
                            automations[automation['id']] = automation
                        elif 'entity_id' in automation:
                            # Extract ID from entity_id
                            entity_id = automation['entity_id']
                            if entity_id.startswith('automation.'):
                                automations[entity_id[11:]] = automation
            except Exception as e:
                logger.warning(f"Failed to get automations from API: {e}")
            
            # If API didn't work or returned empty, try loading from file
            if not automations:
                automations = self._load_automations_from_file()
            
            self.automation_cache = automations
            self.last_cache_refresh = datetime.now()
        
        return self.automation_cache
    
    def _load_automations_from_file(self) -> Dict[str, Any]:
        """
        Load automations from the configuration file.
        
        Returns:
            Dict[str, Any]: Dictionary of automation ID/alias to automation data
        """
        automations = {}
        
        try:
            # Check if automations_path is a file or directory
            path = Path(self.automations_path)
            
            if path.is_file():
                # Load from a single file
                with open(path, 'r') as f:
                    content = yaml.safe_load(f)
                    
                    # Handle different formats (list or dict)
                    if isinstance(content, list):
                        for auto in content:
                            if isinstance(auto, dict):
                                # Use ID if available, otherwise alias or index
                                key = auto.get('id', auto.get('alias', f"auto_{len(automations)}"))
                                automations[key] = auto
                    elif isinstance(content, dict):
                        # Format where the keys are the automation IDs
                        for auto_id, auto in content.items():
                            if isinstance(auto, dict):
                                automations[auto_id] = auto
            
            elif path.is_dir():
                # Load from multiple files in a directory
                for yaml_file in path.glob('*.yaml'):
                    try:
                        with open(yaml_file, 'r') as f:
                            content = yaml.safe_load(f)
                            
                            # Handle different formats
                            if isinstance(content, list):
                                for auto in content:
                                    if isinstance(auto, dict):
                                        key = auto.get('id', auto.get('alias', yaml_file.stem))
                                        automations[key] = auto
                            elif isinstance(content, dict):
                                key = content.get('id', content.get('alias', yaml_file.stem))
                                automations[key] = content
                    except Exception as e:
                        logger.error(f"Failed to load automation file {yaml_file}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to load automations from file: {e}")
        
        return automations
    
    async def save_automation(self, automation: Dict[str, Any]) -> bool:
        """
        Save an automation to the configuration.
        
        Args:
            automation (Dict[str, Any]): Automation configuration
            
        Returns:
            bool: Success status
        """
        try:
            # Ensure automation has an ID
            if 'id' not in automation:
                automation['id'] = f"auto_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Get existing automations
            automations = await self.load_automations()
            
            # Update or add the automation
            automations[automation['id']] = automation
            
            # Save to file
            success = self._save_automations_to_file(automations)
            
            # If saved successfully, update the cache
            if success:
                self.automation_cache = automations
                self.last_cache_refresh = datetime.now()
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to save automation: {e}")
            return False
    
    def _save_automations_to_file(self, automations: Dict[str, Any]) -> bool:
        """
        Save automations to the configuration file.
        
        Args:
            automations (Dict[str, Any]): Automations to save
            
        Returns:
            bool: Success status
        """
        try:
            # Convert dictionary to list for YAML output
            automation_list = list(automations.values())
            
            # Check if automations_path is a file or directory
            path = Path(self.automations_path)
            
            if path.is_file() or not path.exists():
                # Save to a single file
                os.makedirs(path.parent, exist_ok=True)
                with open(path, 'w') as f:
                    yaml.dump(automation_list, f, sort_keys=False, default_flow_style=False)
            
            elif path.is_dir():
                # Save each automation to a separate file
                os.makedirs(path, exist_ok=True)
                
                # Clear existing files
                for yaml_file in path.glob('*.yaml'):
                    yaml_file.unlink()
                
                # Save each automation
                for auto_id, auto in automations.items():
                    # Generate a filename from the ID or alias
                    filename = auto.get('id', auto.get('alias', f"auto_{len(automations)}"))
                    filename = filename.replace(' ', '_').lower()
                    
                    file_path = path / f"{filename}.yaml"
                    with open(file_path, 'w') as f:
                        yaml.dump(auto, f, sort_keys=False, default_flow_style=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save automations to file: {e}")
            return False
    
    async def delete_automation(self, automation_id: str) -> bool:
        """
        Delete an automation from the configuration.
        
        Args:
            automation_id (str): Automation ID to delete
            
        Returns:
            bool: Success status
        """
        try:
            # Get existing automations
            automations = await self.load_automations()
            
            # Check if automation exists
            if automation_id not in automations:
                logger.warning(f"Automation {automation_id} not found, cannot delete")
                return False
            
            # Remove the automation
            del automations[automation_id]
            
            # Save to file
            success = self._save_automations_to_file(automations)
            
            # If saved successfully, update the cache
            if success:
                self.automation_cache = automations
                self.last_cache_refresh = datetime.now()
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete automation: {e}")
            return False
    
    async def enable_disable_automation(self, automation_id: str, enable: bool) -> bool:
        """
        Enable or disable an automation.
        
        Args:
            automation_id (str): Automation ID to enable/disable
            enable (bool): True to enable, False to disable
            
        Returns:
            bool: Success status
        """
        try:
            # Try using the API first
            service = 'automation.turn_on' if enable else 'automation.turn_off'
            
            try:
                await self.api.call_service(service, {'entity_id': f"automation.{automation_id}"})
                return True
            except Exception as api_error:
                logger.warning(f"Failed to {service} via API: {api_error}")
            
            # If API failed, try updating the file
            automations = await self.load_automations()
            
            if automation_id in automations:
                # Update the enabled state
                if 'enabled' in automations[automation_id]:
                    automations[automation_id]['enabled'] = enable
                elif not enable:
                    # Only add 'enabled: false' if disabling, otherwise let HA manage it
                    automations[automation_id]['enabled'] = False
                
                # Save to file
                success = self._save_automations_to_file(automations)
                
                # If saved successfully, update the cache
                if success:
                    self.automation_cache = automations
                    self.last_cache_refresh = datetime.now()
                
                return success
            else:
                logger.warning(f"Automation {automation_id} not found, cannot enable/disable")
                return False
                
        except Exception as e:
            logger.error(f"Failed to enable/disable automation: {e}")
            return False
    
    async def trigger_automation(self, automation_id: str) -> bool:
        """
        Trigger an automation manually.
        
        Args:
            automation_id (str): Automation ID to trigger
            
        Returns:
            bool: Success status
        """
        try:
            # Trigger the automation via the API
            await self.api.call_service('automation.trigger', {
                'entity_id': f"automation.{automation_id}"
            })
            return True
            
        except Exception as e:
            logger.error(f"Failed to trigger automation: {e}")
            return False
    
    def format_automation_for_display(self, automation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format an automation for display to the user.
        
        Args:
            automation (Dict[str, Any]): Automation configuration
            
        Returns:
            Dict[str, Any]: Formatted automation
        """
        # Create a simplified view of the automation
        formatted = {
            'id': automation.get('id', ''),
            'alias': automation.get('alias', 'Unnamed Automation'),
            'description': automation.get('description', ''),
            'enabled': automation.get('enabled', True)
        }
        
        # Add trigger information
        trigger = automation.get('trigger', [])
        if not isinstance(trigger, list):
            trigger = [trigger]
        
        formatted['triggers'] = []
        for t in trigger:
            if isinstance(t, dict):
                trigger_info = {'type': t.get('platform', 'unknown')}
                
                # Add details based on trigger type
                if t.get('platform') == 'state':
                    trigger_info['entity'] = t.get('entity_id', '')
                    trigger_info['to'] = t.get('to', '')
                    trigger_info['from'] = t.get('from', '')
                elif t.get('platform') == 'time':
                    trigger_info['at'] = t.get('at', '')
                
                formatted['triggers'].append(trigger_info)
        
        # Add action information
        action = automation.get('action', [])
        if not isinstance(action, list):
            action = [action]
        
        formatted['actions'] = []
        for a in action:
            if isinstance(a, dict):
                action_info = {'type': 'service' if 'service' in a else 'unknown'}
                
                # Add details based on action type
                if 'service' in a:
                    action_info['service'] = a.get('service', '')
                    
                    # Get entity IDs
                    if 'entity_id' in a:
                        action_info['entities'] = [a['entity_id']]
                    elif 'target' in a and 'entity_id' in a['target']:
                        entity_id = a['target']['entity_id']
                        if isinstance(entity_id, list):
                            action_info['entities'] = entity_id
                        else:
                            action_info['entities'] = [entity_id]
                    else:
                        action_info['entities'] = []
                
                formatted['actions'].append(action_info)
        
        return formatted
    
    async def get_automation_by_entity(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Find automations that reference a specific entity.
        
        Args:
            entity_id (str): Entity ID to search for
            
        Returns:
            List[Dict[str, Any]]: List of automations that reference the entity
        """
        automations = await self.load_automations()
        matching_automations = []
        
        # Convert automation dictionary to a list for processing
        auto_list = list(automations.values())
        
        for auto in auto_list:
            # Check triggers
            trigger = auto.get('trigger', [])
            if not isinstance(trigger, list):
                trigger = [trigger]
            
            for t in trigger:
                if isinstance(t, dict) and t.get('entity_id') == entity_id:
                    matching_automations.append(auto)
                    break
            
            # Check actions
            if auto not in matching_automations:  # Skip if already added
                action = auto.get('action', [])
                if not isinstance(action, list):
                    action = [action]
                
                for a in action:
                    if isinstance(a, dict):
                        # Check direct entity_id
                        if a.get('entity_id') == entity_id:
                            matching_automations.append(auto)
                            break
                        
                        # Check target.entity_id
                        if 'target' in a and 'entity_id' in a['target']:
                            target_entities = a['target']['entity_id']
                            if isinstance(target_entities, list) and entity_id in target_entities:
                                matching_automations.append(auto)
                                break
                            elif target_entities == entity_id:
                                matching_automations.append(auto)
                                break
        
        return matching_automations
    
    async def get_raw_automation_yaml(self, automation_id: str) -> Optional[str]:
        """
        Get the raw YAML for a specific automation.
        
        Args:
            automation_id (str): Automation ID
            
        Returns:
            Optional[str]: Raw YAML or None if not found
        """
        automations = await self.load_automations()
        
        if automation_id in automations:
            try:
                auto = automations[automation_id]
                return yaml.dump(auto, sort_keys=False, default_flow_style=False)
            except Exception as e:
                logger.error(f"Failed to generate YAML for automation {automation_id}: {e}")
                return None
        else:
            logger.warning(f"Automation {automation_id} not found, cannot get YAML")
            return None