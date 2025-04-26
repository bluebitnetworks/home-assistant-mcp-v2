"""
Home Assistant Advanced Pattern Discovery.

This module provides advanced algorithms for discovering usage patterns in Home Assistant.
"""

import logging
import numpy as np
from datetime import datetime, timedelta, time
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict

logger = logging.getLogger(__name__)

class PatternDiscovery:
    """Class for discovering patterns in Home Assistant usage data."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the pattern discovery system.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
        """
        self.config = config
        self.min_occurrences = config['automation'].get('min_occurrences', 3)
        self.confidence_threshold = config['automation'].get('confidence_threshold', 0.7)
    
    def discover_daily_patterns(self, entity_history: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Discover daily patterns in entity usage.
        
        Args:
            entity_history (Dict[str, List[Dict[str, Any]]]): Entity history data by entity ID
            
        Returns:
            List[Dict[str, Any]]: Daily patterns detected
        """
        daily_patterns = []
        
        for entity_id, history in entity_history.items():
            # Skip entities with limited history
            if len(history) < self.min_occurrences:
                continue
            
            # Analyze entity domain
            domain = entity_id.split('.')[0]
            
            # Group state changes by day of week and hour
            day_hour_buckets = self._group_by_day_and_hour(history)
            
            # Analyze each day/hour bucket for consistent patterns
            for (day, hour), states in day_hour_buckets.items():
                if len(states) < self.min_occurrences:
                    continue
                
                # Check for consistent states
                counter = defaultdict(int)
                for state in states:
                    counter[state] += 1
                
                # Find most common state and calculate confidence
                if counter:
                    most_common_state = max(counter.items(), key=lambda x: x[1])
                    state_value, count = most_common_state
                    confidence = count / len(states)
                    
                    if confidence >= self.confidence_threshold:
                        pattern = {
                            'type': 'daily',
                            'entity_id': entity_id,
                            'domain': domain,
                            'day_of_week': day,
                            'hour': hour,
                            'state': state_value,
                            'confidence': confidence,
                            'occurrences': count
                        }
                        daily_patterns.append(pattern)
        
        return daily_patterns
    
    def discover_sequence_patterns(self, entity_history: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Discover sequence patterns where multiple entities change in a specific order.
        
        Args:
            entity_history (Dict[str, List[Dict[str, Any]]]): Entity history data by entity ID
            
        Returns:
            List[Dict[str, Any]]: Sequence patterns detected
        """
        # Flatten history entries and sort by timestamp
        all_entries = []
        for entity_id, history in entity_history.items():
            for entry in history:
                if 'last_changed' in entry and 'state' in entry:
                    all_entries.append({
                        'entity_id': entity_id,
                        'timestamp': entry['last_changed'],
                        'state': entry['state'],
                        'domain': entity_id.split('.')[0]
                    })
        
        # Sort entries by timestamp
        all_entries.sort(key=lambda x: x['timestamp'])
        
        # Look for sequences of state changes within a time window
        sequence_patterns = []
        window_size = timedelta(minutes=2)  # Look for sequences within 2 minutes
        
        # Sliding window through the timeline
        for i in range(len(all_entries)):
            start_entry = all_entries[i]
            start_time = datetime.fromisoformat(start_entry['timestamp'].replace('Z', '+00:00'))
            
            # Collect state changes within the window
            sequence = [start_entry]
            for j in range(i + 1, len(all_entries)):
                entry = all_entries[j]
                entry_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                
                if (entry_time - start_time) <= window_size:
                    # Only add if it's a different entity
                    if entry['entity_id'] != start_entry['entity_id']:
                        sequence.append(entry)
                else:
                    # Outside the window, stop
                    break
            
            # Only consider sequences with at least 3 entities
            if len(sequence) >= 3:
                # Create a sequence key
                seq_key = tuple((e['entity_id'], e['state']) for e in sequence)
                
                # Check if we've found this exact sequence before
                if seq_key not in [s.get('sequence_key') for s in sequence_patterns]:
                    # Count occurrences of similar sequences
                    occurrences = self._count_sequence_occurrences(all_entries, sequence)
                    
                    if occurrences >= self.min_occurrences:
                        pattern = {
                            'type': 'sequence',
                            'steps': [
                                {
                                    'entity_id': e['entity_id'],
                                    'state': e['state'],
                                    'domain': e['domain']
                                } for e in sequence
                            ],
                            'sequence_key': seq_key,
                            'confidence': min(1.0, occurrences / 10),  # Scale confidence
                            'occurrences': occurrences
                        }
                        sequence_patterns.append(pattern)
        
        return sequence_patterns
    
    def discover_conditional_patterns(self, entity_history: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Discover conditional patterns where entity states depend on other entity states.
        
        Args:
            entity_history (Dict[str, List[Dict[str, Any]]]): Entity history data by entity ID
            
        Returns:
            List[Dict[str, Any]]: Conditional patterns detected
        """
        conditional_patterns = []
        
        # First, identify potential "condition" entities
        condition_entities = set()
        for entity_id, history in entity_history.items():
            domain = entity_id.split('.')[0]
            # Good candidates for condition entities
            if domain in ['binary_sensor', 'sensor', 'sun', 'weather', 'person', 'device_tracker']:
                condition_entities.add(entity_id)
        
        # For each entity that's not a condition entity, check if its state correlates with condition entities
        for entity_id, history in entity_history.items():
            domain = entity_id.split('.')[0]
            
            # Skip entities that can't be controlled or don't have enough history
            if domain in ['binary_sensor', 'sensor', 'sun', 'weather'] or len(history) < self.min_occurrences:
                continue
            
            # For each condition entity, check for correlations
            for condition_id in condition_entities:
                if condition_id == entity_id:
                    continue
                
                condition_history = entity_history.get(condition_id, [])
                if len(condition_history) < self.min_occurrences:
                    continue
                
                # Find conditional patterns
                correlations = defaultdict(lambda: defaultdict(int))
                
                # Map condition entity states to target entity states
                for condition_entry in condition_history:
                    if 'state' not in condition_entry or 'last_changed' not in condition_entry:
                        continue
                    
                    condition_state = condition_entry['state']
                    condition_time = datetime.fromisoformat(condition_entry['last_changed'].replace('Z', '+00:00'))
                    
                    # Find entity states when condition is active
                    for entry in history:
                        if 'state' not in entry or 'last_changed' not in entry:
                            continue
                        
                        entry_time = datetime.fromisoformat(entry['last_changed'].replace('Z', '+00:00'))
                        
                        # Check if entity state changes within 10 minutes after condition change
                        if 0 <= (entry_time - condition_time).total_seconds() <= 600:
                            correlations[condition_state][entry['state']] += 1
                
                # Analyze correlations
                for condition_state, state_counts in correlations.items():
                    if not state_counts:
                        continue
                    
                    total_count = sum(state_counts.values())
                    if total_count < self.min_occurrences:
                        continue
                    
                    # Find most common target state
                    most_common_state = max(state_counts.items(), key=lambda x: x[1])
                    target_state, count = most_common_state
                    
                    confidence = count / total_count
                    if confidence >= self.confidence_threshold:
                        pattern = {
                            'type': 'conditional',
                            'entity_id': entity_id,
                            'domain': domain,
                            'condition_entity': condition_id,
                            'condition_state': condition_state,
                            'target_state': target_state,
                            'confidence': confidence,
                            'occurrences': count
                        }
                        conditional_patterns.append(pattern)
        
        return conditional_patterns
    
    def discover_periodic_patterns(self, entity_history: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Discover periodic patterns where entities change at regular intervals.
        
        Args:
            entity_history (Dict[str, List[Dict[str, Any]]]): Entity history data by entity ID
            
        Returns:
            List[Dict[str, Any]]: Periodic patterns detected
        """
        periodic_patterns = []
        
        for entity_id, history in entity_history.items():
            domain = entity_id.split('.')[0]
            
            # Skip entities that can't be controlled or don't have enough history
            if domain in ['binary_sensor', 'sensor', 'sun', 'weather'] or len(history) < self.min_occurrences * 2:
                continue
            
            # Extract timestamps for each target state
            state_timestamps = defaultdict(list)
            
            for entry in history:
                if 'state' not in entry or 'last_changed' not in entry:
                    continue
                
                state = entry['state']
                try:
                    timestamp = datetime.fromisoformat(entry['last_changed'].replace('Z', '+00:00'))
                    state_timestamps[state].append(timestamp)
                except (ValueError, TypeError):
                    continue
            
            # Look for periodic patterns for each state
            for state, timestamps in state_timestamps.items():
                if len(timestamps) < self.min_occurrences * 2:
                    continue
                
                # Sort timestamps
                timestamps.sort()
                
                # Calculate intervals between consecutive timestamps
                intervals = [(timestamps[i] - timestamps[i-1]).total_seconds() for i in range(1, len(timestamps))]
                
                # Convert to hours for easier analysis
                interval_hours = [interval / 3600 for interval in intervals]
                
                # Look for consistent intervals
                if interval_hours:
                    avg_interval = sum(interval_hours) / len(interval_hours)
                    std_dev = np.std(interval_hours)
                    
                    # If standard deviation is low, we have a consistent interval
                    if std_dev < avg_interval * 0.3:  # Tolerance of 30%
                        # Round to nearest hour or half hour
                        rounded_interval = round(avg_interval * 2) / 2
                        
                        if rounded_interval >= 1 and rounded_interval <= 24:
                            pattern = {
                                'type': 'periodic',
                                'entity_id': entity_id,
                                'domain': domain,
                                'state': state,
                                'interval_hours': rounded_interval,
                                'confidence': 1.0 - (std_dev / avg_interval),
                                'occurrences': len(timestamps)
                            }
                            periodic_patterns.append(pattern)
        
        return periodic_patterns
    
    def _group_by_day_and_hour(self, history: List[Dict[str, Any]]) -> Dict[Tuple[int, int], List[str]]:
        """
        Group entity history by day of week and hour.
        
        Args:
            history (List[Dict[str, Any]]): Entity history data
            
        Returns:
            Dict[Tuple[int, int], List[str]]: Grouped state data by (day, hour)
        """
        day_hour_buckets = defaultdict(list)
        
        for entry in history:
            if 'last_changed' in entry and 'state' in entry:
                try:
                    timestamp = datetime.fromisoformat(entry['last_changed'].replace('Z', '+00:00'))
                    day_of_week = timestamp.weekday()  # 0=Monday, 6=Sunday
                    hour = timestamp.hour
                    
                    day_hour_buckets[(day_of_week, hour)].append(entry['state'])
                except (ValueError, TypeError):
                    continue
        
        return day_hour_buckets
    
    def _count_sequence_occurrences(self, all_entries: List[Dict[str, Any]], 
                                   sequence: List[Dict[str, Any]]) -> int:
        """
        Count how many times a similar sequence appears in the history.
        
        Args:
            all_entries (List[Dict[str, Any]]): All history entries
            sequence (List[Dict[str, Any]]): Sequence to look for
            
        Returns:
            int: Number of occurrences
        """
        count = 0
        seq_entities = [e['entity_id'] for e in sequence]
        seq_states = [e['state'] for e in sequence]
        
        # Look for similar sequences in the timeline
        window_size = timedelta(minutes=2)
        
        for i in range(len(all_entries)):
            if all_entries[i]['entity_id'] != seq_entities[0]:
                continue
                
            if all_entries[i]['state'] != seq_states[0]:
                continue
            
            # Found potential start of sequence
            start_time = datetime.fromisoformat(all_entries[i]['timestamp'].replace('Z', '+00:00'))
            
            # Check if the rest of the sequence follows
            matched = True
            for j in range(1, len(sequence)):
                found_match = False
                
                # Look for matching entity and state within the time window
                for k in range(i + 1, len(all_entries)):
                    entry_time = datetime.fromisoformat(all_entries[k]['timestamp'].replace('Z', '+00:00'))
                    
                    if (entry_time - start_time) > window_size:
                        break
                    
                    if (all_entries[k]['entity_id'] == seq_entities[j] and
                        all_entries[k]['state'] == seq_states[j]):
                        found_match = True
                        break
                
                if not found_match:
                    matched = False
                    break
            
            if matched:
                count += 1
        
        return count