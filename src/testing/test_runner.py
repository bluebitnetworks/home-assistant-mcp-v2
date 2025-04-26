"""
Home Assistant Configuration Test Runner.

This module provides functionality to run tests against Home Assistant configurations.
"""

import logging
import yaml
import json
import asyncio
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union, Set

from src.connection.api import HomeAssistantAPI
from src.testing.validator import ConfigValidator
from src.testing.config_analyzer import ConfigAnalyzer

logger = logging.getLogger(__name__)

class ConfigTestRunner:
    """Class for running tests against Home Assistant configurations."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the configuration test runner.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
        """
        self.config = config
        self.validator = ConfigValidator(config)
        self.analyzer = ConfigAnalyzer()
        self.api = HomeAssistantAPI(config)
    
    async def test_dashboard_config(self, dashboard_yaml: str, apply_suggestions: bool = False) -> Dict[str, Any]:
        """
        Test a dashboard configuration.
        
        Args:
            dashboard_yaml (str): Dashboard YAML content
            apply_suggestions (bool, optional): Whether to apply suggestions to the dashboard. Defaults to False.
            
        Returns:
            Dict[str, Any]: Test results
        """
        results = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'suggestions': [],
            'applied_changes': [],
            'yaml_content': dashboard_yaml,
            'yaml_content_updated': dashboard_yaml,
            'config_type': 'dashboard'
        }
        
        try:
            # Validate the dashboard configuration
            valid, error = self.validator.validate_dashboard_config(dashboard_yaml)
            if not valid:
                results['errors'].append(error)
                return results
            
            # Validate against API
            validation_results = await self.validator.validate_config_against_api('dashboard', dashboard_yaml)
            results['valid'] = validation_results.get('valid', False)
            results['errors'] = validation_results.get('errors', [])
            results['warnings'] = validation_results.get('warnings', [])
            
            # Analyze the configuration
            validation_results['yaml_content'] = dashboard_yaml
            analysis = self.analyzer.analyze_validation_results(validation_results)
            
            # Add suggestions
            for rec in analysis.get('recommendations', []):
                results['suggestions'].append({
                    'type': 'recommendation',
                    'issue': rec.get('issue', ''),
                    'suggestion': rec.get('recommendation', ''),
                    'severity': rec.get('severity', 'low')
                })
            
            for practice in analysis.get('best_practices', []):
                results['suggestions'].append({
                    'type': 'best_practice',
                    'suggestion': practice,
                    'severity': 'low'
                })
            
            for perf in analysis.get('performance_suggestions', []):
                results['suggestions'].append({
                    'type': 'performance',
                    'suggestion': perf,
                    'severity': 'medium'
                })
            
            for sec in analysis.get('security_suggestions', []):
                results['suggestions'].append({
                    'type': 'security',
                    'suggestion': sec,
                    'severity': 'high'
                })
            
            # Apply suggestions if requested
            if apply_suggestions:
                updated_yaml = self._apply_dashboard_suggestions(dashboard_yaml, results['suggestions'])
                results['yaml_content_updated'] = updated_yaml
                results['applied_changes'].append('Applied automated suggestions to dashboard configuration')
            
            return results
            
        except Exception as e:
            error_msg = f"Error testing dashboard configuration: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            return results
    
    async def test_automation_config(self, automation_yaml: str, apply_suggestions: bool = False) -> Dict[str, Any]:
        """
        Test an automation configuration.
        
        Args:
            automation_yaml (str): Automation YAML content
            apply_suggestions (bool, optional): Whether to apply suggestions to the automation. Defaults to False.
            
        Returns:
            Dict[str, Any]: Test results
        """
        results = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'suggestions': [],
            'applied_changes': [],
            'yaml_content': automation_yaml,
            'yaml_content_updated': automation_yaml,
            'config_type': 'automation'
        }
        
        try:
            # Validate the automation configuration
            valid, error = self.validator.validate_automation_config(automation_yaml)
            if not valid:
                results['errors'].append(error)
                return results
            
            # Validate against API
            validation_results = await self.validator.validate_config_against_api('automation', automation_yaml)
            results['valid'] = validation_results.get('valid', False)
            results['errors'] = validation_results.get('errors', [])
            results['warnings'] = validation_results.get('warnings', [])
            
            # Analyze the configuration
            validation_results['yaml_content'] = automation_yaml
            analysis = self.analyzer.analyze_validation_results(validation_results)
            
            # Add suggestions
            for rec in analysis.get('recommendations', []):
                results['suggestions'].append({
                    'type': 'recommendation',
                    'issue': rec.get('issue', ''),
                    'suggestion': rec.get('recommendation', ''),
                    'severity': rec.get('severity', 'low')
                })
            
            for practice in analysis.get('best_practices', []):
                results['suggestions'].append({
                    'type': 'best_practice',
                    'suggestion': practice,
                    'severity': 'low'
                })
            
            for perf in analysis.get('performance_suggestions', []):
                results['suggestions'].append({
                    'type': 'performance',
                    'suggestion': perf,
                    'severity': 'medium'
                })
            
            for sec in analysis.get('security_suggestions', []):
                results['suggestions'].append({
                    'type': 'security',
                    'suggestion': sec,
                    'severity': 'high'
                })
            
            # Apply suggestions if requested
            if apply_suggestions:
                updated_yaml = self._apply_automation_suggestions(automation_yaml, results['suggestions'])
                results['yaml_content_updated'] = updated_yaml
                results['applied_changes'].append('Applied automated suggestions to automation configuration')
            
            return results
            
        except Exception as e:
            error_msg = f"Error testing automation configuration: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            return results
    
    async def test_config_file(self, config_path: str, config_type: str = None, apply_suggestions: bool = False) -> Dict[str, Any]:
        """
        Test a configuration file.
        
        Args:
            config_path (str): Path to configuration file
            config_type (str, optional): Type of configuration. If None, will be determined from the file extension.
            apply_suggestions (bool, optional): Whether to apply suggestions to the configuration. Defaults to False.
            
        Returns:
            Dict[str, Any]: Test results
        """
        results = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'suggestions': [],
            'applied_changes': [],
            'file_path': config_path,
            'config_type': config_type
        }
        
        try:
            # Read the file
            with open(config_path, 'r') as f:
                yaml_content = f.read()
            
            results['yaml_content'] = yaml_content
            results['yaml_content_updated'] = yaml_content
            
            # Determine config type if not provided
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
            
            results['config_type'] = config_type
            
            # Validate file
            valid, validation_result = self.validator.validate_config_file(config_path, config_type)
            results['valid'] = valid
            results['errors'] = validation_result.get('errors', [])
            results['warnings'] = validation_result.get('warnings', [])
            
            # Perform specific tests based on config type
            if config_type == 'dashboard':
                test_results = await self.test_dashboard_config(yaml_content, apply_suggestions)
                results['suggestions'] = test_results.get('suggestions', [])
                if apply_suggestions:
                    results['yaml_content_updated'] = test_results.get('yaml_content_updated', yaml_content)
                    results['applied_changes'] = test_results.get('applied_changes', [])
                
            elif config_type == 'automation':
                test_results = await self.test_automation_config(yaml_content, apply_suggestions)
                results['suggestions'] = test_results.get('suggestions', [])
                if apply_suggestions:
                    results['yaml_content_updated'] = test_results.get('yaml_content_updated', yaml_content)
                    results['applied_changes'] = test_results.get('applied_changes', [])
            
            else:
                # For other types, just use the analyzer directly
                analysis = self.analyzer.analyze_yaml_content(yaml_content, config_type)
                
                # Add suggestions
                for rec in analysis.get('recommendations', []):
                    results['suggestions'].append({
                        'type': 'recommendation',
                        'issue': rec.get('issue', ''),
                        'suggestion': rec.get('recommendation', ''),
                        'severity': rec.get('severity', 'low')
                    })
                
                for practice in analysis.get('best_practices', []):
                    results['suggestions'].append({
                        'type': 'best_practice',
                        'suggestion': practice,
                        'severity': 'low'
                    })
                
                for perf in analysis.get('performance_suggestions', []):
                    results['suggestions'].append({
                        'type': 'performance',
                        'suggestion': perf,
                        'severity': 'medium'
                    })
                
                for sec in analysis.get('security_suggestions', []):
                    results['suggestions'].append({
                        'type': 'security',
                        'suggestion': sec,
                        'severity': 'high'
                    })
            
            # Apply suggestions to file if requested
            if apply_suggestions and results['yaml_content'] != results['yaml_content_updated']:
                with open(config_path, 'w') as f:
                    f.write(results['yaml_content_updated'])
                results['applied_changes'].append(f"Applied changes to {config_path}")
            
            return results
            
        except Exception as e:
            error_msg = f"Error testing configuration file: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            return results
    
    async def test_ha_config_dir(self, config_dir: str, apply_suggestions: bool = False) -> Dict[str, Any]:
        """
        Test a Home Assistant configuration directory.
        
        Args:
            config_dir (str): Path to Home Assistant configuration directory
            apply_suggestions (bool, optional): Whether to apply suggestions to the configurations. Defaults to False.
            
        Returns:
            Dict[str, Any]: Test results
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'file_results': {},
            'suggestions': [],
            'config_dir': config_dir
        }
        
        try:
            # Check if the directory exists
            config_path = Path(config_dir)
            if not config_path.exists() or not config_path.is_dir():
                results['valid'] = False
                results['errors'].append(f"Configuration directory {config_dir} does not exist")
                return results
            
            # First, run the basic configuration check
            valid, check_result = self.validator.check_config_with_hass_cli(config_dir)
            if not valid:
                results['valid'] = False
                results['errors'].extend(check_result.get('errors', []))
                results['warnings'].extend(check_result.get('warnings', []))
            
            # Find all YAML files in the configuration directory
            yaml_files = []
            for ext in ['.yaml', '.yml']:
                yaml_files.extend(list(config_path.glob(f"**/*{ext}")))
            
            # Test each YAML file
            for yaml_file in yaml_files:
                # Skip files that are unlikely to be Home Assistant config files
                if yaml_file.name.startswith('.') or yaml_file.name == 'secrets.yaml':
                    continue
                
                # Determine the config type
                config_type = 'unknown'
                rel_path = yaml_file.relative_to(config_path)
                file_path = str(yaml_file)
                
                if 'lovelace' in file_path or 'dashboard' in file_path or 'ui-lovelace' in file_path:
                    config_type = 'dashboard'
                elif 'automation' in file_path:
                    config_type = 'automation'
                elif 'script' in file_path:
                    config_type = 'script'
                elif 'sensor' in file_path:
                    config_type = 'sensor'
                elif yaml_file.name == 'configuration.yaml':
                    config_type = 'core'
                
                # Test the file
                file_result = await self.test_config_file(file_path, config_type, apply_suggestions)
                
                # Store the result
                results['file_results'][str(rel_path)] = file_result
                
                # Update overall results
                if not file_result.get('valid', True):
                    results['valid'] = False
                
                results['errors'].extend([f"{rel_path}: {error}" for error in file_result.get('errors', [])])
                results['warnings'].extend([f"{rel_path}: {warning}" for warning in file_result.get('warnings', [])])
                
                # Add key suggestions to the overall results
                high_severity_suggestions = [s for s in file_result.get('suggestions', []) if s.get('severity') == 'high']
                if high_severity_suggestions:
                    for suggestion in high_severity_suggestions:
                        results['suggestions'].append({
                            'file': str(rel_path),
                            'type': suggestion.get('type', 'recommendation'),
                            'issue': suggestion.get('issue', ''),
                            'suggestion': suggestion.get('suggestion', ''),
                            'severity': 'high'
                        })
            
            return results
            
        except Exception as e:
            error_msg = f"Error testing Home Assistant configuration directory: {str(e)}"
            logger.error(error_msg)
            results['valid'] = False
            results['errors'].append(error_msg)
            return results
    
    def _apply_dashboard_suggestions(self, dashboard_yaml: str, suggestions: List[Dict[str, Any]]) -> str:
        """
        Apply suggestions to a dashboard configuration.
        
        Args:
            dashboard_yaml (str): Dashboard YAML content
            suggestions (List[Dict[str, Any]]): List of suggestions
            
        Returns:
            str: Updated dashboard YAML content
        """
        try:
            # Parse the YAML
            dashboard = yaml.safe_load(dashboard_yaml)
            if not isinstance(dashboard, dict):
                return dashboard_yaml
            
            # Apply suggestions
            # For now, we just implement a few basic auto-fixes
            modified = False
            
            # Add theme if missing
            if 'theme' not in dashboard:
                for suggestion in suggestions:
                    if suggestion.get('issue', '').endswith("doesn't specify a theme"):
                        dashboard['theme'] = 'default'
                        modified = True
                        break
            
            # Add icons to views without them
            views = dashboard.get('views', [])
            for view_idx, view in enumerate(views):
                if not isinstance(view, dict):
                    continue
                
                if 'icon' not in view and view.get('show_in_sidebar', True):
                    for suggestion in suggestions:
                        if 'issue' in suggestion and 'icon' in suggestion['issue'] and f"View '{view.get('title', '')}'" in suggestion['issue']:
                            # Determine an appropriate icon based on the view title
                            title = view.get('title', '').lower()
                            if 'home' in title or 'overview' in title:
                                view['icon'] = 'mdi:home'
                            elif 'light' in title or 'lighting' in title:
                                view['icon'] = 'mdi:lightbulb'
                            elif 'climate' in title or 'temperature' in title:
                                view['icon'] = 'mdi:thermostat'
                            elif 'security' in title or 'camera' in title:
                                view['icon'] = 'mdi:shield-home'
                            else:
                                view['icon'] = 'mdi:view-dashboard'
                            
                            modified = True
                            break
            
            if modified:
                # Convert back to YAML
                return yaml.dump(dashboard, sort_keys=False)
            else:
                return dashboard_yaml
                
        except Exception as e:
            logger.error(f"Error applying dashboard suggestions: {str(e)}")
            return dashboard_yaml
    
    def _apply_automation_suggestions(self, automation_yaml: str, suggestions: List[Dict[str, Any]]) -> str:
        """
        Apply suggestions to an automation configuration.
        
        Args:
            automation_yaml (str): Automation YAML content
            suggestions (List[Dict[str, Any]]): List of suggestions
            
        Returns:
            str: Updated automation YAML content
        """
        try:
            # Parse the YAML
            automation = yaml.safe_load(automation_yaml)
            if not isinstance(automation, (dict, list)):
                return automation_yaml
            
            # Handle single automation or list of automations
            automations = automation if isinstance(automation, list) else [automation]
            modified = False
            
            for auto_idx, auto in enumerate(automations):
                if not isinstance(auto, dict):
                    continue
                
                # Add mode if missing
                if 'mode' not in auto:
                    for suggestion in suggestions:
                        if 'issue' in suggestion and 'mode' in suggestion['issue'] and (
                            f"Automation '{auto.get('alias', auto.get('id', ''))}'" in suggestion['issue'] or
                            f"Automation {auto_idx}" in suggestion['issue']
                        ):
                            auto['mode'] = 'single'
                            modified = True
                            break
                
                # Add description if missing
                if 'description' not in auto:
                    for suggestion in suggestions:
                        if 'issue' in suggestion and 'description' in suggestion['issue'] and (
                            f"Automation '{auto.get('alias', auto.get('id', ''))}'" in suggestion['issue'] or
                            f"Automation {auto_idx}" in suggestion['issue']
                        ):
                            # Create a basic description based on alias or id
                            alias = auto.get('alias', auto.get('id', f'automation_{auto_idx}'))
                            auto['description'] = f"Automation for {alias}"
                            modified = True
                            break
            
            if modified:
                # Convert back to YAML
                if isinstance(automation, list):
                    return yaml.dump(automations, sort_keys=False)
                else:
                    return yaml.dump(automations[0], sort_keys=False)
            else:
                return automation_yaml
                
        except Exception as e:
            logger.error(f"Error applying automation suggestions: {str(e)}")
            return automation_yaml