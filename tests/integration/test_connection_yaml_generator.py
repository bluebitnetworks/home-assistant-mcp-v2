"""
Integration tests for the Connection and YAML Generator modules.

This module tests the integration between the Home Assistant API connection
and the YAML Generator for dashboard creation.
"""

import os
import sys
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Add the root directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.connection.api import HomeAssistantAPI
from src.yaml_generator.dashboard import DashboardGenerator
from src.yaml_generator.dashboard_factory import DashboardFactory


@pytest.fixture
def config():
    """Fixture for test configuration."""
    return {
        'home_assistant': {
            'url': 'http://test.local:8123',
            'token': 'test_token',
            'verify_ssl': False
        },
        'dashboard': {
            'default_theme': 'default',
            'default_icon': 'mdi:home-assistant'
        }
    }


@pytest.fixture
def mock_entities():
    """Fixture for mock entity data."""
    return [
        {
            'entity_id': 'light.living_room',
            'state': 'on',
            'attributes': {
                'friendly_name': 'Living Room Light',
                'brightness': 255,
                'supported_features': 1
            }
        },
        {
            'entity_id': 'sensor.temperature',
            'state': '72',
            'attributes': {
                'friendly_name': 'Temperature',
                'unit_of_measurement': '°F'
            }
        },
        {
            'entity_id': 'switch.kitchen',
            'state': 'off',
            'attributes': {
                'friendly_name': 'Kitchen Switch'
            }
        }
    ]


@pytest.mark.asyncio
async def test_dashboard_generation_with_api_data(config, mock_entities):
    """
    Test that the dashboard generator properly uses data from the API.
    """
    # Mock the API to return our fixture data
    with patch('src.connection.api.HomeAssistantAPI') as mock_api_class:
        mock_api = AsyncMock()
        mock_api.get_states.return_value = mock_entities
        mock_api.get_entity_state.side_effect = lambda entity_id: next(
            (e for e in mock_entities if e['entity_id'] == entity_id), None
        )
        mock_api_class.return_value = mock_api
        
        # Create the dashboard generator with our mocked API
        dashboard_generator = DashboardGenerator(config)
        
        # Test creating a dashboard with api data
        title = "Test Dashboard"
        views = [
            {
                "title": "Main View",
                "cards": [
                    {
                        "type": "entities",
                        "title": "Lights",
                        "entities": ["light.living_room"]
                    },
                    {
                        "type": "sensor", 
                        "entity": "sensor.temperature"
                    }
                ]
            }
        ]
        
        # Generate the dashboard
        dashboard_yaml = dashboard_generator.generate_dashboard(title, views)
        
        # Verify the dashboard contains the expected data
        assert "Test Dashboard" in dashboard_yaml
        assert "Living Room Light" in dashboard_yaml
        assert "Temperature" in dashboard_yaml
        assert "°F" in dashboard_yaml  # Entity attributes should be included


@pytest.mark.asyncio
async def test_entity_data_enrichment(config, mock_entities):
    """
    Test that the dashboard generator enriches cards with entity data.
    """
    # Mock the API to return our fixture data
    with patch('src.connection.api.HomeAssistantAPI') as mock_api_class:
        mock_api = AsyncMock()
        mock_api.get_states.return_value = mock_entities
        mock_api.get_entity_state.side_effect = lambda entity_id: next(
            (e for e in mock_entities if e['entity_id'] == entity_id), None
        )
        mock_api_class.return_value = mock_api
        
        # Create the dashboard generator with our mocked API
        dashboard_generator = DashboardGenerator(config)
        
        # Test with a simple card that needs enrichment
        title = "Enrichment Test"
        views = [
            {
                "title": "Sensors View",
                "cards": [
                    {
                        "type": "entities",
                        "title": "Auto Title",
                        "entities": ["light.living_room", "sensor.temperature", "switch.kitchen"]
                    }
                ]
            }
        ]
        
        # Generate the dashboard
        dashboard_yaml = dashboard_generator.generate_dashboard(title, views)
        
        # Verify entity enrichment
        assert "Living Room Light" in dashboard_yaml  # Friendly name was added
        assert "Temperature" in dashboard_yaml
        assert "Kitchen Switch" in dashboard_yaml
        

@pytest.mark.asyncio
async def test_dashboard_generation_with_non_existent_entities(config, mock_entities):
    """
    Test dashboard generation with non-existent entities.
    """
    # Mock the API to return our fixture data
    with patch('src.connection.api.HomeAssistantAPI') as mock_api_class:
        mock_api = AsyncMock()
        mock_api.get_states.return_value = mock_entities
        mock_api.get_entity_state.side_effect = lambda entity_id: next(
            (e for e in mock_entities if e['entity_id'] == entity_id), None
        )
        mock_api_class.return_value = mock_api
        
        # Create the dashboard generator with our mocked API
        dashboard_generator = DashboardGenerator(config)
        
        # Test with some non-existent entities
        title = "Mixed Entities Test"
        views = [
            {
                "title": "Mixed View",
                "cards": [
                    {
                        "type": "entities",
                        "title": "Entities",
                        "entities": ["light.living_room", "light.non_existent", "sensor.temperature"]
                    }
                ]
            }
        ]
        
        # Generate the dashboard
        dashboard_yaml = dashboard_generator.generate_dashboard(title, views)
        
        # Verify the dashboard contains valid entities but still includes non-existent ones
        assert "Living Room Light" in dashboard_yaml
        assert "Temperature" in dashboard_yaml
        assert "light.non_existent" in dashboard_yaml


@pytest.mark.asyncio
async def test_dashboard_factory_with_api_data(config, mock_entities):
    """
    Test that the dashboard factory properly generates cards based on entity types.
    """
    # Mock the API to return our fixture data
    with patch('src.connection.api.HomeAssistantAPI') as mock_api_class:
        mock_api = AsyncMock()
        mock_api.get_states.return_value = mock_entities
        mock_api.get_entity_state.side_effect = lambda entity_id: next(
            (e for e in mock_entities if e['entity_id'] == entity_id), None
        )
        mock_api_class.return_value = mock_api
        
        # Create the dashboard factory
        dashboard_factory = DashboardFactory(config)
        
        # Test card generation for a light entity
        light_card = dashboard_factory.create_card("light.living_room")
        assert light_card["type"] == "light"
        assert "entity" in light_card
        assert light_card["entity"] == "light.living_room"
        
        # Test card generation for a sensor entity
        sensor_card = dashboard_factory.create_card("sensor.temperature")
        assert sensor_card["type"] == "sensor"
        assert "entity" in sensor_card
        assert sensor_card["entity"] == "sensor.temperature"
        
        # Test card generation for a switch entity
        switch_card = dashboard_factory.create_card("switch.kitchen")
        assert switch_card["type"] == "toggle"
        assert "entity" in switch_card
        assert switch_card["entity"] == "switch.kitchen"
