"""
Home Assistant Connection Utilities.

This module provides utility functions for interacting with Home Assistant.
"""

import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple

from src.connection.api import HomeAssistantAPI

logger = logging.getLogger(__name__)

async def discover_entities(api: HomeAssistantAPI) -> Dict[str, List[Dict[str, Any]]]:
    """
    Discover and categorize Home Assistant entities.
    
    Args:
        api (HomeAssistantAPI): Home Assistant API client
        
    Returns:
        Dict[str, List[Dict[str, Any]]]: Entities categorized by type
    """
    all_entities = await api.get_states()
    
    # Categorize entities by domain
    categorized = {}
    
    for entity in all_entities:
        entity_id = entity.get('entity_id', '')
        if not entity_id:
            continue
            
        domain = entity_id.split('.')[0]
        
        if domain not in categorized:
            categorized[domain] = []
            
        categorized[domain].append(entity)
    
    return categorized

async def get_entity_groups(api: HomeAssistantAPI) -> Dict[str, List[str]]:
    """
    Get entity groups (areas and domains).
    
    Args:
        api (HomeAssistantAPI): Home Assistant API client
        
    Returns:
        Dict[str, List[str]]: Entity groups with member entity IDs
    """
    categories = await api.get_entities_by_category()
    entity_groups = {}
    
    # Process areas
    for area, domains in categories.items():
        area_key = f"area.{area.lower().replace(' ', '_')}"
        entity_groups[area_key] = []
        
        # Add all entities in this area
        for domain_entities in domains.values():
            entity_groups[area_key].extend(domain_entities)
        
        # Also create domain-specific groups within areas
        for domain, domain_entities in domains.items():
            domain_key = f"area.{area.lower().replace(' ', '_')}_{domain}"
            entity_groups[domain_key] = domain_entities
    
    # Create domain-based groups (all entities of a type)
    domain_entities = {}
    for area_data in categories.values():
        for domain, entities in area_data.items():
            if domain not in domain_entities:
                domain_entities[domain] = []
            domain_entities[domain].extend(entities)
    
    # Add domain groups to the result
    for domain, entities in domain_entities.items():
        entity_groups[f"domain.{domain}"] = entities
    
    return entity_groups

async def detect_entity_relationships(api: HomeAssistantAPI) -> Dict[str, List[str]]:
    """
    Detect relationships between entities based on history data.
    
    Args:
        api (HomeAssistantAPI): Home Assistant API client
        
    Returns:
        Dict[str, List[str]]: Dictionary of related entities
    """
    # Get all entities
    entities = await api.get_states()
    entity_ids = [e.get('entity_id') for e in entities if e.get('entity_id')]
    
    # Get history for the last day
    start_time = datetime.now() - timedelta(days=1)
    history_data = await api.get_history(entity_ids, start_time)
    
    # Analyze state changes to find correlations
    correlations = {}
    
    # Create a timeline of state changes
    timeline = []
    
    for entity_history in history_data:
        if not entity_history:
            continue
            
        entity_id = entity_history[0].get('entity_id')
        if not entity_id:
            continue
            
        for state_item in entity_history:
            if 'last_changed' in state_item and 'state' in state_item:
                try:
                    timestamp = datetime.fromisoformat(state_item['last_changed'].replace('Z', '+00:00'))
                    timeline.append({
                        'timestamp': timestamp,
                        'entity_id': entity_id,
                        'state': state_item['state']
                    })
                except (ValueError, TypeError):
                    continue
    
    # Sort timeline by timestamp
    timeline.sort(key=lambda x: x['timestamp'])
    
    # Look for state changes that happen close to each other
    related_entities = {}
    
    for i, event in enumerate(timeline):
        # Skip the last event
        if i >= len(timeline) - 1:
            continue
            
        entity_id = event['entity_id']
        timestamp = event['timestamp']
        
        # Look for events that occur within 60 seconds after this one
        for j in range(i + 1, len(timeline)):
            next_event = timeline[j]
            next_timestamp = next_event['timestamp']
            next_entity_id = next_event['entity_id']
            
            # Skip if it's the same entity
            if next_entity_id == entity_id:
                continue
                
            # Check if the events are within 60 seconds of each other
            time_diff = (next_timestamp - timestamp).total_seconds()
            if 0 <= time_diff <= 60:
                # Record the relationship
                if entity_id not in related_entities:
                    related_entities[entity_id] = set()
                if next_entity_id not in related_entities:
                    related_entities[next_entity_id] = set()
                    
                related_entities[entity_id].add(next_entity_id)
                related_entities[next_entity_id].add(entity_id)
            elif time_diff > 60:
                # Stop looking if we're beyond the time window
                break
    
    # Convert sets to lists for JSON serialization
    result = {entity_id: list(related) for entity_id, related in related_entities.items()}
    return result

