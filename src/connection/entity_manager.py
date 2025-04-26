"""
Home Assistant Entity Manager.

This module provides a high-level interface for managing Home Assistant entities.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from datetime import datetime, timedelta

from src.connection.api import HomeAssistantAPI
from src.connection.utils import get_domain_from_entity, get_service_for_action

logger = logging.getLogger(__name__)

class EntityManager:
    """Class for managing Home Assistant entities."""
    
    def __init__(self, api: HomeAssistantAPI):
        """
        Initialize the entity manager.
        
        Args:
            api (HomeAssistantAPI): Home Assistant API client
        """
        self.api = api
        self._entity_cache = {}
        self._entity_capabilities = {}
        self._last_update = None
    
    async def refresh_entities(self) -> None:
        """
        Refresh the cached entity states.
        """
        try:
            entities = await self.api.get_states()
            
            # Update the cache
            self._entity_cache = {entity['entity_id']: entity for entity in entities}
            self._last_update = datetime.now()
            
            logger.info(f"Refreshed {len(entities)} entities")
        except Exception as e:
            logger.error(f"Failed to refresh entities: {str(e)}")
    
    def refresh_entities_sync(self) -> None:
        """
        Synchronous version of refresh_entities.
        """
        try:
            entities = self.api.get_entities_sync()
            
            # Update the cache
            self._entity_cache = {entity['entity_id']: entity for entity in entities}
            self._last_update = datetime.now()
            
            logger.info(f"Refreshed {len(entities)} entities")
        except Exception as e:
            logger.error(f"Failed to refresh entities: {str(e)}")
    
    async def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific entity from the cache or fetch from API if not cached.
        
        Args:
            entity_id (str): Entity ID to get
            
        Returns:
            Optional[Dict[str, Any]]: Entity state or None if not found
        """
        # Check if we need to refresh the cache
        if not self._entity_cache or self._last_update is None or \
           (datetime.now() - self._last_update) > timedelta(minutes=1):
            await self.refresh_entities()
        
        # Try to get from cache
        if entity_id in self._entity_cache:
            return self._entity_cache[entity_id]
        
        # If not in cache, fetch directly
        entity = await self.api.get_entity_state(entity_id)
        if entity:
            self._entity_cache[entity_id] = entity
            return entity
        
        return None
    
    def get_entity_sync(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Synchronous version of get_entity.
        
        Args:
            entity_id (str): Entity ID to get
            
        Returns:
            Optional[Dict[str, Any]]: Entity state or None if not found
        """
        # Check if we need to refresh the cache
        if not self._entity_cache or self._last_update is None or \
           (datetime.now() - self._last_update) > timedelta(minutes=1):
            self.refresh_entities_sync()
        
        # Try to get from cache
        if entity_id in self._entity_cache:
            return self._entity_cache[entity_id]
        
        # If not in cache, fetch directly
        entity = self.api.get_entity_state_sync(entity_id)
        if entity:
            self._entity_cache[entity_id] = entity
            return entity
        
        return None
    
    async def get_all_entities(self) -> List[Dict[str, Any]]:
        """
        Get all entities, refreshing cache if needed.
        
        Returns:
            List[Dict[str, Any]]: List of all entities
        """
        # Check if we need to refresh the cache
        if not self._entity_cache or self._last_update is None or \
           (datetime.now() - self._last_update) > timedelta(minutes=1):
            await self.refresh_entities()
        
        return list(self._entity_cache.values())
    
    def get_all_entities_sync(self) -> List[Dict[str, Any]]:
        """
        Synchronous version of get_all_entities.
        
        Returns:
            List[Dict[str, Any]]: List of all entities
        """
        # Check if we need to refresh the cache
        if not self._entity_cache or self._last_update is None or \
           (datetime.now() - self._last_update) > timedelta(minutes=1):
            self.refresh_entities_sync()
        
        return list(self._entity_cache.values())
    
    async def get_entities_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """
        Get all entities of a specific domain.
        
        Args:
            domain (str): Domain to filter by
            
        Returns:
            List[Dict[str, Any]]: List of entities in the domain
        """
        entities = await self.get_all_entities()
        return [e for e in entities if get_domain_from_entity(e['entity_id']) == domain]
    
    def get_entities_by_domain_sync(self, domain: str) -> List[Dict[str, Any]]:
        """
        Synchronous version of get_entities_by_domain.
        
        Args:
            domain (str): Domain to filter by
            
        Returns:
            List[Dict[str, Any]]: List of entities in the domain
        """
        entities = self.get_all_entities_sync()
        return [e for e in entities if get_domain_from_entity(e['entity_id']) == domain]
    
    async def get_entity_state(self, entity_id: str) -> Optional[str]:
        """
        Get the state value of an entity.
        
        Args:
            entity_id (str): Entity ID to get state for
            
        Returns:
            Optional[str]: Entity state value or None if not found
        """
        entity = await self.get_entity(entity_id)
        if entity and 'state' in entity:
            return entity['state']
        return None
    
    def get_entity_state_sync(self, entity_id: str) -> Optional[str]:
        """
        Synchronous version of get_entity_state.
        
        Args:
            entity_id (str): Entity ID to get state for
            
        Returns:
            Optional[str]: Entity state value or None if not found
        """
        entity = self.get_entity_sync(entity_id)
        if entity and 'state' in entity:
            return entity['state']
        return None
    
    async def get_entity_attributes(self, entity_id: str) -> Dict[str, Any]:
        """
        Get the attributes of an entity.
        
        Args:
            entity_id (str): Entity ID to get attributes for
            
        Returns:
            Dict[str, Any]: Entity attributes or empty dict if not found
        """
        entity = await self.get_entity(entity_id)
        if entity and 'attributes' in entity:
            return entity['attributes']
        return {}
    
    def get_entity_attributes_sync(self, entity_id: str) -> Dict[str, Any]:
        """
        Synchronous version of get_entity_attributes.
        
        Args:
            entity_id (str): Entity ID to get attributes for
            
        Returns:
            Dict[str, Any]: Entity attributes or empty dict if not found
        """
        entity = self.get_entity_sync(entity_id)
        if entity and 'attributes' in entity:
            return entity['attributes']
        return {}
    
    async def get_entity_name(self, entity_id: str) -> str:
        """
        Get the friendly name of an entity.
        
        Args:
            entity_id (str): Entity ID to get name for
            
        Returns:
            str: Friendly name or entity_id if not found
        """
        attributes = await self.get_entity_attributes(entity_id)
        return attributes.get('friendly_name', entity_id)
    
    def get_entity_name_sync(self, entity_id: str) -> str:
        """
        Synchronous version of get_entity_name.
        
        Args:
            entity_id (str): Entity ID to get name for
            
        Returns:
            str: Friendly name or entity_id if not found
        """
        attributes = self.get_entity_attributes_sync(entity_id)
        return attributes.get('friendly_name', entity_id)
    
    async def control_entity(self, entity_id: str, action: str, 
                           parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Control an entity with a high-level action.
        
        Args:
            entity_id (str): Entity ID to control
            action (str): Action to perform (e.g., 'turn_on', 'turn_off', 'toggle')
            parameters (Optional[Dict[str, Any]]): Additional parameters for the action
            
        Returns:
            bool: True if successful, False otherwise
        """
        domain = get_domain_from_entity(entity_id)
        service_domain, service = get_service_for_action(domain, action)
        
        # Prepare service data
        service_data = {'entity_id': entity_id}
        if parameters:
            service_data.update(parameters)
        
        # Call the service
        result = await self.api.call_service(service_domain, service, service_data)
        
        # Update the cache with the new state if successful
        if result:
            # Wait a short time for the state to update
            await asyncio.sleep(0.5)
            # Refresh the entity
            entity = await self.api.get_entity_state(entity_id)
            if entity:
                self._entity_cache[entity_id] = entity
        
        return result
    
    def control_entity_sync(self, entity_id: str, action: str, 
                          parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Synchronous version of control_entity.
        
        Args:
            entity_id (str): Entity ID to control
            action (str): Action to perform (e.g., 'turn_on', 'turn_off', 'toggle')
            parameters (Optional[Dict[str, Any]]): Additional parameters for the action
            
        Returns:
            bool: True if successful, False otherwise
        """
        domain = get_domain_from_entity(entity_id)
        service_domain, service = get_service_for_action(domain, action)
        
        # Prepare service data
        service_data = {'entity_id': entity_id}
        if parameters:
            service_data.update(parameters)
        
        # Call the service
        result = self.api.call_service_sync(service_domain, service, service_data)
        
        # Update the cache with the new state if successful
        if result:
            # Wait a short time for the state to update
            import time
            time.sleep(0.5)
            # Refresh the entity
            entity = self.api.get_entity_state_sync(entity_id)
            if entity:
                self._entity_cache[entity_id] = entity
        
        return result
    
    async def search_entities(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for entities by name or ID.
        
        Args:
            query (str): Search query
            
        Returns:
            List[Dict[str, Any]]: List of matching entities
        """
        entities = await self.get_all_entities()
        query = query.lower()
        
        results = []
        for entity in entities:
            entity_id = entity['entity_id'].lower()
            friendly_name = entity.get('attributes', {}).get('friendly_name', '').lower()
            
            if query in entity_id or query in friendly_name:
                results.append(entity)
        
        return results
    
    def search_entities_sync(self, query: str) -> List[Dict[str, Any]]:
        """
        Synchronous version of search_entities.
        
        Args:
            query (str): Search query
            
        Returns:
            List[Dict[str, Any]]: List of matching entities
        """
        entities = self.get_all_entities_sync()
        query = query.lower()
        
        results = []
        for entity in entities:
            entity_id = entity['entity_id'].lower()
            friendly_name = entity.get('attributes', {}).get('friendly_name', '').lower()
            
            if query in entity_id or query in friendly_name:
                results.append(entity)
        
        return results
    
    async def get_entity_capability(self, entity_id: str) -> Dict[str, Any]:
        """
        Get the capabilities of an entity.
        
        Args:
            entity_id (str): Entity ID to get capabilities for
            
        Returns:
            Dict[str, Any]: Entity capabilities
        """
        # Check if we have cached capabilities
        if entity_id in self._entity_capabilities:
            return self._entity_capabilities[entity_id]
        
        # Get capabilities from API
        capabilities = await self.api.get_entity_capabilities(entity_id)
        
        # Cache the result
        self._entity_capabilities[entity_id] = capabilities
        
        return capabilities
    
    def get_entity_capability_sync(self, entity_id: str) -> Dict[str, Any]:
        """
        Simplified synchronous version of get_entity_capability.
        
        Args:
            entity_id (str): Entity ID to get capabilities for
            
        Returns:
            Dict[str, Any]: Entity capabilities
        """
        domain = get_domain_from_entity(entity_id)
        attributes = self.get_entity_attributes_sync(entity_id)
        
        capabilities = {
            'can_toggle': False,
            'can_dim': False,
            'can_color': False,
            'has_temperature': False,
            'has_humidity': False,
            'has_motion': False,
            'has_binary_state': False
        }
        
        # Determine capabilities based on domain
        if domain in ['light', 'switch', 'fan', 'input_boolean']:
            capabilities['can_toggle'] = True
            capabilities['has_binary_state'] = True
        
        if domain == 'light':
            if 'brightness' in attributes:
                capabilities['can_dim'] = True
            if 'rgb_color' in attributes or 'hs_color' in attributes:
                capabilities['can_color'] = True
        
        if domain in ['climate', 'weather']:
            if 'temperature' in attributes or 'current_temperature' in attributes:
                capabilities['has_temperature'] = True
            if 'humidity' in attributes or 'current_humidity' in attributes:
                capabilities['has_humidity'] = True
        
        if domain == 'sensor':
            if 'device_class' in attributes:
                device_class = attributes['device_class']
                if device_class == 'temperature':
                    capabilities['has_temperature'] = True
                elif device_class == 'humidity':
                    capabilities['has_humidity'] = True
        
        if domain in ['binary_sensor']:
            capabilities['has_binary_state'] = True
            if 'device_class' in attributes and attributes['device_class'] == 'motion':
                capabilities['has_motion'] = True
        
        return capabilities