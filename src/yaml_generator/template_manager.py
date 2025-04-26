"""
Home Assistant Template Manager.

This module provides template management and rendering functions for Home Assistant configurations.
"""

import logging
import yaml
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import jinja2

logger = logging.getLogger(__name__)

class TemplateManager:
    """Class for managing and rendering Home Assistant templates."""
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize the template manager.
        
        Args:
            template_dir (Optional[str]): Directory containing templates. 
                                         If None, uses default templates directory.
        """
        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            self.template_dir = Path(__file__).parent / "templates"
            
        if not self.template_dir.exists():
            self.template_dir.mkdir(parents=True, exist_ok=True)
            
        self.env = self._setup_jinja_environment()
    
    def _setup_jinja_environment(self) -> jinja2.Environment:
        """
        Set up the Jinja2 environment for templates.
        
        Returns:
            jinja2.Environment: Configured Jinja environment
        """
        # Create a loader that looks for templates in the specified directory
        loader = jinja2.FileSystemLoader(self.template_dir)
        env = jinja2.Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
        
        # Add custom filters
        env.filters['to_yaml'] = self._to_yaml_filter
        env.filters['to_json'] = lambda x: json.dumps(x)
        env.filters['domain'] = lambda x: x.split('.')[0] if '.' in x else x
        env.filters['friendly_name'] = self._friendly_name_filter
        env.filters['icon_for_domain'] = self._icon_for_domain_filter
        env.filters['icon_for_entity'] = self._icon_for_entity_filter
        
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
    
    def _icon_for_domain_filter(self, domain: str) -> str:
        """
        Get an icon for a domain.
        
        Args:
            domain (str): Domain name
            
        Returns:
            str: Icon for the domain
        """
        domain_icons = {
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
        
        return domain_icons.get(domain, 'mdi:home-assistant')
    
    def _icon_for_entity_filter(self, entity_id: str) -> str:
        """
        Get an icon for an entity based on its domain.
        
        Args:
            entity_id (str): Entity ID
            
        Returns:
            str: Icon for the entity
        """
        if not entity_id or '.' not in entity_id:
            return 'mdi:home-assistant'
        
        domain = entity_id.split('.')[0]
        return self._icon_for_domain_filter(domain)
    
    def list_templates(self) -> List[str]:
        """
        List all available templates.
        
        Returns:
            List[str]: List of template names (without .j2 extension)
        """
        templates = []
        for file in self.template_dir.glob('*.j2'):
            templates.append(file.stem)
        return templates
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.
        
        Args:
            template_name (str): Name of the template file (without .j2 extension)
            context (Dict[str, Any]): Template context variables
            
        Returns:
            str: Rendered template content
        """
        try:
            template = self.env.get_template(f"{template_name}.j2")
            return template.render(**context)
        except jinja2.exceptions.TemplateNotFound:
            logger.error(f"Template {template_name}.j2 not found")
            return ""
        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            return ""
    
    def render_string_template(self, template_string: str, context: Dict[str, Any]) -> str:
        """
        Render a template string with the given context.
        
        Args:
            template_string (str): Template string to render
            context (Dict[str, Any]): Template context variables
            
        Returns:
            str: Rendered template content
        """
        try:
            template = self.env.from_string(template_string)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Error rendering template string: {str(e)}")
            return ""
    
    def render_card_template(self, card_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render a card template to generate a card configuration.
        
        Args:
            card_type (str): Type of card to render (e.g., 'light', 'entities', 'glance')
            context (Dict[str, Any]): Template context variables
            
        Returns:
            Dict[str, Any]: Card configuration
        """
        try:
            # Try to load card templates
            card_templates = self.env.get_template("card_templates.j2")
            
            # Check if the template has the macro for this card type
            macro_name = f"{card_type}_card"
            if macro_name not in card_templates.module.__dict__:
                logger.error(f"Card template for {card_type} not found")
                return {}
            
            # Use the macro to render the card
            template_string = f"{{% import 'card_templates.j2' as cards %}}\n{{ cards.{macro_name}(**params) }}"
            template = self.env.from_string(template_string)
            yaml_str = template.render(params=context)
            
            # Convert the YAML string to a Python object
            return yaml.safe_load(yaml_str)
            
        except jinja2.exceptions.TemplateNotFound:
            logger.error("Card templates not found")
            return {}
        except Exception as e:
            logger.error(f"Error rendering card template: {str(e)}")
            return {}
    
    def create_template(self, template_name: str, content: str) -> bool:
        """
        Create a new template file.
        
        Args:
            template_name (str): Name for the template (without .j2 extension)
            content (str): Template content
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            template_path = self.template_dir / f"{template_name}.j2"
            with open(template_path, 'w') as f:
                f.write(content)
            logger.info(f"Created template {template_name}.j2")
            return True
        except Exception as e:
            logger.error(f"Error creating template: {str(e)}")
            return False
    
    def validate_template(self, template_string: str) -> bool:
        """
        Validate a template string.
        
        Args:
            template_string (str): Template string to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            self.env.parse(template_string)
            return True
        except jinja2.exceptions.TemplateSyntaxError as e:
            logger.error(f"Template syntax error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error validating template: {str(e)}")
            return False