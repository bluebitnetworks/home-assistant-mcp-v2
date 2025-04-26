"""
Home Assistant Automation Suggestion Engine.

This module provides smart automation suggestions based on entity usage patterns.
"""

import logging
import yaml
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict

from src.automation.pattern_discovery import PatternDiscovery
from src.automation.generator import AutomationGenerator

logger = logging.getLogger(__name__)

class SuggestionEngine:
    """Class for generating smart automation suggestions."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the suggestion engine.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
        """
        self.config = config
        self.pattern_discovery = PatternDiscovery(config)
        self.automation_generator = AutomationGenerator(config)
        
        # Suggestion settings
        self.max_suggestions = config['automation'].get('max_suggestions', 5)
        self.min_confidence = config['automation'].get('min_confidence', 0.7)
    
    async def generate_suggestions(self, entity_history: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Generate automation suggestions based on entity history.
        
        Args:
            entity_history (Dict[str, List[Dict[str, Any]]]): Entity history data by entity ID
            
        Returns:
            List[Dict[str, Any]]: List of automation suggestions
        """
        suggestions = []
        
        # Discover patterns
        daily_patterns = self.pattern_discovery.discover_daily_patterns(entity_history)
        sequence_patterns = self.pattern_discovery.discover_sequence_patterns(entity_history)
        conditional_patterns = self.pattern_discovery.discover_conditional_patterns(entity_history)
        periodic_patterns = self.pattern_discovery.discover_periodic_patterns(entity_history)
        
        # Convert patterns to suggestions
        suggestions.extend(self._convert_daily_patterns(daily_patterns))
        suggestions.extend(self._convert_sequence_patterns(sequence_patterns))
        suggestions.extend(self._convert_conditional_patterns(conditional_patterns))
        suggestions.extend(self._convert_periodic_patterns(periodic_patterns))
        
        # Sort by confidence and limit
        suggestions.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        # Filter by minimum confidence
        suggestions = [s for s in suggestions if s.get('confidence', 0) >= self.min_confidence]
        
        return suggestions[:self.max_suggestions]
    
    def _convert_daily_patterns(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert daily patterns to suggestions.
        
        Args:
            patterns (List[Dict[str, Any]]): Daily patterns
            
        Returns:
            List[Dict[str, Any]]: Suggestions based on daily patterns
        """
        suggestions = []
        
        for pattern in patterns:
            entity_id = pattern.get('entity_id')
            domain = pattern.get('domain')
            state = pattern.get('state')
            day = pattern.get('day_of_week')
            hour = pattern.get('hour')
            confidence = pattern.get('confidence', 0)
            
            # Skip if confidence is too low
            if confidence < self.min_confidence:
                continue
            
            # Create a suggestion
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_name = day_names[day] if 0 <= day <= 6 else 'day'
            
            suggestion = {
                'id': f"daily_{entity_id.replace('.', '_')}_{day}_{hour}",
                'type': 'daily',
                'title': f"Turn {state} {entity_id} every {day_name} at {hour}:00",
                'description': (
                    f"This automation will turn {state} the {entity_id} every {day_name} "
                    f"at {hour}:00. This pattern was detected with {confidence:.0%} confidence."
                ),
                'confidence': confidence,
                'entities': [entity_id],
                'pattern': pattern,
                'yaml': self._generate_daily_automation_yaml(pattern)
            }
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _convert_sequence_patterns(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert sequence patterns to suggestions.
        
        Args:
            patterns (List[Dict[str, Any]]): Sequence patterns
            
        Returns:
            List[Dict[str, Any]]: Suggestions based on sequence patterns
        """
        suggestions = []
        
        for pattern in patterns:
            steps = pattern.get('steps', [])
            confidence = pattern.get('confidence', 0)
            
            # Skip if confidence is too low or not enough steps
            if confidence < self.min_confidence or len(steps) < 2:
                continue
            
            # Create a suggestion
            first_entity = steps[0].get('entity_id', '')
            entities = [step.get('entity_id', '') for step in steps]
            
            suggestion = {
                'id': f"sequence_{first_entity.replace('.', '_')}_{len(steps)}",
                'type': 'sequence',
                'title': f"Create a scene with {len(steps)} devices",
                'description': (
                    f"This automation will create a scene that sets {len(steps)} devices to specific states. "
                    f"The scene starts with {first_entity} and includes {', '.join(entities[1:])}. "
                    f"This pattern was detected with {confidence:.0%} confidence."
                ),
                'confidence': confidence,
                'entities': entities,
                'pattern': pattern,
                'yaml': self._generate_sequence_automation_yaml(pattern)
            }
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _convert_conditional_patterns(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert conditional patterns to suggestions.
        
        Args:
            patterns (List[Dict[str, Any]]): Conditional patterns
            
        Returns:
            List[Dict[str, Any]]: Suggestions based on conditional patterns
        """
        suggestions = []
        
        for pattern in patterns:
            entity_id = pattern.get('entity_id')
            condition_entity = pattern.get('condition_entity')
            condition_state = pattern.get('condition_state')
            target_state = pattern.get('target_state')
            confidence = pattern.get('confidence', 0)
            
            # Skip if confidence is too low
            if confidence < self.min_confidence:
                continue
            
            # Create a suggestion
            suggestion = {
                'id': f"condition_{entity_id.replace('.', '_')}_{condition_entity.replace('.', '_')}",
                'type': 'conditional',
                'title': f"Turn {target_state} {entity_id} when {condition_entity} is {condition_state}",
                'description': (
                    f"This automation will turn {target_state} the {entity_id} when {condition_entity} "
                    f"changes to {condition_state}. This pattern was detected with {confidence:.0%} confidence."
                ),
                'confidence': confidence,
                'entities': [entity_id, condition_entity],
                'pattern': pattern,
                'yaml': self._generate_conditional_automation_yaml(pattern)
            }
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _convert_periodic_patterns(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert periodic patterns to suggestions.
        
        Args:
            patterns (List[Dict[str, Any]]): Periodic patterns
            
        Returns:
            List[Dict[str, Any]]: Suggestions based on periodic patterns
        """
        suggestions = []
        
        for pattern in patterns:
            entity_id = pattern.get('entity_id')
            interval_hours = pattern.get('interval_hours')
            state = pattern.get('state')
            confidence = pattern.get('confidence', 0)
            
            # Skip if confidence is too low
            if confidence < self.min_confidence:
                continue
            
            # Create a suggestion
            interval_str = f"{interval_hours:.1f}".rstrip('0').rstrip('.') if interval_hours else "0"
            
            suggestion = {
                'id': f"periodic_{entity_id.replace('.', '_')}_{interval_str.replace('.', '_')}",
                'type': 'periodic',
                'title': f"Turn {state} {entity_id} every {interval_str} hours",
                'description': (
                    f"This automation will turn {state} the {entity_id} every {interval_str} hours. "
                    f"This pattern was detected with {confidence:.0%} confidence."
                ),
                'confidence': confidence,
                'entities': [entity_id],
                'pattern': pattern,
                'yaml': self._generate_periodic_automation_yaml(pattern)
            }
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_daily_automation_yaml(self, pattern: Dict[str, Any]) -> str:
        """
        Generate YAML for a daily automation.
        
        Args:
            pattern (Dict[str, Any]): Daily pattern
            
        Returns:
            str: Automation YAML
        """
        entity_id = pattern.get('entity_id')
        domain = pattern.get('domain')
        state = pattern.get('state')
        day = pattern.get('day_of_week')
        hour = pattern.get('hour')
        
        # Create a friendly name for the automation
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_name = day_names[day] if 0 <= day <= 6 else 'day'
        
        # Format the time with leading zero
        time_str = f"{hour:02d}:00:00"
        
        # Automation ID and alias
        auto_id = f"daily_{entity_id.replace('.', '_')}_{day}_{hour}"
        alias = f"Turn {state} {entity_id} on {day_name} at {hour}:00"
        
        # Create the automation
        automation = {
            'id': auto_id,
            'alias': alias,
            'description': f"Automatically turn {state} the {entity_id} every {day_name} at {hour}:00",
            'trigger': {
                'platform': 'time',
                'at': time_str,
                'weekday': [day + 1]  # Home Assistant uses 1-7 for Mon-Sun
            },
            'action': {}
        }
        
        # Set the action based on domain and state
        if domain in ['light', 'switch', 'fan', 'cover']:
            service = f"{domain}.turn_on" if state == 'on' else f"{domain}.turn_off"
            automation['action'] = {
                'service': service,
                'target': {
                    'entity_id': entity_id
                }
            }
        elif domain == 'climate':
            automation['action'] = {
                'service': 'climate.set_hvac_mode',
                'target': {
                    'entity_id': entity_id
                },
                'data': {
                    'hvac_mode': state
                }
            }
        else:
            # Generic service call
            automation['action'] = {
                'service': f"{domain}.set_state",
                'target': {
                    'entity_id': entity_id
                },
                'data': {
                    'state': state
                }
            }
        
        # Convert to YAML
        return yaml.dump(automation, sort_keys=False, default_flow_style=False)
    
    def _generate_sequence_automation_yaml(self, pattern: Dict[str, Any]) -> str:
        """
        Generate YAML for a sequence automation.
        
        Args:
            pattern (Dict[str, Any]): Sequence pattern
            
        Returns:
            str: Automation YAML
        """
        steps = pattern.get('steps', [])
        first_entity = steps[0].get('entity_id', '') if steps else ''
        
        # Create a friendly name for the automation
        auto_id = f"sequence_{first_entity.replace('.', '_')}_{len(steps)}"
        alias = f"Sequence: {first_entity} and {len(steps)-1} other devices"
        
        # Build a list of actions
        actions = []
        for step in steps:
            entity_id = step.get('entity_id', '')
            state = step.get('state', '')
            domain = step.get('domain', '')
            
            if domain in ['light', 'switch', 'fan', 'cover']:
                service = f"{domain}.turn_on" if state == 'on' else f"{domain}.turn_off"
                actions.append({
                    'service': service,
                    'target': {
                        'entity_id': entity_id
                    }
                })
            elif domain == 'climate':
                actions.append({
                    'service': 'climate.set_hvac_mode',
                    'target': {
                        'entity_id': entity_id
                    },
                    'data': {
                        'hvac_mode': state
                    }
                })
            else:
                # Generic service call
                actions.append({
                    'service': f"{domain}.set_state",
                    'target': {
                        'entity_id': entity_id
                    },
                    'data': {
                        'state': state
                    }
                })
        
        # Create the automation
        automation = {
            'id': auto_id,
            'alias': alias,
            'description': f"Automation to control {len(steps)} devices in sequence",
            'trigger': {
                'platform': 'device',
                'domain': 'mqtt',
                'device_id': '',
                'type': 'button_short_press',
                'subtype': '1'
            },
            'mode': 'single',
            'action': actions
        }
        
        # Add a note to customize the trigger
        automation['description'] += "\nNote: This automation uses a placeholder MQTT button trigger. You should customize this."
        
        # Convert to YAML
        return yaml.dump(automation, sort_keys=False, default_flow_style=False)
    
    def _generate_conditional_automation_yaml(self, pattern: Dict[str, Any]) -> str:
        """
        Generate YAML for a conditional automation.
        
        Args:
            pattern (Dict[str, Any]): Conditional pattern
            
        Returns:
            str: Automation YAML
        """
        entity_id = pattern.get('entity_id')
        domain = pattern.get('domain')
        condition_entity = pattern.get('condition_entity')
        condition_state = pattern.get('condition_state')
        target_state = pattern.get('target_state')
        
        # Create a friendly name for the automation
        auto_id = f"condition_{entity_id.replace('.', '_')}_{condition_entity.replace('.', '_')}"
        alias = f"Control {entity_id} based on {condition_entity}"
        
        # Create the automation
        automation = {
            'id': auto_id,
            'alias': alias,
            'description': f"Turn {target_state} the {entity_id} when {condition_entity} changes to {condition_state}",
            'trigger': {
                'platform': 'state',
                'entity_id': condition_entity,
                'to': condition_state
            },
            'mode': 'single',
            'action': {}
        }
        
        # Set the action based on domain and state
        if domain in ['light', 'switch', 'fan', 'cover']:
            service = f"{domain}.turn_on" if target_state == 'on' else f"{domain}.turn_off"
            automation['action'] = {
                'service': service,
                'target': {
                    'entity_id': entity_id
                }
            }
        elif domain == 'climate':
            automation['action'] = {
                'service': 'climate.set_hvac_mode',
                'target': {
                    'entity_id': entity_id
                },
                'data': {
                    'hvac_mode': target_state
                }
            }
        else:
            # Generic service call
            automation['action'] = {
                'service': f"{domain}.set_state",
                'target': {
                    'entity_id': entity_id
                },
                'data': {
                    'state': target_state
                }
            }
        
        # Convert to YAML
        return yaml.dump(automation, sort_keys=False, default_flow_style=False)
    
    def _generate_periodic_automation_yaml(self, pattern: Dict[str, Any]) -> str:
        """
        Generate YAML for a periodic automation.
        
        Args:
            pattern (Dict[str, Any]): Periodic pattern
            
        Returns:
            str: Automation YAML
        """
        entity_id = pattern.get('entity_id')
        domain = pattern.get('domain')
        interval_hours = pattern.get('interval_hours')
        state = pattern.get('state')
        
        # Format interval for display
        interval_str = f"{interval_hours:.1f}".rstrip('0').rstrip('.') if interval_hours else "0"
        
        # Create a friendly name for the automation
        auto_id = f"periodic_{entity_id.replace('.', '_')}_{interval_str.replace('.', '_')}"
        alias = f"Control {entity_id} every {interval_str} hours"
        
        # Convert hours to minutes for timer
        interval_minutes = int(interval_hours * 60) if interval_hours else 60
        
        # Create the automation
        automation = {
            'id': auto_id,
            'alias': alias,
            'description': f"Turn {state} the {entity_id} every {interval_str} hours",
            'trigger': {
                'platform': 'time_pattern',
                'hours': f"/{interval_str}"
            },
            'mode': 'single',
            'action': {}
        }
        
        # Set the action based on domain and state
        if domain in ['light', 'switch', 'fan', 'cover']:
            service = f"{domain}.turn_on" if state == 'on' else f"{domain}.turn_off"
            automation['action'] = {
                'service': service,
                'target': {
                    'entity_id': entity_id
                }
            }
        elif domain == 'climate':
            automation['action'] = {
                'service': 'climate.set_hvac_mode',
                'target': {
                    'entity_id': entity_id
                },
                'data': {
                    'hvac_mode': state
                }
            }
        else:
            # Generic service call
            automation['action'] = {
                'service': f"{domain}.set_state",
                'target': {
                    'entity_id': entity_id
                },
                'data': {
                    'state': state
                }
            }
        
        # Convert to YAML
        return yaml.dump(automation, sort_keys=False, default_flow_style=False)
    
    def get_suggestion_categories(self, suggestions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group suggestions by category.
        
        Args:
            suggestions (List[Dict[str, Any]]): List of suggestions
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Suggestions grouped by category
        """
        categories = {
            'daily': [],
            'conditional': [],
            'sequence': [],
            'periodic': []
        }
        
        for suggestion in suggestions:
            suggestion_type = suggestion.get('type', 'unknown')
            if suggestion_type in categories:
                categories[suggestion_type].append(suggestion)
        
        return categories
    
    def get_suggestions_by_entity(self, suggestions: List[Dict[str, Any]], entity_id: str) -> List[Dict[str, Any]]:
        """
        Get suggestions related to a specific entity.
        
        Args:
            suggestions (List[Dict[str, Any]]): List of suggestions
            entity_id (str): Entity ID
            
        Returns:
            List[Dict[str, Any]]: Suggestions related to the entity
        """
        entity_suggestions = []
        
        for suggestion in suggestions:
            entities = suggestion.get('entities', [])
            if entity_id in entities:
                entity_suggestions.append(suggestion)
        
        return entity_suggestions