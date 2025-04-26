"""
Home Assistant Dashboard YAML Generator.

This module handles the generation of YAML files for Home Assistant dashboards.
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import jinja2
import re
import json

logger = logging.getLogger(__name__)

class DashboardGenerator:
    """Class for generating Home Assistant dashboard YAML files."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the dashboard generator.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
        """
        self.config = config
        self.default_theme = config['dashboard'].get('default_theme', 'default')
        self.default_icon = config['dashboard'].get('default_icon', 'mdi:home-assistant')
        self.template_env = self._setup_jinja_environment()
        
        # Dictionary of domain to icon mappings
        self.domain_icons = {
            'light': 'mdi:lightbulb',
            'switch': 'mdi:toggle-switch',
            'sensor': 'mdi:eye',
            'binary_sensor': 'mdi:checkbox-marked-circle',
            'climate': 'mdi:thermostat',
            'weather': 'mdi:weather-cloudy',
            'media_player': 'mdi:play-circle',
            'camera': 'mdi:video',
            'cover': 'mdi:window-shutter',
            'fan': 'mdi:fan',
            'vacuum': 'mdi:robot-vacuum',
            'person': 'mdi:account',
            'device_tracker': 'mdi:cellphone',
            'automation': 'mdi:robot',
            'script': 'mdi:script-text',
            'scene': 'mdi:palette',
            'input_boolean': 'mdi:toggle-switch-outline',
            'input_number': 'mdi:numeric',
            'input_select': 'mdi:form-select',
            'input_text': 'mdi:form-textbox',
            'input_datetime': 'mdi:calendar-clock',
            'sun': 'mdi:white-balance-sunny',
            'group': 'mdi:account-group',
        }
    
    def _setup_jinja_environment(self) -> jinja2.Environment:
        """
        Set up the Jinja2 environment for templates.
        
        Returns:
            jinja2.Environment: Configured Jinja environment
        """
        template_dir = Path(__file__).parent / "templates"
        if not template_dir.exists():
            template_dir.mkdir(parents=True)
            
        # Create a loader that looks for templates in the specified directory
        loader = jinja2.FileSystemLoader(template_dir)
        env = jinja2.Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
        
        # Add custom filters
        env.filters['to_yaml'] = self._to_yaml_filter
        env.filters['to_json'] = self._to_json_filter
        env.filters['domain'] = self._domain_filter
        env.filters['friendly_name'] = self._friendly_name_filter
        
        return env
    
    def _to_yaml_filter(self, value: Any) -> str:
        """
        Convert a Python object to YAML format, indented correctly for templates.
        
        Args:
            value (Any): Value to convert to YAML
            
        Returns:
            str: YAML representation of the value
        """
        if isinstance(value, str):
            return value
        
        # Convert to YAML
        yaml_str = yaml.dump(value, default_flow_style=False, sort_keys=False)
        
        # Remove the document start marker
        yaml_str = yaml_str.replace('---\n', '')
        
        # Remove trailing newline
        yaml_str = yaml_str.rstrip()
        
        # Fix indentation for multi-line strings
        lines = yaml_str.split('\n')
        if len(lines) > 1:
            # The first line will be properly aligned with the current indentation
            # Subsequent lines need to be indented to match
            result = [lines[0]]
            for line in lines[1:]:
                result.append('  ' + line)
            return '\n'.join(result)
        
        return yaml_str
    
    def _to_json_filter(self, value: Any) -> str:
        """
        Convert a Python object to JSON format.
        
        Args:
            value (Any): Value to convert to JSON
            
        Returns:
            str: JSON representation of the value
        """
        return json.dumps(value)
    
    def _domain_filter(self, entity_id: str) -> str:
        """
        Extract the domain from an entity ID.
        
        Args:
            entity_id (str): Entity ID
            
        Returns:
            str: Domain part of the entity ID
        """
        parts = entity_id.split('.')
        if len(parts) >= 2:
            return parts[0]
        return entity_id
    
    def _friendly_name_filter(self, entity_id: str, default: str = None) -> str:
        """
        Convert an entity ID to a friendly name.
        
        Args:
            entity_id (str): Entity ID
            default (str, optional): Default name if conversion fails
            
        Returns:
            str: Friendly name
        """
        if not entity_id or '.' not in entity_id:
            return default or entity_id
        
        # Extract the entity name after the domain
        name = entity_id.split('.', 1)[1]
        
        # Replace underscores with spaces and capitalize each word
        name = name.replace('_', ' ').title()
        
        return name
    
    def create_lovelace_dashboard(self, 
                                 title: str, 
                                 views: List[Dict[str, Any]], 
                                 output_path: Optional[str] = None,
                                 **kwargs) -> str:
        """
        Create a Lovelace dashboard YAML file.
        
        Args:
            title (str): Dashboard title
            views (List[Dict[str, Any]]): List of view configurations
            output_path (Optional[str]): Output file path
            **kwargs: Additional dashboard configuration options
            
        Returns:
            str: Generated YAML content or file path if output_path is provided
        """
        dashboard = {
            "title": title,
            "views": views,
            "theme": kwargs.get('theme', self.default_theme)
        }
        
        # Add optional configuration
        if 'background' in kwargs:
            dashboard['background'] = kwargs['background']
        
        if 'panel' in kwargs:
            dashboard['panel'] = kwargs['panel']
        
        yaml_content = yaml.dump(dashboard, sort_keys=False, default_flow_style=False)
        
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(yaml_content)
            logger.info(f"Dashboard YAML written to {output_path}")
            return output_path
        
        return yaml_content
    
    def create_dashboard_from_template(self,
                                      template_name: str,
                                      context: Dict[str, Any],
                                      output_path: Optional[str] = None) -> str:
        """
        Create a dashboard using a Jinja2 template.
        
        Args:
            template_name (str): Name of the template file
            context (Dict[str, Any]): Template context variables
            output_path (Optional[str]): Output file path
            
        Returns:
            str: Generated YAML content or file path if output_path is provided
        """
        try:
            template = self.template_env.get_template(f"{template_name}.j2")
            yaml_content = template.render(**context)
            
            # Validate the generated YAML
            try:
                yaml.safe_load(yaml_content)
            except yaml.YAMLError as e:
                logger.error(f"Generated YAML is invalid: {e}")
                return None
            
            if output_path:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w') as f:
                    f.write(yaml_content)
                logger.info(f"Dashboard YAML written to {output_path}")
                return output_path
            
            return yaml_content
            
        except jinja2.exceptions.TemplateNotFound:
            logger.error(f"Template {template_name}.j2 not found")
            return None
        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            return None
    
    def generate_card(self, card_type: str, entity_id: str, **kwargs) -> Dict[str, Any]:
        """
        Generate a card configuration for a dashboard.
        
        Args:
            card_type (str): Type of card (e.g., 'entities', 'glance', 'light')
            entity_id (str): Entity ID to display on the card
            **kwargs: Additional card-specific configuration options
            
        Returns:
            Dict[str, Any]: Card configuration
        """
        card = {
            "type": card_type,
            "entity": entity_id
        }
        
        # Add optional title if provided
        if 'title' in kwargs:
            card['title'] = kwargs['title']
        
        # Add optional icon if provided, otherwise use default
        if 'icon' in kwargs:
            card['icon'] = kwargs['icon']
        elif self.default_icon and card_type not in ['weather-forecast', 'map', 'iframe', 'picture']:
            # Don't add default icons to certain card types
            card['icon'] = self.default_icon
        
        # Handle special card types
        if card_type == 'entities':
            # For entities card, entity_id should be in the entities list
            card.pop('entity', None)
            card['entities'] = [entity_id]
            if 'entities' in kwargs and isinstance(kwargs['entities'], list):
                card['entities'].extend(kwargs['entities'])
        elif card_type == 'glance':
            # For glance card, entity_id should be in the entities list
            card.pop('entity', None)
            card['entities'] = [entity_id]
            if 'entities' in kwargs and isinstance(kwargs['entities'], list):
                card['entities'].extend(kwargs['entities'])
            # Add optional columns
            if 'columns' in kwargs:
                card['columns'] = kwargs['columns']
        elif card_type == 'picture-entity':
            # Add required image for picture-entity
            if 'image' in kwargs:
                card['image'] = kwargs['image']
            # Add optional camera_image
            if 'camera_image' in kwargs:
                card['camera_image'] = kwargs['camera_image']
                card.pop('image', None)
        elif card_type == 'statistics-graph':
            # For statistics-graph, entity_id should be in the entities list
            card.pop('entity', None)
            card['entities'] = [entity_id]
            if 'entities' in kwargs and isinstance(kwargs['entities'], list):
                card['entities'].extend(kwargs['entities'])
            # Add required statistical type
            if 'stat_types' in kwargs:
                card['stat_types'] = kwargs['stat_types']
            else:
                card['stat_types'] = ['mean']
        elif card_type == 'sensor':
            # Add optional graph or gauge
            if 'graph' in kwargs:
                card['graph'] = kwargs['graph']
            if 'unit' in kwargs:
                card['unit'] = kwargs['unit']
        elif card_type == 'thermostat':
            # Nothing special for thermostat
            pass
        elif card_type == 'button':
            # Button requires a tap_action
            if 'tap_action' in kwargs:
                card['tap_action'] = kwargs['tap_action']
            elif 'action' in kwargs:
                card['tap_action'] = {'action': kwargs['action']}
            else:
                card['tap_action'] = {'action': 'toggle'}
            # Add optional name
            if 'name' in kwargs:
                card['name'] = kwargs['name']
        elif card_type == 'grid':
            # Grid requires cards list
            card.pop('entity', None)
            if 'cards' in kwargs and isinstance(kwargs['cards'], list):
                card['cards'] = kwargs['cards']
            else:
                card['cards'] = []
            # Add optional columns
            if 'columns' in kwargs:
                card['columns'] = kwargs['columns']
            else:
                card['columns'] = 3
        elif card_type == 'markdown':
            # Markdown requires content
            card.pop('entity', None)
            if 'content' in kwargs:
                card['content'] = kwargs['content']
            else:
                card['content'] = "No content provided"
        
        # Add any remaining kwargs to the card config
        for key, value in kwargs.items():
            if key not in ['title', 'icon', 'entities', 'columns', 'image', 'camera_image', 
                          'stat_types', 'graph', 'unit', 'tap_action', 'action', 
                          'cards', 'content']:
                card[key] = value
        
        return card
    
    def generate_entities_card(self, 
                              entity_ids: List[str], 
                              title: Optional[str] = None,
                              show_header_toggle: bool = True,
                              **kwargs) -> Dict[str, Any]:
        """
        Generate an entities card with multiple entities.
        
        Args:
            entity_ids (List[str]): List of entity IDs to include
            title (Optional[str]): Card title
            show_header_toggle (bool): Whether to show the header toggle
            **kwargs: Additional card configuration options
            
        Returns:
            Dict[str, Any]: Entities card configuration
        """
        card = {
            "type": "entities",
            "entities": [],
            "show_header_toggle": show_header_toggle
        }
        
        if title:
            card["title"] = title
        
        # Process each entity ID
        for entity_id in entity_ids:
            if isinstance(entity_id, str):
                # Simple entity ID string
                card["entities"].append(entity_id)
            elif isinstance(entity_id, dict):
                # Entity with custom configuration
                card["entities"].append(entity_id)
        
        # Add any additional configuration
        for key, value in kwargs.items():
            if key not in ['type', 'entities', 'show_header_toggle', 'title']:
                card[key] = value
        
        return card
    
    def generate_glance_card(self,
                            entity_ids: List[str],
                            title: Optional[str] = None,
                            columns: Optional[int] = None,
                            **kwargs) -> Dict[str, Any]:
        """
        Generate a glance card with multiple entities.
        
        Args:
            entity_ids (List[str]): List of entity IDs to include
            title (Optional[str]): Card title
            columns (Optional[int]): Number of columns
            **kwargs: Additional card configuration options
            
        Returns:
            Dict[str, Any]: Glance card configuration
        """
        card = {
            "type": "glance",
            "entities": []
        }
        
        if title:
            card["title"] = title
        
        if columns:
            card["columns"] = columns
        
        # Process each entity ID
        for entity_id in entity_ids:
            if isinstance(entity_id, str):
                # Simple entity ID string
                card["entities"].append(entity_id)
            elif isinstance(entity_id, dict):
                # Entity with custom configuration
                card["entities"].append(entity_id)
        
        # Add any additional configuration
        for key, value in kwargs.items():
            if key not in ['type', 'entities', 'title', 'columns']:
                card[key] = value
        
        return card
    
    def generate_view(self,
                     title: str,
                     cards: List[Dict[str, Any]],
                     path: Optional[str] = None,
                     icon: Optional[str] = None,
                     **kwargs) -> Dict[str, Any]:
        """
        Generate a view configuration.
        
        Args:
            title (str): View title
            cards (List[Dict[str, Any]]): List of cards in the view
            path (Optional[str]): URL path for the view
            icon (Optional[str]): Icon for the view
            **kwargs: Additional view configuration options
            
        Returns:
            Dict[str, Any]: View configuration
        """
        view = {
            "title": title,
            "cards": cards
        }
        
        if path:
            view["path"] = path
        else:
            # Generate a path from the title
            view["path"] = title.lower().replace(' ', '_')
        
        if icon:
            view["icon"] = icon
        
        # Add any additional view configuration
        for key, value in kwargs.items():
            if key not in ['title', 'cards', 'path', 'icon']:
                view[key] = value
        
        return view
    
    def generate_area_view(self,
                          area_name: str,
                          entities: List[Dict[str, Any]],
                          **kwargs) -> Dict[str, Any]:
        """
        Generate a view for a specific area.
        
        Args:
            area_name (str): Name of the area
            entities (List[Dict[str, Any]]): List of entities in the area
            **kwargs: Additional view configuration options
            
        Returns:
            Dict[str, Any]: View configuration
        """
        # Group entities by domain
        domains = {}
        for entity in entities:
            entity_id = entity.get('entity_id', '')
            if not entity_id:
                continue
                
            domain = entity_id.split('.')[0]
            
            if domain not in domains:
                domains[domain] = []
                
            domains[domain].append(entity)
        
        # Create cards for each domain
        cards = []
        
        # Add a title card
        cards.append({
            "type": "markdown",
            "content": f"# {area_name}\n\n{kwargs.get('description', '')}"
        })
        
        # Create cards for each domain
        for domain, domain_entities in domains.items():
            if not domain_entities:
                continue
                
            # Skip some domains that are better as individual cards
            if domain in ['camera', 'weather']:
                for entity in domain_entities:
                    entity_id = entity.get('entity_id', '')
                    name = entity.get('name', self._friendly_name_filter(entity_id))
                    
                    cards.append(self.generate_card(
                        domain,
                        entity_id,
                        title=name,
                        icon=self.domain_icons.get(domain)
                    ))
                continue
            
            # Create an entities card for this domain
            card_entities = []
            for entity in domain_entities:
                entity_id = entity.get('entity_id', '')
                if entity_id:
                    card_entities.append({
                        "entity": entity_id,
                        "name": entity.get('name', self._friendly_name_filter(entity_id))
                    })
            
            if card_entities:
                cards.append(self.generate_entities_card(
                    card_entities,
                    title=f"{domain.title()} ({len(card_entities)})",
                    icon=self.domain_icons.get(domain)
                ))
        
        # Create the view
        return self.generate_view(
            title=area_name,
            cards=cards,
            path=kwargs.get('path', area_name.lower().replace(' ', '_')),
            icon=kwargs.get('icon', 'mdi:floor-plan')
        )
    
    def generate_domain_view(self,
                            domain: str,
                            entities: List[Dict[str, Any]],
                            **kwargs) -> Dict[str, Any]:
        """
        Generate a view for a specific domain.
        
        Args:
            domain (str): Domain name
            entities (List[Dict[str, Any]]): List of entities in the domain
            **kwargs: Additional view configuration options
            
        Returns:
            Dict[str, Any]: View configuration
        """
        cards = []
        
        # Add a title card
        cards.append({
            "type": "markdown",
            "content": f"# {domain.title()}\n\n{kwargs.get('description', '')}"
        })
        
        # Determine the best card type for this domain
        if domain == 'camera':
            # For cameras, use individual cards
            for entity in entities:
                entity_id = entity.get('entity_id', '')
                name = entity.get('name', self._friendly_name_filter(entity_id))
                
                cards.append(self.generate_card(
                    'picture-entity',
                    entity_id,
                    title=name,
                    camera_image=entity_id
                ))
        elif domain == 'weather':
            # For weather, use individual cards
            for entity in entities:
                entity_id = entity.get('entity_id', '')
                name = entity.get('name', self._friendly_name_filter(entity_id))
                
                cards.append(self.generate_card(
                    'weather-forecast',
                    entity_id,
                    title=name,
                    forecast=True
                ))
        elif domain in ['light', 'switch', 'fan', 'cover']:
            # For controllable entities, use a glance card
            entity_configs = []
            for entity in entities:
                entity_id = entity.get('entity_id', '')
                if entity_id:
                    entity_configs.append({
                        "entity": entity_id,
                        "name": entity.get('name', self._friendly_name_filter(entity_id)),
                        "tap_action": {"action": "toggle"}
                    })
            
            # Split into multiple cards if there are many entities
            max_per_card = 8
            for i in range(0, len(entity_configs), max_per_card):
                batch = entity_configs[i:i+max_per_card]
                cards.append(self.generate_glance_card(
                    batch,
                    title=f"{domain.title()} {i//max_per_card + 1}" if len(entity_configs) > max_per_card else domain.title(),
                    columns=4,
                    show_state=True
                ))
        else:
            # For other domains, use entities cards
            entity_configs = []
            for entity in entities:
                entity_id = entity.get('entity_id', '')
                if entity_id:
                    entity_configs.append({
                        "entity": entity_id,
                        "name": entity.get('name', self._friendly_name_filter(entity_id))
                    })
            
            # Split into multiple cards if there are many entities
            max_per_card = 10
            for i in range(0, len(entity_configs), max_per_card):
                batch = entity_configs[i:i+max_per_card]
                cards.append(self.generate_entities_card(
                    batch,
                    title=f"{domain.title()} {i//max_per_card + 1}" if len(entity_configs) > max_per_card else domain.title(),
                    show_header_toggle=domain in ['light', 'switch', 'fan', 'cover']
                ))
        
        # Create the view
        return self.generate_view(
            title=domain.title(),
            cards=cards,
            path=kwargs.get('path', domain.lower()),
            icon=kwargs.get('icon', self.domain_icons.get(domain, 'mdi:circle'))
        )
    
    def validate_yaml(self, yaml_content: str) -> bool:
        """
        Validate YAML syntax.
        
        Args:
            yaml_content (str): YAML content to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            yaml.safe_load(yaml_content)
            return True
        except yaml.YAMLError as e:
            logger.error(f"YAML validation failed: {e}")
            return False