"""
Home Assistant API Connection Module.

This module handles authentication and API interactions with Home Assistant.
"""

import logging
import aiohttp
import requests
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, Set

logger = logging.getLogger(__name__)

class HomeAssistantAPI:
    """Class for interacting with the Home Assistant API."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Home Assistant API connection.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary containing Home Assistant connection details
        """
        self.base_url = config['home_assistant']['url']
        self.token = config['home_assistant']['token']
        self.verify_ssl = config['home_assistant']['verify_ssl']
        self.session = None
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        self._entity_categories = {}
        self._domain_services = {}
    
    async def connect(self) -> None:
        """Establish connection to Home Assistant API."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self._headers)
        logger.info(f"Connected to Home Assistant at {self.base_url}")
    
    async def close(self) -> None:
        """Close the API connection."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Closed connection to Home Assistant")
    
    async def validate_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Validate the connection to Home Assistant.
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            await self.connect()
            url = f"{self.base_url}/api/"
            async with self.session.get(url, ssl=self.verify_ssl) as response:
                if response.status == 200:
                    data = await response.json()
                    if "message" in data and data["message"] == "API running.":
                        logger.info("Home Assistant API connection validated successfully")
                        return True, None
                    else:
                        logger.error(f"Unexpected API response: {data}")
                        return False, "Unexpected API response"
                elif response.status == 401:
                    logger.error("Authentication failed - invalid token")
                    return False, "Authentication failed - invalid token"
                else:
                    logger.error(f"API validation failed: {response.status}")
                    return False, f"API validation failed: {response.status}"
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Connection error: {str(e)}")
            return False, f"Connection error: {str(e)}"
        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            return False, f"Validation failed: {str(e)}"
    
    def validate_connection_sync(self) -> Tuple[bool, Optional[str]]:
        """
        Synchronous version of validate_connection.
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            url = f"{self.base_url}/api/"
            response = requests.get(url, headers=self._headers, verify=self.verify_ssl)
            if response.status_code == 200:
                data = response.json()
                if "message" in data and data["message"] == "API running.":
                    logger.info("Home Assistant API connection validated successfully")
                    return True, None
                else:
                    logger.error(f"Unexpected API response: {data}")
                    return False, "Unexpected API response"
            elif response.status_code == 401:
                logger.error("Authentication failed - invalid token")
                return False, "Authentication failed - invalid token"
            else:
                logger.error(f"API validation failed: {response.status_code}")
                return False, f"API validation failed: {response.status_code}"
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {str(e)}")
            return False, f"Connection error: {str(e)}"
        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            return False, f"Validation failed: {str(e)}"
    
    async def get_states(self) -> List[Dict[str, Any]]:
        """
        Get states of all entities.
        
        Returns:
            List[Dict[str, Any]]: List of entity states
        """
        await self.connect()
        url = f"{self.base_url}/api/states"
        async with self.session.get(url, ssl=self.verify_ssl) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to get states: {response.status}")
                return []
    
    async def get_entity_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get state of a specific entity.
        
        Args:
            entity_id (str): Entity ID to get state for
            
        Returns:
            Optional[Dict[str, Any]]: Entity state or None if not found
        """
        await self.connect()
        url = f"{self.base_url}/api/states/{entity_id}"
        async with self.session.get(url, ssl=self.verify_ssl) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to get state for {entity_id}: {response.status}")
                return None
    
    async def call_service(self, domain: str, service: str, service_data: Dict[str, Any]) -> bool:
        """
        Call a Home Assistant service.
        
        Args:
            domain (str): Service domain (e.g., 'light', 'switch')
            service (str): Service to call (e.g., 'turn_on', 'turn_off')
            service_data (Dict[str, Any]): Service data including entity_id and any parameters
            
        Returns:
            bool: True if successful, False otherwise
        """
        await self.connect()
        url = f"{self.base_url}/api/services/{domain}/{service}"
        async with self.session.post(url, json=service_data, ssl=self.verify_ssl) as response:
            if response.status in (200, 201):
                logger.info(f"Successfully called service {domain}.{service}")
                return True
            else:
                logger.error(f"Failed to call service {domain}.{service}: {response.status}")
                return False
    
    async def get_history(self, 
                         entity_ids: Optional[List[str]] = None, 
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get history data for entities.
        
        Args:
            entity_ids (Optional[List[str]]): List of entity IDs to get history for. 
                                            None means all entities.
            start_time (Optional[datetime]): Start time for history data. 
                                            None means 1 day ago.
            end_time (Optional[datetime]): End time for history data. 
                                          None means now.
            
        Returns:
            List[Dict[str, Any]]: List of history data
        """
        await self.connect()
        
        # Default to last 24 hours if not specified
        if start_time is None:
            start_time = datetime.now() - timedelta(days=1)
        
        if end_time is None:
            end_time = datetime.now()
        
        # Format timestamps for the API
        start_time_str = start_time.isoformat()
        end_time_str = end_time.isoformat()
        
        # Build the URL with query parameters
        url = f"{self.base_url}/api/history/period/{start_time_str}"
        params = {
            "end_time": end_time_str
        }
        
        if entity_ids:
            params["filter_entity_id"] = ",".join(entity_ids)
        
        async with self.session.get(url, params=params, ssl=self.verify_ssl) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to get history: {response.status}")
                return []
    
    async def get_services(self) -> Dict[str, Any]:
        """
        Get available services from Home Assistant.
        
        Returns:
            Dict[str, Any]: Dictionary of available services by domain
        """
        await self.connect()
        url = f"{self.base_url}/api/services"
        async with self.session.get(url, ssl=self.verify_ssl) as response:
            if response.status == 200:
                services = await response.json()
                # Cache the services for later use
                self._domain_services = {domain: service_data for domain, service_data in services.items()}
                return services
            else:
                logger.error(f"Failed to get services: {response.status}")
                return {}
    
    async def get_config(self) -> Dict[str, Any]:
        """
        Get Home Assistant configuration.
        
        Returns:
            Dict[str, Any]: Home Assistant configuration
        """
        await self.connect()
        url = f"{self.base_url}/api/config"
        async with self.session.get(url, ssl=self.verify_ssl) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to get config: {response.status}")
                return {}
    
    async def get_areas(self) -> List[Dict[str, Any]]:
        """
        Get Home Assistant areas.
        
        Returns:
            List[Dict[str, Any]]: List of areas
        """
        await self.connect()
        url = f"{self.base_url}/api/config/area_registry"
        async with self.session.get(url, ssl=self.verify_ssl) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to get areas: {response.status}")
                return []
    
    async def get_entity_registry(self) -> List[Dict[str, Any]]:
        """
        Get Home Assistant entity registry.
        
        Returns:
            List[Dict[str, Any]]: List of entity registry entries
        """
        await self.connect()
        url = f"{self.base_url}/api/config/entity_registry"
        async with self.session.get(url, ssl=self.verify_ssl) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to get entity registry: {response.status}")
                return []
    
    async def update_entity_metadata(self) -> bool:
        """
        Update entity metadata including categories and area assignments.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get entity registry to understand what entities are available
            entity_registry = await self.get_entity_registry()
            
            # Get area registry to map area IDs to names
            areas = await self.get_areas()
            area_map = {area['area_id']: area['name'] for area in areas}
            
            # Reset the categories
            self._entity_categories = {}
            
            # Categorize entities by domain, capability, and area
            for entity in entity_registry:
                entity_id = entity.get('entity_id')
                if not entity_id:
                    continue
                
                domain = entity_id.split('.')[0]
                
                # Categorize by area
                area_id = entity.get('area_id')
                area_name = area_map.get(area_id, 'Unknown Area') if area_id else 'No Area'
                
                if area_name not in self._entity_categories:
                    self._entity_categories[area_name] = {}
                
                if domain not in self._entity_categories[area_name]:
                    self._entity_categories[area_name][domain] = []
                
                self._entity_categories[area_name][domain].append(entity_id)
            
            return True
        except Exception as e:
            logger.error(f"Failed to update entity metadata: {str(e)}")
            return False
    
    async def get_entities_by_category(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Get entities organized by category (area and domain).
        
        Returns:
            Dict[str, Dict[str, List[str]]]: Dictionary of entities by area and domain
        """
        if not self._entity_categories:
            await self.update_entity_metadata()
        
        return self._entity_categories
    
    async def get_entity_attributes(self, entity_id: str) -> Dict[str, Any]:
        """
        Get all attributes for a specific entity.
        
        Args:
            entity_id (str): Entity ID to get attributes for
            
        Returns:
            Dict[str, Any]: Entity attributes or empty dict if not found
        """
        entity_state = await self.get_entity_state(entity_id)
        if entity_state and 'attributes' in entity_state:
            return entity_state['attributes']
        return {}
    
    async def get_entity_capabilities(self, entity_id: str) -> Dict[str, Any]:
        """
        Get capabilities for a specific entity based on its domain and attributes.
        
        Args:
            entity_id (str): Entity ID to get capabilities for
            
        Returns:
            Dict[str, Any]: Entity capabilities
        """
        domain = entity_id.split('.')[0]
        attributes = await self.get_entity_attributes(entity_id)
        
        capabilities = {
            'can_toggle': False,
            'can_dim': False,
            'can_color': False,
            'has_temperature': False,
            'has_humidity': False,
            'has_motion': False,
            'has_binary_state': False,
            'supports_services': []
        }
        
        # Get available services for this domain
        if not self._domain_services:
            await self.get_services()
        
        domain_services = self._domain_services.get(domain, {})
        capabilities['supports_services'] = list(domain_services.keys()) if domain_services else []
        
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
    
    def get_entities_sync(self) -> List[Dict[str, Any]]:
        """
        Synchronous version of get_states for use in Claude tools.
        
        Returns:
            List[Dict[str, Any]]: List of entity states
        """
        url = f"{self.base_url}/api/states"
        response = requests.get(url, headers=self._headers, verify=self.verify_ssl)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get states: {response.status_code}")
            return []
    
    def get_entity_state_sync(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Synchronous version of get_entity_state.
        
        Args:
            entity_id (str): Entity ID to get state for
            
        Returns:
            Optional[Dict[str, Any]]: Entity state or None if not found
        """
        url = f"{self.base_url}/api/states/{entity_id}"
        response = requests.get(url, headers=self._headers, verify=self.verify_ssl)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get state for {entity_id}: {response.status_code}")
            return None
    
    def call_service_sync(self, domain: str, service: str, service_data: Dict[str, Any]) -> bool:
        """
        Synchronous version of call_service for use in Claude tools.
        
        Args:
            domain (str): Service domain (e.g., 'light', 'switch')
            service (str): Service to call (e.g., 'turn_on', 'turn_off')
            service_data (Dict[str, Any]): Service data including entity_id and any parameters
            
        Returns:
            bool: True if successful, False otherwise
        """
        url = f"{self.base_url}/api/services/{domain}/{service}"
        response = requests.post(url, json=service_data, headers=self._headers, verify=self.verify_ssl)
        if response.status_code in (200, 201):
            logger.info(f"Successfully called service {domain}.{service}")
            return True
        else:
            logger.error(f"Failed to call service {domain}.{service}: {response.status_code}")
            return False
    
    def get_history_sync(self,
                        entity_ids: Optional[List[str]] = None,
                        start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Synchronous version of get_history.
        
        Args:
            entity_ids (Optional[List[str]]): List of entity IDs to get history for.
                                            None means all entities.
            start_time (Optional[datetime]): Start time for history data.
                                            None means 1 day ago.
            end_time (Optional[datetime]): End time for history data.
                                          None means now.
            
        Returns:
            List[Dict[str, Any]]: List of history data
        """
        # Default to last 24 hours if not specified
        if start_time is None:
            start_time = datetime.now() - timedelta(days=1)
        
        if end_time is None:
            end_time = datetime.now()
        
        # Format timestamps for the API
        start_time_str = start_time.isoformat()
        end_time_str = end_time.isoformat()
        
        # Build the URL with query parameters
        url = f"{self.base_url}/api/history/period/{start_time_str}"
        params = {
            "end_time": end_time_str
        }
        
        if entity_ids:
            params["filter_entity_id"] = ",".join(entity_ids)
        
        response = requests.get(url, headers=self._headers, params=params, verify=self.verify_ssl)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get history: {response.status_code}")
            return []