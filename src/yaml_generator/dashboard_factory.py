"""
Home Assistant Dashboard Factory.

This module provides high-level functions for creating various types of dashboards.
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

from src.connection.api import HomeAssistantAPI
from src.connection.entity_manager import EntityManager
from src.yaml_generator.dashboard import DashboardGenerator
from src.yaml_generator.template_manager import TemplateManager

logger = logging.getLogger(__name__)

class DashboardFactory:
    """Class for generating complete Home Assistant dashboards."""
    
    def __init__(self, api: HomeAssistantAPI, config: Dict[str, Any]):
        """
        Initialize the dashboard factory.
        
        Args:
            api (HomeAssistantAPI): Home Assistant API client
            config (Dict[str, Any]): Configuration dictionary
        """
        self.api = api
        self.entity_manager = EntityManager(api)
        self.config = config
        self.dashboard_generator = DashboardGenerator(config)
        self.template_manager = TemplateManager()
    
    async def create_overview_dashboard(self, 
                                       title: str = "Home Overview", 
                                       output_path: Optional[str] = None) -> str:
        """
        Create an overview dashboard with all entity types.
        
        Args:
            title (str): Dashboard title
            output_path (Optional[str]): Output file path
            
        Returns:
            str: Generated YAML content or file path if output_path is provided
        """
        logger.info(f"Creating overview dashboard: {title}")
        
        # Get all entities
        entities = await self.entity_manager.get_all_entities()
        
        # Get entity categories by area
        categories = await self.api.get_entities_by_category()
        
        # Create views
        views = []
        
        # 1. Create a main overview view
        main_cards = []
        
        # Add a welcome card
        main_cards.append({
            "type": "markdown",
            "content": f"# Welcome to {title}\n\nDashboard created: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        })
        
        # Add a weather card if available
        weather_entities = [e for e in entities if e['entity_id'].startswith('weather.')]
        if weather_entities:
            main_cards.append(self.dashboard_generator.generate_card(
                'weather-forecast',
                weather_entities[0]['entity_id'],
                forecast=True
            ))
        
        # Add quick access to important entities
        important_domains = ['light', 'climate', 'cover', 'media_player']
        important_entities = []
        
        for domain in important_domains:
            domain_entities = [e for e in entities if e['entity_id'].startswith(f"{domain}.")]
            if domain_entities:
                # Take up to 8 entities from each domain
                for entity in domain_entities[:8]:
                    important_entities.append({
                        "entity": entity['entity_id'],
                        "name": entity['attributes'].get('friendly_name', entity['entity_id'].split('.')[1].replace('_', ' ').title())
                    })
        
        if important_entities:
            main_cards.append(self.dashboard_generator.generate_glance_card(
                important_entities,
                title="Quick Access",
                columns=4,
                show_state=True
            ))
        
        # Create the main view
        views.append(self.dashboard_generator.generate_view(
            title="Overview",
            cards=main_cards,
            path="overview",
            icon="mdi:view-dashboard"
        ))
        
        # 2. Create area views
        for area_name, domains in categories.items():
            # Skip areas with no entities
            if not domains:
                continue
            
            area_entities = []
            for domain_entities in domains.values():
                for entity_id in domain_entities:
                    # Get the entity state and attributes
                    entity = await self.entity_manager.get_entity(entity_id)
                    if entity:
                        area_entities.append(entity)
            
            if area_entities:
                area_view = self.dashboard_generator.generate_area_view(
                    area_name=area_name,
                    entities=area_entities,
                    icon="mdi:floor-plan"
                )
                views.append(area_view)
        
        # 3. Create domain-specific views
        domains_to_include = ['light', 'switch', 'sensor', 'binary_sensor', 'climate', 
                             'media_player', 'camera', 'automation', 'scene']
        
        for domain in domains_to_include:
            domain_entities = await self.entity_manager.get_entities_by_domain(domain)
            
            # Skip domains with few entities
            if len(domain_entities) <= 2:
                continue
            
            domain_view = self.dashboard_generator.generate_domain_view(
                domain=domain,
                entities=domain_entities,
                icon=self.dashboard_generator.domain_icons.get(domain, "mdi:circle")
            )
            views.append(domain_view)
        
        # Create the dashboard
        return self.dashboard_generator.create_lovelace_dashboard(
            title=title,
            views=views,
            output_path=output_path
        )
    
    async def create_room_dashboard(self,
                                   title: str = "Rooms",
                                   output_path: Optional[str] = None) -> str:
        """
        Create a room-based dashboard.
        
        Args:
            title (str): Dashboard title
            output_path (Optional[str]): Output file path
            
        Returns:
            str: Generated YAML content or file path if output_path is provided
        """
        logger.info(f"Creating room dashboard: {title}")
        
        # Get entity categories by area
        categories = await self.api.get_entities_by_category()
        
        # Prepare rooms data structure
        rooms = []
        
        for area_name, domains in categories.items():
            # Skip areas with no entities
            if not domains:
                continue
            
            # Collect all entities for this area
            area_entities = []
            for domain_entities in domains.values():
                for entity_id in domain_entities:
                    # Get the entity state and attributes
                    entity = await self.entity_manager.get_entity(entity_id)
                    if entity:
                        area_entities.append(entity)
            
            if not area_entities:
                continue
            
            # Group entities by domain for cards
            cards = []
            
            # Try to identify the most relevant entities for this room
            lights = [e for e in area_entities if e['entity_id'].startswith('light.')]
            climate = [e for e in area_entities if e['entity_id'].startswith('climate.')]
            media = [e for e in area_entities if e['entity_id'].startswith('media_player.')]
            covers = [e for e in area_entities if e['entity_id'].startswith('cover.')]
            sensors = [e for e in area_entities if e['entity_id'].startswith('sensor.')]
            binary_sensors = [e for e in area_entities if e['entity_id'].startswith('binary_sensor.')]
            cameras = [e for e in area_entities if e['entity_id'].startswith('camera.')]
            
            # Add a title card
            cards.append({
                "type": "markdown",
                "content": f"# {area_name}"
            })
            
            # Add camera cards if any
            for camera in cameras:
                cards.append(self.dashboard_generator.generate_card(
                    'picture-entity',
                    camera['entity_id'],
                    title=camera['attributes'].get('friendly_name', camera['entity_id'].split('.')[1].replace('_', ' ').title()),
                    camera_image=camera['entity_id'],
                    entity_id=camera['entity_id']
                ))
            
            # Add light controls
            if lights:
                light_entities = []
                for light in lights:
                    light_entities.append({
                        "entity": light['entity_id'],
                        "name": light['attributes'].get('friendly_name', light['entity_id'].split('.')[1].replace('_', ' ').title()),
                        "tap_action": {"action": "toggle"}
                    })
                
                cards.append(self.dashboard_generator.generate_glance_card(
                    light_entities,
                    title="Lights",
                    columns=min(4, len(light_entities)),
                    show_state=True
                ))
            
            # Add climate controls
            for climate_entity in climate:
                cards.append(self.dashboard_generator.generate_card(
                    'thermostat',
                    climate_entity['entity_id'],
                    title=climate_entity['attributes'].get('friendly_name', climate_entity['entity_id'].split('.')[1].replace('_', ' ').title())
                ))
            
            # Add media players
            for media_entity in media:
                cards.append(self.dashboard_generator.generate_card(
                    'media-control',
                    media_entity['entity_id'],
                    title=media_entity['attributes'].get('friendly_name', media_entity['entity_id'].split('.')[1].replace('_', ' ').title())
                ))
            
            # Add cover controls
            if covers:
                cover_entities = []
                for cover in covers:
                    cover_entities.append({
                        "entity": cover['entity_id'],
                        "name": cover['attributes'].get('friendly_name', cover['entity_id'].split('.')[1].replace('_', ' ').title())
                    })
                
                cards.append(self.dashboard_generator.generate_entities_card(
                    cover_entities,
                    title="Covers",
                    show_header_toggle=True
                ))
            
            # Add sensors
            if sensors:
                # Categorize sensors
                temp_sensors = [s for s in sensors if s['attributes'].get('device_class') == 'temperature']
                humidity_sensors = [s for s in sensors if s['attributes'].get('device_class') == 'humidity']
                
                if temp_sensors or humidity_sensors:
                    sensor_entities = []
                    
                    for sensor in temp_sensors + humidity_sensors:
                        sensor_entities.append({
                            "entity": sensor['entity_id'],
                            "name": sensor['attributes'].get('friendly_name', sensor['entity_id'].split('.')[1].replace('_', ' ').title())
                        })
                    
                    cards.append(self.dashboard_generator.generate_entities_card(
                        sensor_entities,
                        title="Climate Sensors",
                        show_header_toggle=False
                    ))
            
            # Add binary sensors (motion, door, window)
            if binary_sensors:
                binary_sensor_entities = []
                for sensor in binary_sensors:
                    binary_sensor_entities.append({
                        "entity": sensor['entity_id'],
                        "name": sensor['attributes'].get('friendly_name', sensor['entity_id'].split('.')[1].replace('_', ' ').title())
                    })
                
                cards.append(self.dashboard_generator.generate_entities_card(
                    binary_sensor_entities,
                    title="Sensors",
                    show_header_toggle=False
                ))
            
            # Add the room to the list
            rooms.append({
                "name": area_name,
                "path": area_name.lower().replace(' ', '_'),
                "icon": "mdi:floor-plan",
                "cards": cards
            })
        
        # Create the dashboard using the room template
        context = {
            "title": title,
            "rooms": rooms
        }
        
        result = self.template_manager.render_template("room_dashboard", context)
        
        if result and output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(result)
            logger.info(f"Room dashboard written to {output_path}")
            return output_path
        
        return result
    
    async def create_entity_type_dashboard(self,
                                          title: str = "Entities by Type",
                                          output_path: Optional[str] = None) -> str:
        """
        Create a dashboard organized by entity type.
        
        Args:
            title (str): Dashboard title
            output_path (Optional[str]): Output file path
            
        Returns:
            str: Generated YAML content or file path if output_path is provided
        """
        logger.info(f"Creating entity type dashboard: {title}")
        
        # Get all entities
        entities = await self.entity_manager.get_all_entities()
        
        # Group entities by domain
        domains = {}
        for entity in entities:
            entity_id = entity['entity_id']
            domain = entity_id.split('.')[0]
            
            if domain not in domains:
                domains[domain] = []
            
            # Add entity with friendly name
            domains[domain].append({
                "entity_id": entity_id,
                "name": entity['attributes'].get('friendly_name', entity_id.split('.')[1].replace('_', ' ').title()),
                "state": entity['state']
            })
        
        # Define domain icons
        domain_icons = self.dashboard_generator.domain_icons
        
        # Prepare context for the template
        context = {
            "title": title,
            "domains": domains,
            "domain_icons": domain_icons,
            "domain_badges": {},  # No badges by default
            "entities_per_card": 10,
            "show_header_toggle": True
        }
        
        # Render the template
        result = self.template_manager.render_template("entity_dashboard", context)
        
        if result and output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(result)
            logger.info(f"Entity type dashboard written to {output_path}")
            return output_path
        
        return result
    
    async def create_grid_dashboard(self,
                                   title: str,
                                   entity_ids: List[str],
                                   output_path: Optional[str] = None,
                                   columns: int = 3) -> str:
        """
        Create a grid dashboard with the specified entities.
        
        Args:
            title (str): Dashboard title
            entity_ids (List[str]): List of entity IDs to include
            output_path (Optional[str]): Output file path
            columns (int): Number of columns in the grid
            
        Returns:
            str: Generated YAML content or file path if output_path is provided
        """
        logger.info(f"Creating grid dashboard: {title}")
        
        # Get entities details
        cards = []
        for entity_id in entity_ids:
            entity = await self.entity_manager.get_entity(entity_id)
            if not entity:
                logger.warning(f"Entity not found: {entity_id}")
                continue
                
            domain = entity_id.split('.')[0]
            friendly_name = entity['attributes'].get('friendly_name', entity_id.split('.')[1].replace('_', ' ').title())
            
            # Determine card type based on domain
            card_type = 'entities'  # Default card type
            
            if domain == 'light':
                card_type = 'light'
            elif domain == 'climate':
                card_type = 'thermostat'
            elif domain == 'weather':
                card_type = 'weather-forecast'
            elif domain == 'media_player':
                card_type = 'media-control'
            elif domain == 'camera':
                card_type = 'picture-entity'
            elif domain in ['sensor', 'binary_sensor']:
                card_type = 'sensor'
            
            # Generate the card
            card = self.dashboard_generator.generate_card(
                card_type,
                entity_id,
                title=friendly_name,
                icon=entity['attributes'].get('icon', self.dashboard_generator.domain_icons.get(domain))
            )
            
            cards.append(card)
        
        # Prepare context for the grid template
        context = {
            "title": title,
            "path": title.lower().replace(' ', '_'),
            "columns": columns,
            "cards": cards
        }
        
        # Render the template
        result = self.template_manager.render_template("grid_dashboard", context)
        
        if result and output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(result)
            logger.info(f"Grid dashboard written to {output_path}")
            return output_path
        
        return result
    
    async def discover_and_suggest_dashboards(self) -> List[Dict[str, Any]]:
        """
        Discover entities and suggest possible dashboards.
        
        Returns:
            List[Dict[str, Any]]: List of suggested dashboards
        """
        logger.info("Discovering and suggesting dashboards")
        
        # Get all entities
        entities = await self.entity_manager.get_all_entities()
        
        # Get entity categories by area
        categories = await self.api.get_entities_by_category()
        
        suggestions = []
        
        # 1. Always suggest an overview dashboard
        suggestions.append({
            "title": "Home Overview",
            "description": "Complete overview of your home with all areas and entity types",
            "type": "overview",
            "recommended": True
        })
        
        # 2. Suggest room-based dashboard if we have multiple areas
        if len(categories) > 1:
            suggestions.append({
                "title": "Rooms",
                "description": f"Dashboard organized by rooms ({len(categories)} areas detected)",
                "type": "rooms",
                "recommended": True
            })
        
        # 3. Suggest entity-type dashboard if we have diverse entity types
        domains = set()
        for entity in entities:
            domains.add(entity['entity_id'].split('.')[0])
        
        if len(domains) > 3:
            suggestions.append({
                "title": "Entities by Type",
                "description": f"Dashboard organized by entity types ({len(domains)} types detected)",
                "type": "entity_types",
                "recommended": True
            })
        
        # 4. Suggest domain-specific dashboards for domains with many entities
        domain_counts = {}
        for entity in entities:
            domain = entity['entity_id'].split('.')[0]
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        for domain, count in domain_counts.items():
            if count >= 5:  # Only suggest if there are at least 5 entities
                suggestions.append({
                    "title": f"{domain.title()} Dashboard",
                    "description": f"Dashboard for all {domain} entities ({count} detected)",
                    "type": "domain",
                    "domain": domain,
                    "recommended": count >= 10  # Strongly recommend if there are many entities
                })
        
        # 5. Suggest special dashboards based on entity types
        
        # Climate dashboard if we have climate entities
        climate_entities = [e for e in entities if e['entity_id'].startswith('climate.')]
        if climate_entities:
            suggestions.append({
                "title": "Climate Control",
                "description": f"Dashboard for all climate and temperature entities ({len(climate_entities)} climate devices detected)",
                "type": "climate",
                "recommended": len(climate_entities) > 1
            })
        
        # Media dashboard if we have media players
        media_entities = [e for e in entities if e['entity_id'].startswith('media_player.')]
        if media_entities:
            suggestions.append({
                "title": "Media Players",
                "description": f"Dashboard for all media players ({len(media_entities)} detected)",
                "type": "media",
                "recommended": len(media_entities) > 1
            })
        
        # Security dashboard if we have cameras or security sensors
        camera_entities = [e for e in entities if e['entity_id'].startswith('camera.')]
        motion_sensors = [e for e in entities if e['entity_id'].startswith('binary_sensor.') 
                        and e['attributes'].get('device_class') == 'motion']
        door_sensors = [e for e in entities if e['entity_id'].startswith('binary_sensor.')
                       and e['attributes'].get('device_class') in ['door', 'window', 'opening']]
        
        if camera_entities or (motion_sensors and door_sensors):
            suggestions.append({
                "title": "Security",
                "description": f"Security dashboard with cameras and sensors ({len(camera_entities)} cameras, {len(motion_sensors)} motion sensors, {len(door_sensors)} door/window sensors)",
                "type": "security",
                "recommended": True if camera_entities else False
            })
        
        return suggestions