async def get_entity_hierarchy(api: HomeAssistantAPI) -> Dict[str, Any]:
    """
    Build a hierarchical representation of entities by area and domain.
    
    Args:
        api (HomeAssistantAPI): Home Assistant API client
        
    Returns:
        Dict[str, Any]: Hierarchical entity structure
    """
    # Get entity categories
    categories = await api.get_entities_by_category()
    
    # Get states for all entities
    all_states = {entity['entity_id']: entity for entity in await api.get_states()}
    
    # Build the hierarchy
    hierarchy = {
        'areas': []
    }
    
    for area_name, domains in categories.items():
        area = {
            'name': area_name,
            'domains': []
        }
        
        for domain, entity_ids in domains.items():
            domain_info = {
                'name': domain,
                'entities': []
            }
            
            for entity_id in entity_ids:
                entity_info = {
                    'entity_id': entity_id,
                    'name': all_states.get(entity_id, {}).get('attributes', {}).get('friendly_name', entity_id),
                    'state': all_states.get(entity_id, {}).get('state', 'unknown')
                }
                domain_info['entities'].append(entity_info)
            
            area['domains'].append(domain_info)
        
        hierarchy['areas'].append(area)
    
    return hierarchy

def get_entity_hierarchy_sync(api: HomeAssistantAPI) -> Dict[str, Any]:
    """
    Synchronous version of get_entity_hierarchy.
    
    Args:
        api (HomeAssistantAPI): Home Assistant API client
        
    Returns:
        Dict[str, Any]: Hierarchical entity structure
    """
    # This is a simplification that doesn't use areas since we can't do async
    all_entities = api.get_entities_sync()
    
    # Group entities by domain
    domains = {}
    for entity in all_entities:
        entity_id = entity.get('entity_id', '')
        if not entity_id:
            continue
            
        domain = entity_id.split('.')[0]
        
        if domain not in domains:
            domains[domain] = []
            
        entity_info = {
            'entity_id': entity_id,
            'name': entity.get('attributes', {}).get('friendly_name', entity_id),
            'state': entity.get('state', 'unknown')
        }
        domains[domain].append(entity_info)
    
    # Build a simpler hierarchy without areas
    hierarchy = {
        'domains': [
            {
                'name': domain,
                'entities': entities
            } for domain, entities in domains.items()
        ]
    }
    
    return hierarchy

def get_domain_from_entity(entity_id: str) -> str:
    """
    Extract the domain from an entity ID.
    
    Args:
        entity_id (str): Entity ID
        
    Returns:
        str: Domain
    """
    return entity_id.split('.')[0]

def get_service_for_action(domain: str, action: str) -> Tuple[str, str]:
    """
    Map a human-readable action to a service call.
    
    Args:
        domain (str): Entity domain
        action (str): Action to perform
        
    Returns:
        Tuple[str, str]: (service_domain, service_name)
    """
    # Handle common actions
    if action in ['turn_on', 'on', 'enable', 'start']:
        return domain, 'turn_on'
    elif action in ['turn_off', 'off', 'disable', 'stop']:
        return domain, 'turn_off'
    elif action in ['toggle']:
        return domain, 'toggle'
    
    # Domain-specific actions
    if domain == 'light':
        if action in ['dim', 'brightness']:
            return domain, 'turn_on'  # Will need brightness parameter
        elif action in ['color', 'set_color']:
            return domain, 'turn_on'  # Will need rgb_color parameter
    elif domain == 'cover':
        if action in ['open']:
            return domain, 'open_cover'
        elif action in ['close']:
            return domain, 'close_cover'
    elif domain == 'climate':
        if action in ['heat', 'set_temperature']:
            return domain, 'set_temperature'
        elif action in ['set_mode']:
            return domain, 'set_hvac_mode'
    elif domain == 'media_player':
        if action in ['play']:
            return domain, 'media_play'
        elif action in ['pause']:
            return domain, 'media_pause'
        elif action in ['volume', 'set_volume']:
            return domain, 'volume_set'
    
    # Default to just using the action as the service name
    return domain, action