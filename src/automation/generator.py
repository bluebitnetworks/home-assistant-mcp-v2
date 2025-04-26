"""
Home Assistant Automation Generator.

This module handles analyzing usage patterns and generating automation configurations.
"""

import logging
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)

class AutomationGenerator:
    """Class for generating Home Assistant automations."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the automation generator.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
        """
        self.config = config
        self.suggestion_threshold = config['automation'].get('suggestion_threshold', 3)
        self.max_suggestions = config['automation'].get('max_suggestions', 5)
    
    def analyze_entity_usage(self, history_data) -> List[Dict[str, Any]]:
        """
        Analyze entity usage patterns from history data.
        
        Args:
            history_data: Either a list of history entries or a dictionary with entity_id as keys
            
        Returns:
            List[Dict[str, Any]]: List of potential automation patterns
        """
        patterns = []
        
        # Handle both input formats: list format and dictionary format
        if isinstance(history_data, list):
            # Group history data by entity (legacy format)
            entity_history = defaultdict(list)
            for item in history_data:
                entity_id = item.get('entity_id')
                if entity_id:
                    entity_history[entity_id].append(item)
        elif isinstance(history_data, dict):
            # Dictionary format (already grouped by entity_id)
            entity_history = history_data
        else:
            logger.error(f"Unsupported history_data format: {type(history_data)}")
            return []
        
        # Analyze each entity's history
        for entity_id, history in entity_history.items():
            # Skip entities with too little history
            if len(history) < self.suggestion_threshold:
                continue
            
            # Look for time-based patterns
            time_patterns = self._find_time_patterns(entity_id, history)
            if time_patterns:
                patterns.extend(time_patterns)
            
            # Look for state-based patterns (entity state changes based on other entities)
            state_patterns = self._find_state_patterns(entity_id, history, entity_history)
            if state_patterns:
                patterns.extend(state_patterns)
        
        # Sort patterns by confidence and limit to max_suggestions
        patterns.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        return patterns[:self.max_suggestions]
    
    def _find_time_patterns(self, entity_id: str, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find time-based patterns for an entity.
        
        Args:
            entity_id (str): Entity ID
            history (List[Dict[str, Any]]): Entity history data
            
        Returns:
            List[Dict[str, Any]]: List of time-based patterns
        """
        patterns = []
        
        # Group state changes by time of day
        time_buckets = defaultdict(list)
        for entry in history:
            if 'last_changed' in entry and 'state' in entry:
                try:
                    timestamp = datetime.fromisoformat(entry['last_changed'].replace('Z', '+00:00'))
                    hour = timestamp.hour
                    time_bucket = f"{hour:02d}:00"
                    time_buckets[time_bucket].append(entry)
                except (ValueError, TypeError):
                    continue
        
        # Look for consistent state changes at specific times
        for time_bucket, entries in time_buckets.items():
            if len(entries) >= self.suggestion_threshold:
                # Check if state changes are consistent
                states = [entry['state'] for entry in entries]
                most_common_state = max(set(states), key=states.count)
                confidence = states.count(most_common_state) / len(states)
                
                if confidence >= 0.7:  # At least 70% confidence
                    pattern = {
                        'entity_id': entity_id,
                        'type': 'time',
                        'trigger_time': time_bucket,
                        'action_state': most_common_state,
                        'confidence': confidence,
                        'occurrences': len(entries)
                    }
                    patterns.append(pattern)
        
        return patterns
    
    def _find_state_patterns(self, entity_id: str, history: List[Dict[str, Any]], 
                             all_entity_history: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Find state-based patterns between entities.
        
        Args:
            entity_id (str): Entity ID
            history (List[Dict[str, Any]]): Entity history data
            all_entity_history (Dict[str, List[Dict[str, Any]]]): All entities history data
            
        Returns:
            List[Dict[str, Any]]: List of state-based patterns
        """
        patterns = []
        
        # Skip non-controllable entities (sensors, etc.)
        entity_domain = entity_id.split('.')[0]
        if entity_domain in ['sensor', 'binary_sensor', 'sun', 'weather']:
            return patterns
        
        # Look for correlations with other entities
        for trigger_entity_id, trigger_history in all_entity_history.items():
            # Skip if this is the same entity or not enough history
            if trigger_entity_id == entity_id or len(trigger_history) < self.suggestion_threshold:
                continue
            
            # Skip non-trigger entities
            trigger_domain = trigger_entity_id.split('.')[0]
            if trigger_domain not in ['binary_sensor', 'sensor', 'device_tracker', 'person']:
                continue
            
            # Look for state changes in entity_id that follow state changes in trigger_entity_id
            correlations = []
            for trigger_entry in trigger_history:
                if 'last_changed' not in trigger_entry or 'state' not in trigger_entry:
                    continue
                
                try:
                    trigger_time = datetime.fromisoformat(trigger_entry['last_changed'].replace('Z', '+00:00'))
                    trigger_state = trigger_entry['state']
                    
                    # Look for entity changes within 1 minute after trigger
                    for entry in history:
                        if 'last_changed' not in entry or 'state' not in entry:
                            continue
                        
                        entity_time = datetime.fromisoformat(entry['last_changed'].replace('Z', '+00:00'))
                        time_diff = (entity_time - trigger_time).total_seconds()
                        
                        # If entity changed 0-60 seconds after trigger
                        if 0 <= time_diff <= 60:
                            correlations.append({
                                'trigger_entity': trigger_entity_id,
                                'trigger_state': trigger_state,
                                'action_state': entry['state'],
                                'time_diff': time_diff
                            })
                except (ValueError, TypeError):
                    continue
            
            # If we found consistent correlations
            if len(correlations) >= self.suggestion_threshold:
                # Group by trigger state
                triggers = defaultdict(list)
                for corr in correlations:
                    key = (corr['trigger_entity'], corr['trigger_state'])
                    triggers[key].append(corr['action_state'])
                
                # Check for consistent state changes
                for (trigger_entity, trigger_state), action_states in triggers.items():
                    if len(action_states) >= self.suggestion_threshold:
                        most_common_state = max(set(action_states), key=action_states.count)
                        confidence = action_states.count(most_common_state) / len(action_states)
                        
                        if confidence >= 0.7:  # At least 70% confidence
                            pattern = {
                                'entity_id': entity_id,
                                'type': 'state',
                                'trigger_entity': trigger_entity,
                                'trigger_state': trigger_state,
                                'action_state': most_common_state,
                                'confidence': confidence,
                                'occurrences': len(action_states)
                            }
                            patterns.append(pattern)
        
        return patterns
    
    def generate_automation_yaml(self, pattern: Dict[str, Any]) -> str:
        """
        Generate YAML for an automation based on a detected pattern.
        
        Args:
            pattern (Dict[str, Any]): Pattern detected by analyze_entity_usage
            
        Returns:
            str: Automation YAML
        """
        entity_id = pattern.get('entity_id')
        pattern_type = pattern.get('type')
        
        automation = {
            'id': f"auto_{pattern_type}_{entity_id.replace('.', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'alias': f"Auto-generated {pattern_type} automation for {entity_id}",
            'description': f"Automatically generated {pattern_type}-based automation for {entity_id}",
            'mode': 'single'
        }
        
        # Set up trigger based on pattern type
        if pattern_type == 'time':
            time_parts = pattern.get('trigger_time', '00:00').split(':')
            automation['trigger'] = {
                'platform': 'time',
                'at': pattern.get('trigger_time')
            }
        elif pattern_type == 'state':
            automation['trigger'] = {
                'platform': 'state',
                'entity_id': pattern.get('trigger_entity'),
                'to': pattern.get('trigger_state')
            }
        
        # Set up action based on entity domain
        domain = entity_id.split('.')[0]
        action_state = pattern.get('action_state')
        
        if domain in ['light', 'switch', 'fan', 'cover']:
            service = f"{domain}.turn_on" if action_state == 'on' else f"{domain}.turn_off"
            automation['action'] = {
                'service': service,
                'target': {
                    'entity_id': entity_id
                }
            }
        elif domain == 'climate':
            # For climate entities, we need more information (like temperature)
            automation['action'] = {
                'service': 'climate.set_hvac_mode',
                'target': {
                    'entity_id': entity_id
                },
                'data': {
                    'hvac_mode': action_state
                }
            }
        else:
            # Generic service call for other domains
            automation['action'] = {
                'service': f"{domain}.set_state",
                'target': {
                    'entity_id': entity_id
                },
                'data': {
                    'state': action_state
                }
            }
        
        # Add condition with a time allowance if it's a state-based trigger
        if pattern_type == 'state':
            automation['condition'] = []
        
        # Convert to YAML
        yaml_content = yaml.dump(automation, sort_keys=False, default_flow_style=False)
        return yaml_content