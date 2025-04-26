"""
Home Assistant Configuration Testing and Validation.

This module handles validating Home Assistant configurations before deployment.
"""

import logging
import yaml
import json
import tempfile
import subprocess
import os
import requests
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union, Set

from src.connection.api import HomeAssistantAPI
from src.testing.advanced_validator import AdvancedValidator

logger = logging.getLogger(__name__)

class ConfigValidator:
    """Class for validating Home Assistant configurations."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the configuration validator.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
        """
        self.config = config
        self.ha_url = config['home_assistant']['url']
        self.ha_token = config['home_assistant']['token']
        self.api = None
        self.advanced_validator = None
    
    def setup_api(self):
        """
        Set up the API client if not already initialized.
        """
        if self.api is None:
            self.api = HomeAssistantAPI(self.config)
            self.advanced_validator = AdvancedValidator(self.config, self.api)
    
    def validate_yaml_syntax(self, yaml_content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate YAML syntax without checking Home Assistant schema.
        
        Args:
            yaml_content (str): YAML content to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            yaml.safe_load(yaml_content)
            return True, None
        except yaml.YAMLError as e:
            error_msg = f"YAML syntax error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def validate_dashboard_config(self, dashboard_yaml: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a Lovelace dashboard configuration.
        
        Args:
            dashboard_yaml (str): Dashboard YAML content
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # First validate YAML syntax
        valid_syntax, error = self.validate_yaml_syntax(dashboard_yaml)
        if not valid_syntax:
            return False, error
        
        # Parse the YAML to check for required fields
        try:
            dashboard = yaml.safe_load(dashboard_yaml)
            
            # Check for required keys
            if not isinstance(dashboard, dict):
                return False, "Dashboard configuration must be a dictionary"
            
            if 'views' not in dashboard:
                return False, "Dashboard must contain 'views' key"
            
            if not isinstance(dashboard['views'], list):
                return False, "'views' must be a list"
            
            # Check each view for required fields
            for i, view in enumerate(dashboard['views']):
                if not isinstance(view, dict):
                    return False, f"View {i} must be a dictionary"
                
                if 'path' not in view and 'title' not in view:
                    return False, f"View {i} must contain either 'path' or 'title'"
                
                if 'cards' in view and not isinstance(view['cards'], list):
                    return False, f"'cards' in view {i} must be a list"
            
            return True, None
            
        except Exception as e:
            error_msg = f"Dashboard validation error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def validate_automation_config(self, automation_yaml: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an automation configuration.
        
        Args:
            automation_yaml (str): Automation YAML content
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # First validate YAML syntax
        valid_syntax, error = self.validate_yaml_syntax(automation_yaml)
        if not valid_syntax:
            return False, error
        
        # Parse the YAML to check for required fields
        try:
            automation = yaml.safe_load(automation_yaml)
            
            # Handle single automation or list of automations
            automations = automation if isinstance(automation, list) else [automation]
            
            for i, auto in enumerate(automations):
                if not isinstance(auto, dict):
                    return False, f"Automation {i} must be a dictionary"
                
                # Check for required keys
                required_keys = ['trigger']
                missing_keys = [key for key in required_keys if key not in auto]
                
                if missing_keys:
                    return False, f"Automation {i} is missing required keys: {', '.join(missing_keys)}"
                
                # Check action exists (required for useful automation)
                if 'action' not in auto:
                    return False, f"Automation {i} is missing 'action' which is required for a useful automation"
                
                # Check that trigger is list or dict
                if not isinstance(auto['trigger'], (list, dict)):
                    return False, f"'trigger' in automation {i} must be a list or dictionary"
                
                # Check that action is list or dict
                if not isinstance(auto['action'], (list, dict)):
                    return False, f"'action' in automation {i} must be a list or dictionary"
            
            return True, None
            
        except Exception as e:
            error_msg = f"Automation validation error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def validate_script_config(self, script_yaml: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a script configuration.
        
        Args:
            script_yaml (str): Script YAML content
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # First validate YAML syntax
        valid_syntax, error = self.validate_yaml_syntax(script_yaml)
        if not valid_syntax:
            return False, error
        
        # Parse the YAML to check for required fields
        try:
            script = yaml.safe_load(script_yaml)
            
            # Handle script object or dict of scripts
            if isinstance(script, dict):
                # Check if it's a direct script or a collection of scripts
                if 'sequence' in script:
                    # It's a direct script configuration
                    if not isinstance(script['sequence'], (list, dict)):
                        return False, "'sequence' must be a list or dictionary"
                else:
                    # It's a collection of scripts
                    for script_name, script_config in script.items():
                        if not isinstance(script_config, dict):
                            return False, f"Script '{script_name}' must be a dictionary"
                        
                        if 'sequence' not in script_config:
                            return False, f"Script '{script_name}' is missing required 'sequence' key"
                        
                        if not isinstance(script_config['sequence'], (list, dict)):
                            return False, f"'sequence' in script '{script_name}' must be a list or dictionary"
            else:
                return False, "Script configuration must be a dictionary"
            
            return True, None
            
        except Exception as e:
            error_msg = f"Script validation error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def validate_sensor_config(self, sensor_yaml: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a sensor configuration.
        
        Args:
            sensor_yaml (str): Sensor YAML content
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # First validate YAML syntax
        valid_syntax, error = self.validate_yaml_syntax(sensor_yaml)
        if not valid_syntax:
            return False, error
        
        # Parse the YAML to check for required fields
        try:
            sensor = yaml.safe_load(sensor_yaml)
            
            # Handle single sensor or list of sensors
            sensors = sensor if isinstance(sensor, list) else [sensor]
            
            for i, sens in enumerate(sensors):
                if not isinstance(sens, dict):
                    return False, f"Sensor {i} must be a dictionary"
                
                # Check for required keys based on platform
                if 'platform' not in sens:
                    return False, f"Sensor {i} is missing required 'platform' key"
                
                platform = sens['platform']
                
                # Check platform-specific required fields
                if platform == 'template':
                    if 'sensors' not in sens:
                        return False, f"Template sensor {i} is missing required 'sensors' key"
                    
                    if not isinstance(sens['sensors'], dict):
                        return False, f"'sensors' in template sensor {i} must be a dictionary"
                    
                    # Check each template sensor
                    for sensor_name, sensor_config in sens['sensors'].items():
                        if not isinstance(sensor_config, dict):
                            return False, f"Template sensor '{sensor_name}' config must be a dictionary"
                        
                        if 'value_template' not in sensor_config:
                            return False, f"Template sensor '{sensor_name}' is missing required 'value_template' key"
                
                elif platform == 'rest':
                    if 'resource' not in sens:
                        return False, f"REST sensor {i} is missing required 'resource' key"
                
                elif platform == 'mqtt':
                    if 'state_topic' not in sens:
                        return False, f"MQTT sensor {i} is missing required 'state_topic' key"
            
            return True, None
            
        except Exception as e:
            error_msg = f"Sensor validation error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    async def validate_config_against_api(self, config_type: str, yaml_content: str) -> Dict[str, Any]:
        """
        Validate a configuration against the Home Assistant API.
        
        Args:
            config_type (str): Type of configuration (dashboard, automation, etc.)
            yaml_content (str): YAML content to validate
            
        Returns:
            Dict[str, Any]: Validation results
        """
        self.setup_api()
        
        try:
            valid, result = await self.advanced_validator.validate_config_against_api(
                config_type, yaml_content
            )
            
            return result
        except Exception as e:
            error_msg = f"Error validating configuration against API: {str(e)}"
            logger.error(error_msg)
            return {
                'valid': False,
                'errors': [error_msg],
                'warnings': [],
                'config_type': config_type
            }
    
    def validate_config_file(self, config_path: str, config_type: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate a configuration file.
        
        Args:
            config_path (str): Path to configuration file
            config_type (str, optional): Type of configuration. If None, will be determined from the file extension.
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, validation_results)
        """
        try:
            # Determine config type from file extension if not provided
            if config_type is None:
                file_extension = Path(config_path).suffix.lower()
                
                if 'lovelace' in config_path or 'dashboard' in config_path:
                    config_type = 'dashboard'
                elif 'automation' in config_path:
                    config_type = 'automation'
                elif 'script' in config_path:
                    config_type = 'script'
                elif 'sensor' in config_path:
                    config_type = 'sensor'
                else:
                    config_type = 'unknown'
            
            # Read the file
            with open(config_path, 'r') as f:
                yaml_content = f.read()
            
            # Validate syntax based on config type
            if config_type == 'dashboard':
                valid, error = self.validate_dashboard_config(yaml_content)
            elif config_type == 'automation':
                valid, error = self.validate_automation_config(yaml_content)
            elif config_type == 'script':
                valid, error = self.validate_script_config(yaml_content)
            elif config_type == 'sensor':
                valid, error = self.validate_sensor_config(yaml_content)
            else:
                # Generic YAML validation
                valid, error = self.validate_yaml_syntax(yaml_content)
            
            result = {
                'valid': valid,
                'errors': [error] if error else [],
                'warnings': [],
                'config_type': config_type,
                'file_path': config_path
            }
            
            return valid, result
            
        except Exception as e:
            error_msg = f"Error validating configuration file: {str(e)}"
            logger.error(error_msg)
            return False, {
                'valid': False,
                'errors': [error_msg],
                'warnings': [],
                'config_type': config_type,
                'file_path': config_path
            }
    
    def check_config_with_hass_cli(self, config_dir: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check configuration using the Home Assistant CLI (hass).
        
        Args:
            config_dir (str): Path to Home Assistant configuration directory
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, validation_results)
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'output': '',
            'config_dir': config_dir
        }
        
        try:
            # Check if the hass command is available
            try:
                subprocess.run(['hass', '--version'], 
                              check=True, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
            except (subprocess.SubprocessError, FileNotFoundError):
                result['errors'].append("Home Assistant CLI (hass) not found. Please install Home Assistant CLI.")
                return False, result
            
            # Run the configuration check
            process = subprocess.run(['hass', '-c', config_dir, '--script', 'check_config'],
                                    check=False,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    universal_newlines=True)
            
            # Capture output
            output = process.stdout + '\n' + process.stderr
            result['output'] = output
            
            # Parse the output to determine if the configuration is valid
            if 'Configuration valid!' in output:
                result['valid'] = True
            else:
                result['valid'] = False
                
                # Extract error messages
                error_pattern = r'(?:ERROR|Invalid config|Error loading|Invalid configuration)(.*?)(?=\n[A-Z]|\Z)'
                for match in re.finditer(error_pattern, output, re.DOTALL):
                    error_msg = match.group(1).strip()
                    if error_msg:
                        result['errors'].append(error_msg)
                
                # Extract warning messages
                warning_pattern = r'(?:WARNING)(.*?)(?=\n[A-Z]|\Z)'
                for match in re.finditer(warning_pattern, output, re.DOTALL):
                    warning_msg = match.group(1).strip()
                    if warning_msg:
                        result['warnings'].append(warning_msg)
            
            return result['valid'], result
            
        except Exception as e:
            error_msg = f"Error checking configuration with Home Assistant CLI: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            return False, result
    
    def check_config_with_api(self, config_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check configuration validity by sending it to the Home Assistant API.
        
        Args:
            config_path (str): Path to configuration file
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, validation_results)
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'api_response': None,
            'file_path': config_path
        }
        
        try:
            # Read the configuration file
            with open(config_path, 'r') as f:
                config_content = f.read()
            
            # Determine the configuration type
            config_type = 'unknown'
            file_name = Path(config_path).name.lower()
            
            if 'lovelace' in file_name or 'dashboard' in file_name:
                config_type = 'dashboard'
            elif 'automation' in file_name:
                config_type = 'automation'
            elif 'script' in file_name:
                config_type = 'script'
            elif 'sensor' in file_name:
                config_type = 'sensor'
            
            # Prepare API URL based on config type
            url = f"{self.ha_url}/api/config/core/check_config"
            if config_type == 'dashboard':
                url = f"{self.ha_url}/api/lovelace/dashboards/validate"
            
            # Prepare headers
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json"
            }
            
            # Prepare payload
            payload = {
                "config": config_content
            }
            
            # Send the request
            response = requests.post(url, headers=headers, json=payload)
            
            # Process the response
            if response.status_code == 200:
                response_data = response.json()
                result['api_response'] = response_data
                
                if 'result' in response_data and response_data['result'] == 'valid':
                    result['valid'] = True
                elif 'valid' in response_data:
                    result['valid'] = response_data['valid']
                else:
                    result['valid'] = False
                    
                if 'errors' in response_data:
                    result['errors'] = response_data['errors']
                    
                if 'warnings' in response_data:
                    result['warnings'] = response_data['warnings']
                    
            else:
                result['valid'] = False
                result['errors'].append(f"API returned status code {response.status_code}: {response.text}")
            
            return result['valid'], result
            
        except Exception as e:
            error_msg = f"Error checking configuration with API: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            return False, result
    
    def simulate_config_check(self, config_path: str) -> Tuple[bool, Optional[str]]:
        """
        Simulate a Home Assistant configuration check.
        
        Note: This requires Home Assistant CLI tools or API access.
        
        Args:
            config_path (str): Path to configuration file
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # First try with API
            valid, result = self.check_config_with_api(config_path)
            
            if valid:
                return True, None
                
            if result['errors']:
                return False, "\n".join(result['errors'])
                
            # If API check failed but didn't provide errors, try with CLI
            config_dir = str(Path(config_path).parent)
            valid, result = self.check_config_with_hass_cli(config_dir)
            
            if valid:
                return True, None
                
            if result['errors']:
                return False, "\n".join(result['errors'])
                
            # Fallback to basic validation
            with open(config_path, 'r') as f:
                content = f.read()
            
            return self.validate_yaml_syntax(content)
            
        except Exception as e:
            error_msg = f"Configuration check failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg