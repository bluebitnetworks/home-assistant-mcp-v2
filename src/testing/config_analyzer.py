"""
Home Assistant Configuration Analyzer.

This module analyzes Home Assistant configurations and provides recommendations
for improvements, optimizations, and issue fixes.
"""

import logging
import yaml
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union, Set

logger = logging.getLogger(__name__)

class ConfigAnalyzer:
    """Class for analyzing Home Assistant configurations and providing recommendations."""
    
    def __init__(self):
        """Initialize the configuration analyzer."""
        # Common issues and their recommendations
        self.common_issues = {
            # Dashboard issues
            'empty_view': {
                'pattern': r'View .*? has no cards',
                'recommendation': 'Add cards to the empty view to provide useful information.',
                'severity': 'low'
            },
            'non_standard_card': {
                'pattern': r'Card type .*? is not a standard Lovelace card type',
                'recommendation': 'Consider using standard card types for better compatibility.',
                'severity': 'low'
            },
            'invalid_entity': {
                'pattern': r"Referenced entity '.*?' doesn't exist",
                'recommendation': 'Update the reference to use an existing entity or create the missing entity.',
                'severity': 'high'
            },
            
            # Automation issues
            'missing_condition': {
                'pattern': r'Automation .* has no conditions',
                'recommendation': 'Consider adding conditions to prevent the automation from running unnecessarily.',
                'severity': 'medium'
            },
            'complex_trigger': {
                'pattern': r'Automation .* has .* triggers',
                'recommendation': 'Consider breaking down complex automations with many triggers into separate automations.',
                'severity': 'low'
            },
            'invalid_service': {
                'pattern': r"Referenced service '.*?' doesn't exist",
                'recommendation': 'Update the reference to use an existing service.',
                'severity': 'high'
            },
            
            # YAML issues
            'long_lines': {
                'pattern': r'Line .* is too long',
                'recommendation': 'Break down long lines for better readability.',
                'severity': 'low'
            },
            'inconsistent_indentation': {
                'pattern': r'Inconsistent indentation',
                'recommendation': 'Use consistent indentation (2 spaces is recommended).',
                'severity': 'medium'
            }
        }
        
        # Best practices for Home Assistant configurations
        self.best_practices = {
            'dashboard': [
                'Group related entities into separate views',
                'Use appropriate card types for different entity domains',
                'Include a title for each view and card for better clarity',
                'Consider using custom themes for better visual appeal',
                'Use grid or vertical-stack cards to organize related entities',
                'Keep dashboards simple and focused for better usability'
            ],
            'automation': [
                'Use descriptive IDs for automations',
                'Include mode: single to prevent multiple executions',
                'Add conditions to prevent unnecessary triggering',
                'Use variables for values used multiple times',
                'Break complex automations into smaller, more focused ones',
                'Add a description field to document the automation purpose'
            ],
            'script': [
                'Use descriptive IDs for scripts',
                'Include a description field to document the script purpose',
                'Set a default timeout to prevent scripts from running indefinitely',
                'Use variables for values used multiple times',
                'Break complex scripts into smaller, more focused ones'
            ],
            'sensor': [
                'Use descriptive names for sensors',
                'Include unit_of_measurement when applicable',
                'Set appropriate scan_interval for better performance',
                'Group related sensors in the same file',
                'Use unique_id for better entity handling during restarts'
            ]
        }
    
    def analyze_validation_results(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze validation results and provide recommendations.
        
        Args:
            validation_results (Dict[str, Any]): Validation results from ConfigValidator
            
        Returns:
            Dict[str, Any]: Analysis results with recommendations
        """
        analysis = {
            'recommendations': [],
            'best_practices': [],
            'performance_suggestions': [],
            'security_suggestions': [],
            'config_type': validation_results.get('config_type', 'unknown')
        }
        
        # Check validation errors and warnings
        self._analyze_errors_and_warnings(validation_results, analysis)
        
        # Add best practices based on config type
        self._add_best_practices(analysis)
        
        # Add performance suggestions
        self._add_performance_suggestions(validation_results, analysis)
        
        # Add security suggestions
        self._add_security_suggestions(validation_results, analysis)
        
        return analysis
    
    def analyze_yaml_content(self, yaml_content: str, config_type: str) -> Dict[str, Any]:
        """
        Analyze YAML content and provide recommendations.
        
        Args:
            yaml_content (str): YAML content to analyze
            config_type (str): Type of configuration (dashboard, automation, etc.)
            
        Returns:
            Dict[str, Any]: Analysis results with recommendations
        """
        analysis = {
            'recommendations': [],
            'best_practices': [],
            'performance_suggestions': [],
            'security_suggestions': [],
            'config_type': config_type
        }
        
        # Check YAML structure issues
        self._analyze_yaml_structure(yaml_content, analysis)
        
        # Add best practices based on config type
        self._add_best_practices(analysis)
        
        # Check for specific patterns based on config type
        if config_type == 'dashboard':
            self._analyze_dashboard_content(yaml_content, analysis)
        elif config_type == 'automation':
            self._analyze_automation_content(yaml_content, analysis)
        elif config_type == 'script':
            self._analyze_script_content(yaml_content, analysis)
        elif config_type == 'sensor':
            self._analyze_sensor_content(yaml_content, analysis)
        
        return analysis
    
    def _analyze_errors_and_warnings(self, validation_results: Dict[str, Any], analysis: Dict[str, Any]):
        """
        Analyze validation errors and warnings and add recommendations.
        
        Args:
            validation_results (Dict[str, Any]): Validation results
            analysis (Dict[str, Any]): Analysis results to update
        """
        # Process errors
        for error in validation_results.get('errors', []):
            if not error:
                continue
                
            recommendation = self._find_recommendation_for_issue(error)
            if recommendation:
                analysis['recommendations'].append({
                    'issue': error,
                    'recommendation': recommendation['recommendation'],
                    'severity': recommendation['severity']
                })
            else:
                # Generic recommendation for errors without specific match
                analysis['recommendations'].append({
                    'issue': error,
                    'recommendation': 'Fix the error to ensure proper functionality.',
                    'severity': 'high'
                })
        
        # Process warnings
        for warning in validation_results.get('warnings', []):
            if not warning:
                continue
                
            recommendation = self._find_recommendation_for_issue(warning)
            if recommendation:
                analysis['recommendations'].append({
                    'issue': warning,
                    'recommendation': recommendation['recommendation'],
                    'severity': recommendation['severity']
                })
            else:
                # Generic recommendation for warnings without specific match
                analysis['recommendations'].append({
                    'issue': warning,
                    'recommendation': 'Consider addressing this warning for better functionality.',
                    'severity': 'medium'
                })
    
    def _find_recommendation_for_issue(self, issue_text: str) -> Optional[Dict[str, str]]:
        """
        Find a recommendation for a given issue.
        
        Args:
            issue_text (str): Issue text to match
            
        Returns:
            Optional[Dict[str, str]]: Recommendation if found, None otherwise
        """
        for issue_key, issue_info in self.common_issues.items():
            if re.search(issue_info['pattern'], issue_text, re.IGNORECASE):
                return issue_info
        return None
    
    def _add_best_practices(self, analysis: Dict[str, Any]):
        """
        Add best practices based on config type.
        
        Args:
            analysis (Dict[str, Any]): Analysis results to update
        """
        config_type = analysis['config_type']
        if config_type in self.best_practices:
            analysis['best_practices'] = self.best_practices[config_type]
    
    def _add_performance_suggestions(self, validation_results: Dict[str, Any], analysis: Dict[str, Any]):
        """
        Add performance suggestions based on validation results.
        
        Args:
            validation_results (Dict[str, Any]): Validation results
            analysis (Dict[str, Any]): Analysis results to update
        """
        config_type = validation_results.get('config_type', 'unknown')
        
        if config_type == 'dashboard':
            # Check for too many cards in a single view
            if 'dashboard' in validation_results:
                dashboard = validation_results['dashboard']
                for view_idx, view in enumerate(dashboard.get('views', [])):
                    cards = view.get('cards', [])
                    if len(cards) > 15:
                        analysis['performance_suggestions'].append(
                            f"View '{view.get('title', view_idx)}' has {len(cards)} cards, which may impact performance. "
                            "Consider breaking it down into multiple views."
                        )
        
        elif config_type == 'automation':
            # Check for complex templates that might affect performance
            yaml_content = validation_results.get('yaml_content', '')
            if yaml_content:
                template_count = len(re.findall(r'template:', yaml_content))
                if template_count > 5:
                    analysis['performance_suggestions'].append(
                        f"Found {template_count} templates, which may impact performance. "
                        "Consider simplifying or caching template results."
                    )
        
        elif config_type == 'sensor':
            # Check for scan_interval settings
            yaml_content = validation_results.get('yaml_content', '')
            if yaml_content and 'scan_interval' not in yaml_content:
                analysis['performance_suggestions'].append(
                    "Consider setting appropriate scan_interval for sensors to optimize performance."
                )
    
    def _add_security_suggestions(self, validation_results: Dict[str, Any], analysis: Dict[str, Any]):
        """
        Add security suggestions based on validation results.
        
        Args:
            validation_results (Dict[str, Any]): Validation results
            analysis (Dict[str, Any]): Analysis results to update
        """
        yaml_content = validation_results.get('yaml_content', '')
        
        # Check for passwords or tokens in clear text
        if re.search(r'(?:password|token|api_key|secret):\s*[\'"]?[^\'\"\s]+[\'"]?', yaml_content, re.IGNORECASE):
            analysis['security_suggestions'].append(
                "Found possible credentials in clear text. Consider using !secret directive to reference secrets.yaml values."
            )
        
        # Check for exposed external URLs without SSL
        if re.search(r'(?:url|resource):\s*http://(?!localhost|127\.0\.0\.1)', yaml_content, re.IGNORECASE):
            analysis['security_suggestions'].append(
                "Found non-SSL URLs (http://). Consider using https:// for external resources for better security."
            )
        
        # Check for exposed IPs
        if re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b(?<!127\.0\.0\.1)', yaml_content):
            analysis['security_suggestions'].append(
                "Found IP addresses in the configuration. Consider using hostnames or !secret directive instead."
            )
    
    def _analyze_yaml_structure(self, yaml_content: str, analysis: Dict[str, Any]):
        """
        Analyze YAML structure and add recommendations.
        
        Args:
            yaml_content (str): YAML content to analyze
            analysis (Dict[str, Any]): Analysis results to update
        """
        # Check for long lines
        lines = yaml_content.split('\n')
        for i, line in enumerate(lines):
            if len(line) > 120:
                analysis['recommendations'].append({
                    'issue': f"Line {i+1} is too long ({len(line)} characters)",
                    'recommendation': "Break down long lines for better readability.",
                    'severity': 'low'
                })
        
        # Check for inconsistent indentation
        indentations = [len(line) - len(line.lstrip()) for line in lines if line.strip()]
        if indentations:
            indentation_counts = {}
            for indent in indentations:
                if indent % 2 != 0:
                    analysis['recommendations'].append({
                        'issue': "Found indentation that is not a multiple of 2 spaces",
                        'recommendation': "Use consistent indentation (2 spaces is recommended).",
                        'severity': 'medium'
                    })
                    break
                indentation_counts[indent] = indentation_counts.get(indent, 0) + 1
    
    def _analyze_dashboard_content(self, yaml_content: str, analysis: Dict[str, Any]):
        """
        Analyze dashboard content and add recommendations.
        
        Args:
            yaml_content (str): Dashboard YAML content to analyze
            analysis (Dict[str, Any]): Analysis results to update
        """
        try:
            dashboard = yaml.safe_load(yaml_content)
            if not isinstance(dashboard, dict):
                return
            
            # Check for missing theme
            if 'theme' not in dashboard:
                analysis['recommendations'].append({
                    'issue': "Dashboard doesn't specify a theme",
                    'recommendation': "Consider specifying a theme for consistent appearance.",
                    'severity': 'low'
                })
            
            # Check views
            views = dashboard.get('views', [])
            for view_idx, view in enumerate(views):
                if not isinstance(view, dict):
                    continue
                
                # Check for missing icon in view
                if 'icon' not in view and view.get('show_in_sidebar', True):
                    analysis['recommendations'].append({
                        'issue': f"View '{view.get('title', view_idx)}' doesn't have an icon but is shown in sidebar",
                        'recommendation': "Add an icon to the view for better navigation in the sidebar.",
                        'severity': 'low'
                    })
                
                # Check cards in the view
                cards = view.get('cards', [])
                if not cards:
                    analysis['recommendations'].append({
                        'issue': f"View '{view.get('title', view_idx)}' has no cards",
                        'recommendation': "Add cards to the view to provide useful information.",
                        'severity': 'medium'
                    })
                
                # Check for mix of different card types
                card_types = set()
                for card in cards:
                    if isinstance(card, dict) and 'type' in card:
                        card_types.add(card['type'])
                
                if len(card_types) > 5:
                    analysis['recommendations'].append({
                        'issue': f"View '{view.get('title', view_idx)}' has {len(card_types)} different card types",
                        'recommendation': "Consider grouping similar card types together for better organization.",
                        'severity': 'low'
                    })
        
        except Exception as e:
            logger.error(f"Error analyzing dashboard content: {str(e)}")
    
    def _analyze_automation_content(self, yaml_content: str, analysis: Dict[str, Any]):
        """
        Analyze automation content and add recommendations.
        
        Args:
            yaml_content (str): Automation YAML content to analyze
            analysis (Dict[str, Any]): Analysis results to update
        """
        try:
            automation = yaml.safe_load(yaml_content)
            
            # Handle single automation or list of automations
            automations = automation if isinstance(automation, list) else [automation]
            
            for auto_idx, auto in enumerate(automations):
                if not isinstance(auto, dict):
                    continue
                
                # Check for missing ID or alias
                if 'id' not in auto and 'alias' not in auto:
                    analysis['recommendations'].append({
                        'issue': f"Automation {auto_idx} doesn't have an ID or alias",
                        'recommendation': "Add an ID or alias for better identification.",
                        'severity': 'medium'
                    })
                
                # Check for missing mode
                if 'mode' not in auto:
                    analysis['recommendations'].append({
                        'issue': f"Automation '{auto.get('alias', auto.get('id', auto_idx))}' doesn't specify a mode",
                        'recommendation': "Add 'mode: single' to prevent unintended parallel executions.",
                        'severity': 'medium'
                    })
                
                # Check for missing conditions
                if 'condition' not in auto:
                    analysis['recommendations'].append({
                        'issue': f"Automation '{auto.get('alias', auto.get('id', auto_idx))}' has no conditions",
                        'recommendation': "Consider adding conditions to prevent the automation from running unnecessarily.",
                        'severity': 'medium'
                    })
                
                # Check for complex triggers
                triggers = auto.get('trigger', [])
                if isinstance(triggers, list) and len(triggers) > 3:
                    analysis['recommendations'].append({
                        'issue': f"Automation '{auto.get('alias', auto.get('id', auto_idx))}' has {len(triggers)} triggers",
                        'recommendation': "Consider breaking down complex automations with many triggers into separate automations.",
                        'severity': 'low'
                    })
                
                # Check for complex actions
                actions = auto.get('action', [])
                if isinstance(actions, list) and len(actions) > 5:
                    analysis['recommendations'].append({
                        'issue': f"Automation '{auto.get('alias', auto.get('id', auto_idx))}' has {len(actions)} actions",
                        'recommendation': "Consider breaking down complex automations with many actions into separate automations or scripts.",
                        'severity': 'low'
                    })
                
                # Check for missing description
                if 'description' not in auto:
                    analysis['recommendations'].append({
                        'issue': f"Automation '{auto.get('alias', auto.get('id', auto_idx))}' doesn't have a description",
                        'recommendation': "Add a description to document the automation's purpose.",
                        'severity': 'low'
                    })
        
        except Exception as e:
            logger.error(f"Error analyzing automation content: {str(e)}")
    
    def _analyze_script_content(self, yaml_content: str, analysis: Dict[str, Any]):
        """
        Analyze script content and add recommendations.
        
        Args:
            yaml_content (str): Script YAML content to analyze
            analysis (Dict[str, Any]): Analysis results to update
        """
        try:
            script = yaml.safe_load(yaml_content)
            
            if not isinstance(script, dict):
                return
            
            # Check if it's a direct script or a collection of scripts
            if 'sequence' in script:
                # It's a direct script configuration
                self._check_script_config(script, 'script', analysis)
            else:
                # It's a collection of scripts
                for script_name, script_config in script.items():
                    if isinstance(script_config, dict):
                        self._check_script_config(script_config, script_name, analysis)
        
        except Exception as e:
            logger.error(f"Error analyzing script content: {str(e)}")
    
    def _check_script_config(self, script_config: Dict[str, Any], script_name: str, analysis: Dict[str, Any]):
        """
        Check a script configuration and add recommendations.
        
        Args:
            script_config (Dict[str, Any]): Script configuration
            script_name (str): Script name or identifier
            analysis (Dict[str, Any]): Analysis results to update
        """
        # Check for missing fields
        if 'alias' not in script_config:
            analysis['recommendations'].append({
                'issue': f"Script '{script_name}' doesn't have an alias",
                'recommendation': "Add an alias for better identification.",
                'severity': 'low'
            })
        
        # Check for missing timeout
        if 'timeout' not in script_config:
            analysis['recommendations'].append({
                'issue': f"Script '{script_name}' doesn't specify a timeout",
                'recommendation': "Add a timeout to prevent the script from running indefinitely.",
                'severity': 'medium'
            })
        
        # Check for missing description
        if 'description' not in script_config:
            analysis['recommendations'].append({
                'issue': f"Script '{script_name}' doesn't have a description",
                'recommendation': "Add a description to document the script's purpose.",
                'severity': 'low'
            })
        
        # Check for complex sequence
        sequence = script_config.get('sequence', [])
        if isinstance(sequence, list) and len(sequence) > 7:
            analysis['recommendations'].append({
                'issue': f"Script '{script_name}' has a complex sequence with {len(sequence)} steps",
                'recommendation': "Consider breaking down complex scripts into smaller, more focused ones.",
                'severity': 'medium'
            })
    
    def _analyze_sensor_content(self, yaml_content: str, analysis: Dict[str, Any]):
        """
        Analyze sensor content and add recommendations.
        
        Args:
            yaml_content (str): Sensor YAML content to analyze
            analysis (Dict[str, Any]): Analysis results to update
        """
        try:
            sensor = yaml.safe_load(yaml_content)
            
            # Handle single sensor or list of sensors
            sensors = sensor if isinstance(sensor, list) else [sensor]
            
            for sensor_idx, sens in enumerate(sensors):
                if not isinstance(sens, dict):
                    continue
                
                platform = sens.get('platform', '')
                
                # Check for missing scan_interval
                if 'scan_interval' not in sens:
                    analysis['recommendations'].append({
                        'issue': f"Sensor {sensor_idx} (platform: {platform}) doesn't specify a scan_interval",
                        'recommendation': "Add an appropriate scan_interval for better performance.",
                        'severity': 'low'
                    })
                
                # Check for missing unique_id
                sensors_dict = None
                if platform == 'template':
                    sensors_dict = sens.get('sensors', {})
                elif 'name' in sens:
                    sensors_dict = {sens.get('name'): sens}
                
                if sensors_dict:
                    for name, config in sensors_dict.items():
                        if isinstance(config, dict) and 'unique_id' not in config:
                            analysis['recommendations'].append({
                                'issue': f"Sensor '{name}' doesn't have a unique_id",
                                'recommendation': "Add a unique_id for better entity handling during restarts.",
                                'severity': 'medium'
                            })
                
                # Check REST sensors for SSL usage
                if platform == 'rest' and 'resource' in sens:
                    resource = sens['resource']
                    if resource.startswith('http://') and not (
                        resource.startswith('http://localhost') or 
                        resource.startswith('http://127.0.0.1')
                    ):
                        analysis['recommendations'].append({
                            'issue': f"REST sensor {sensor_idx} uses non-SSL URL: {resource}",
                            'recommendation': "Use https:// for external resources for better security.",
                            'severity': 'high'
                        })
        
        except Exception as e:
            logger.error(f"Error analyzing sensor content: {str(e)}")