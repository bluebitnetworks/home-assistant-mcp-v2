"""
Tests for the Home Assistant Connection Utilities.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from src.connection.api import HomeAssistantAPI
from src.connection.utils import (
    discover_entities, get_entity_groups, detect_entity_relationships,
    get_entity_hierarchy, get_entity_hierarchy_sync,
    get_domain_from_entity, get_service_for_action
)

@pytest.fixture
def mock_api():
    """Fixture for mocked HomeAssistantAPI."""
    api = MagicMock(spec=HomeAssistantAPI)
    # Configure necessary async methods as AsyncMock
    api.get_states = AsyncMock()
    api.get_entities_by_category = AsyncMock()
    api.get_history = AsyncMock()
    return api

@pytest.mark.asyncio
async def test_discover_entities(mock_api):
    """Test discover_entities function."""
    # Setup mock return value
    mock_api.get_states.return_value = [
        {'entity_id': 'light.living_room', 'state': 'on'},
        {'entity_id': 'light.kitchen', 'state': 'off'},
        {'entity_id': 'switch.tv', 'state': 'off'},
        {'entity_id': 'sensor.temperature', 'state': '22.5'},
    ]
    
    result = await discover_entities(mock_api)
    
    # Check that entities are correctly categorized by domain
    assert 'light' in result
    assert 'switch' in result
    assert 'sensor' in result
    assert len(result['light']) == 2
    assert len(result['switch']) == 1
    assert len(result['sensor']) == 1
    assert result['light'][0]['entity_id'] == 'light.living_room'
    assert result['light'][1]['entity_id'] == 'light.kitchen'
    assert result['switch'][0]['entity_id'] == 'switch.tv'
    assert result['sensor'][0]['entity_id'] == 'sensor.temperature'

@pytest.mark.asyncio
async def test_get_entity_groups(mock_api):
    """Test get_entity_groups function."""
    # Setup mock return value
    mock_api.get_entities_by_category.return_value = {
        'Living Room': {
            'light': ['light.living_room'],
            'switch': ['switch.tv']
        },
        'Kitchen': {
            'light': ['light.kitchen'],
            'sensor': ['sensor.temperature']
        }
    }
    
    result = await get_entity_groups(mock_api)
    
    # Check that we get the expected groups
    assert 'area.living_room' in result
    assert 'area.kitchen' in result
    assert 'area.living_room_light' in result
    assert 'area.living_room_switch' in result
    assert 'area.kitchen_light' in result
    assert 'area.kitchen_sensor' in result
    assert 'domain.light' in result
    assert 'domain.switch' in result
    assert 'domain.sensor' in result
    
    # Check that entities are in the correct groups
    assert 'light.living_room' in result['area.living_room']
    assert 'switch.tv' in result['area.living_room']
    assert 'light.kitchen' in result['area.kitchen']
    assert 'sensor.temperature' in result['area.kitchen']
    assert 'light.living_room' in result['area.living_room_light']
    assert 'switch.tv' in result['area.living_room_switch']
    assert 'light.kitchen' in result['area.kitchen_light']
    assert 'sensor.temperature' in result['area.kitchen_sensor']
    assert 'light.living_room' in result['domain.light']
    assert 'light.kitchen' in result['domain.light']
    assert 'switch.tv' in result['domain.switch']
    assert 'sensor.temperature' in result['domain.sensor']

@pytest.mark.asyncio
async def test_detect_entity_relationships(mock_api):
    """Test detect_entity_relationships function."""
    # Setup mock return value for get_states
    mock_api.get_states.return_value = [
        {'entity_id': 'light.living_room'},
        {'entity_id': 'switch.tv'},
        {'entity_id': 'binary_sensor.motion'}
    ]
    
    # Setup mock return value for get_history
    motion_time = datetime.now() - timedelta(hours=1)
    light_time = motion_time + timedelta(seconds=5)  # 5 seconds after motion
    
    mock_api.get_history.return_value = [
        [  # binary_sensor.motion history
            {
                'entity_id': 'binary_sensor.motion', 
                'state': 'on',
                'last_changed': motion_time.isoformat()
            }
        ],
        [  # light.living_room history
            {
                'entity_id': 'light.living_room', 
                'state': 'on',
                'last_changed': light_time.isoformat()
            }
        ],
        [  # switch.tv history - changed much later, shouldn't be related
            {
                'entity_id': 'switch.tv', 
                'state': 'on',
                'last_changed': (motion_time + timedelta(minutes=5)).isoformat()
            }
        ]
    ]
    
    result = await detect_entity_relationships(mock_api)
    
    # Check that we detected the relationship between motion and light
    assert 'binary_sensor.motion' in result
    assert 'light.living_room' in result
    assert 'light.living_room' in result['binary_sensor.motion']
    assert 'binary_sensor.motion' in result['light.living_room']
    
    # The TV shouldn't be related to anything
    if 'switch.tv' in result:
        assert len(result['switch.tv']) == 0

@pytest.mark.asyncio
async def test_get_entity_hierarchy(mock_api):
    """Test get_entity_hierarchy function."""
    # Setup mock return value for get_entities_by_category
    mock_api.get_entities_by_category.return_value = {
        'Living Room': {
            'light': ['light.living_room'],
            'switch': ['switch.tv']
        },
        'Kitchen': {
            'light': ['light.kitchen']
        }
    }
    
    # Setup mock return value for get_states
    mock_api.get_states.return_value = [
        {
            'entity_id': 'light.living_room', 
            'state': 'on',
            'attributes': {'friendly_name': 'Living Room Light'}
        },
        {
            'entity_id': 'switch.tv', 
            'state': 'off',
            'attributes': {'friendly_name': 'TV Switch'}
        },
        {
            'entity_id': 'light.kitchen', 
            'state': 'off',
            'attributes': {'friendly_name': 'Kitchen Light'}
        }
    ]
    
    result = await get_entity_hierarchy(mock_api)
    
    # Check the structure of the hierarchy
    assert 'areas' in result
    assert len(result['areas']) == 2
    
    # Find the Living Room area
    living_room = next((a for a in result['areas'] if a['name'] == 'Living Room'), None)
    assert living_room is not None
    assert 'domains' in living_room
    assert len(living_room['domains']) == 2
    
    # Check the light domain in Living Room
    light_domain = next((d for d in living_room['domains'] if d['name'] == 'light'), None)
    assert light_domain is not None
    assert 'entities' in light_domain
    assert len(light_domain['entities']) == 1
    assert light_domain['entities'][0]['entity_id'] == 'light.living_room'
    assert light_domain['entities'][0]['name'] == 'Living Room Light'
    assert light_domain['entities'][0]['state'] == 'on'

def test_get_entity_hierarchy_sync(mock_api):
    """Test get_entity_hierarchy_sync function."""
    # Setup mock return value for get_entities_sync
    mock_api.get_entities_sync.return_value = [
        {
            'entity_id': 'light.living_room', 
            'state': 'on',
            'attributes': {'friendly_name': 'Living Room Light'}
        },
        {
            'entity_id': 'switch.tv', 
            'state': 'off',
            'attributes': {'friendly_name': 'TV Switch'}
        }
    ]
    
    result = get_entity_hierarchy_sync(mock_api)
    
    # Check the structure of the hierarchy
    assert 'domains' in result
    assert len(result['domains']) == 2
    
    # Find the light domain
    light_domain = next((d for d in result['domains'] if d['name'] == 'light'), None)
    assert light_domain is not None
    assert 'entities' in light_domain
    assert len(light_domain['entities']) == 1
    assert light_domain['entities'][0]['entity_id'] == 'light.living_room'
    assert light_domain['entities'][0]['name'] == 'Living Room Light'
    assert light_domain['entities'][0]['state'] == 'on'

def test_get_domain_from_entity():
    """Test get_domain_from_entity function."""
    assert get_domain_from_entity('light.living_room') == 'light'
    assert get_domain_from_entity('switch.tv') == 'switch'
    assert get_domain_from_entity('sensor.temperature') == 'sensor'
    assert get_domain_from_entity('climate.thermostat') == 'climate'

def test_get_service_for_action():
    """Test get_service_for_action function."""
    # Test common actions
    assert get_service_for_action('light', 'turn_on') == ('light', 'turn_on')
    assert get_service_for_action('light', 'on') == ('light', 'turn_on')
    assert get_service_for_action('switch', 'turn_off') == ('switch', 'turn_off')
    assert get_service_for_action('switch', 'off') == ('switch', 'turn_off')
    assert get_service_for_action('light', 'toggle') == ('light', 'toggle')
    
    # Test domain-specific actions
    assert get_service_for_action('light', 'dim') == ('light', 'turn_on')
    assert get_service_for_action('cover', 'open') == ('cover', 'open_cover')
    assert get_service_for_action('climate', 'heat') == ('climate', 'set_temperature')
    assert get_service_for_action('media_player', 'play') == ('media_player', 'media_play')
    
    # Test fallback for unknown actions
    assert get_service_for_action('light', 'blink') == ('light', 'blink')