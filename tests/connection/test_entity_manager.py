"""
Tests for the Home Assistant Entity Manager.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from src.connection.api import HomeAssistantAPI
from src.connection.entity_manager import EntityManager

@pytest.fixture
def mock_api():
    """Fixture for mocked HomeAssistantAPI."""
    api = MagicMock(spec=HomeAssistantAPI)
    # Configure necessary async methods as AsyncMock
    api.get_states = AsyncMock()
    api.get_entity_state = AsyncMock()
    api.call_service = AsyncMock()
    api.get_entity_capabilities = AsyncMock()
    
    # Configure sync methods
    api.get_entities_sync = MagicMock()
    api.get_entity_state_sync = MagicMock()
    api.call_service_sync = MagicMock()
    
    return api

@pytest.fixture
def entity_manager(mock_api):
    """Fixture for EntityManager with mocked API."""
    return EntityManager(mock_api)

@pytest.mark.asyncio
async def test_refresh_entities(entity_manager, mock_api):
    """Test refreshing entities."""
    # Setup mock return value
    mock_api.get_states.return_value = [
        {'entity_id': 'light.living_room', 'state': 'on'},
        {'entity_id': 'switch.tv', 'state': 'off'}
    ]
    
    await entity_manager.refresh_entities()
    
    # Check that the cache was updated
    assert 'light.living_room' in entity_manager._entity_cache
    assert 'switch.tv' in entity_manager._entity_cache
    assert entity_manager._entity_cache['light.living_room']['state'] == 'on'
    assert entity_manager._entity_cache['switch.tv']['state'] == 'off'
    assert entity_manager._last_update is not None

def test_refresh_entities_sync(entity_manager, mock_api):
    """Test synchronous refreshing of entities."""
    # Setup mock return value
    mock_api.get_entities_sync.return_value = [
        {'entity_id': 'light.living_room', 'state': 'on'},
        {'entity_id': 'switch.tv', 'state': 'off'}
    ]
    
    entity_manager.refresh_entities_sync()
    
    # Check that the cache was updated
    assert 'light.living_room' in entity_manager._entity_cache
    assert 'switch.tv' in entity_manager._entity_cache
    assert entity_manager._entity_cache['light.living_room']['state'] == 'on'
    assert entity_manager._entity_cache['switch.tv']['state'] == 'off'
    assert entity_manager._last_update is not None

@pytest.mark.asyncio
async def test_get_entity_from_cache(entity_manager):
    """Test getting an entity from cache."""
    # Setup cache
    entity_manager._entity_cache = {
        'light.living_room': {'entity_id': 'light.living_room', 'state': 'on'}
    }
    entity_manager._last_update = datetime.now()
    
    entity = await entity_manager.get_entity('light.living_room')
    
    assert entity is not None
    assert entity['entity_id'] == 'light.living_room'
    assert entity['state'] == 'on'

@pytest.mark.asyncio
async def test_get_entity_from_api(entity_manager, mock_api):
    """Test getting an entity from API when not in cache."""
    # Empty cache
    entity_manager._entity_cache = {}
    entity_manager._last_update = None
    
    # Setup mock return value
    mock_api.get_states.return_value = []  # Empty for initial refresh
    mock_api.get_entity_state.return_value = {'entity_id': 'light.living_room', 'state': 'on'}
    
    entity = await entity_manager.get_entity('light.living_room')
    
    assert entity is not None
    assert entity['entity_id'] == 'light.living_room'
    assert entity['state'] == 'on'
    assert mock_api.get_entity_state.called
    assert 'light.living_room' in entity_manager._entity_cache

@pytest.mark.asyncio
async def test_get_all_entities(entity_manager, mock_api):
    """Test getting all entities."""
    # Setup mock return value
    mock_api.get_states.return_value = [
        {'entity_id': 'light.living_room', 'state': 'on'},
        {'entity_id': 'switch.tv', 'state': 'off'}
    ]
    
    entities = await entity_manager.get_all_entities()
    
    assert len(entities) == 2
    assert any(e['entity_id'] == 'light.living_room' for e in entities)
    assert any(e['entity_id'] == 'switch.tv' for e in entities)

@pytest.mark.asyncio
async def test_get_entities_by_domain(entity_manager, mock_api):
    """Test getting entities by domain."""
    # Setup mock return value
    mock_api.get_states.return_value = [
        {'entity_id': 'light.living_room', 'state': 'on'},
        {'entity_id': 'light.kitchen', 'state': 'off'},
        {'entity_id': 'switch.tv', 'state': 'off'}
    ]
    
    entities = await entity_manager.get_entities_by_domain('light')
    
    assert len(entities) == 2
    assert all(e['entity_id'].startswith('light.') for e in entities)

@pytest.mark.asyncio
async def test_get_entity_state(entity_manager):
    """Test getting entity state."""
    # Setup cache
    entity_manager._entity_cache = {
        'light.living_room': {
            'entity_id': 'light.living_room', 
            'state': 'on'
        }
    }
    entity_manager._last_update = datetime.now()
    
    state = await entity_manager.get_entity_state('light.living_room')
    
    assert state == 'on'

@pytest.mark.asyncio
async def test_get_entity_attributes(entity_manager):
    """Test getting entity attributes."""
    # Setup cache
    entity_manager._entity_cache = {
        'light.living_room': {
            'entity_id': 'light.living_room', 
            'state': 'on',
            'attributes': {
                'friendly_name': 'Living Room Light',
                'brightness': 255
            }
        }
    }
    entity_manager._last_update = datetime.now()
    
    attributes = await entity_manager.get_entity_attributes('light.living_room')
    
    assert attributes.get('friendly_name') == 'Living Room Light'
    assert attributes.get('brightness') == 255

@pytest.mark.asyncio
async def test_get_entity_name(entity_manager):
    """Test getting entity friendly name."""
    # Setup cache
    entity_manager._entity_cache = {
        'light.living_room': {
            'entity_id': 'light.living_room', 
            'state': 'on',
            'attributes': {
                'friendly_name': 'Living Room Light'
            }
        }
    }
    entity_manager._last_update = datetime.now()
    
    name = await entity_manager.get_entity_name('light.living_room')
    
    assert name == 'Living Room Light'

@pytest.mark.asyncio
async def test_control_entity(entity_manager, mock_api):
    """Test controlling an entity."""
    # Setup mocks
    mock_api.call_service.return_value = True
    mock_api.get_entity_state.return_value = {
        'entity_id': 'light.living_room', 
        'state': 'on'
    }
    
    # Call the method
    result = await entity_manager.control_entity('light.living_room', 'turn_on', {'brightness': 255})
    
    # Check the result
    assert result is True
    assert mock_api.call_service.called
    # Check that the service was called with the right parameters
    mock_api.call_service.assert_called_with(
        'light', 'turn_on', {'entity_id': 'light.living_room', 'brightness': 255}
    )
    # Check that the cache was updated
    assert 'light.living_room' in entity_manager._entity_cache
    assert entity_manager._entity_cache['light.living_room']['state'] == 'on'

@pytest.mark.asyncio
async def test_search_entities(entity_manager):
    """Test searching for entities."""
    # Setup cache
    entity_manager._entity_cache = {
        'light.living_room': {
            'entity_id': 'light.living_room', 
            'state': 'on',
            'attributes': {
                'friendly_name': 'Living Room Light'
            }
        },
        'light.kitchen': {
            'entity_id': 'light.kitchen', 
            'state': 'off',
            'attributes': {
                'friendly_name': 'Kitchen Light'
            }
        },
        'switch.tv': {
            'entity_id': 'switch.tv', 
            'state': 'off',
            'attributes': {
                'friendly_name': 'TV Switch'
            }
        }
    }
    entity_manager._last_update = datetime.now()
    
    # Search for lights
    results = await entity_manager.search_entities('light')
    
    assert len(results) == 2
    assert all(e['entity_id'].startswith('light.') for e in results)
    
    # Search by friendly name
    results = await entity_manager.search_entities('kitchen')
    
    assert len(results) == 1
    assert results[0]['entity_id'] == 'light.kitchen'

@pytest.mark.asyncio
async def test_get_entity_capability(entity_manager, mock_api):
    """Test getting entity capabilities."""
    # Setup mock
    mock_api.get_entity_capabilities.return_value = {
        'can_toggle': True,
        'can_dim': True,
        'can_color': False,
        'has_temperature': False,
        'has_humidity': False,
        'has_motion': False,
        'has_binary_state': True,
        'supports_services': ['turn_on', 'turn_off', 'toggle']
    }
    
    capabilities = await entity_manager.get_entity_capability('light.living_room')
    
    assert capabilities['can_toggle'] is True
    assert capabilities['can_dim'] is True
    assert capabilities['can_color'] is False
    assert capabilities['has_binary_state'] is True
    assert 'turn_on' in capabilities['supports_services']
    
    # Check that the capabilities were cached
    assert 'light.living_room' in entity_manager._entity_capabilities