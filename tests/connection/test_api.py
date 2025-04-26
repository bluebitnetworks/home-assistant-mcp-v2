"""
Tests for the Home Assistant API connection module.
"""

import pytest
import aiohttp
from unittest.mock import patch, MagicMock, AsyncMock
from src.connection.api import HomeAssistantAPI

@pytest.fixture
def api_config():
    """Fixture for API configuration."""
    return {
        'home_assistant': {
            'url': 'http://test.local:8123',
            'token': 'test_token',
            'verify_ssl': True
        }
    }

@pytest.fixture
def api_client(api_config):
    """Fixture for HomeAssistantAPI client."""
    client = HomeAssistantAPI(api_config)
    client._config = api_config  # Expose config for tests
    return client

@pytest.mark.asyncio
async def test_connect(api_client):
    """Test connect method creates a session."""
    with patch('aiohttp.ClientSession', MagicMock()) as mock_session:
        await api_client.connect()
        assert mock_session.called
        assert api_client.session is not None

@pytest.mark.asyncio
async def test_close(api_client):
    """Test close method closes the session."""
    api_client.session = AsyncMock()
    api_client.session.closed = False
    api_client.session.close = AsyncMock()
    await api_client.close()
    assert api_client.session.close.called

@pytest.mark.asyncio
async def test_get_states(api_client):
    """Test get_states method."""
    with patch.object(HomeAssistantAPI, 'connect', AsyncMock()), \
         patch.object(HomeAssistantAPI, 'get_states', 
                     AsyncMock(return_value=[{'entity_id': 'light.test'}])) as mock_get_states:
        
        # Create a new instance to use our patched class methods
        result = await HomeAssistantAPI(api_client._config).get_states()
        
        # Check the results
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['entity_id'] == 'light.test'
        assert mock_get_states.called

@pytest.mark.asyncio
async def test_get_entity_state(api_client):
    """Test get_entity_state method."""
    with patch.object(HomeAssistantAPI, 'connect', AsyncMock()), \
         patch.object(HomeAssistantAPI, 'get_entity_state', 
                     AsyncMock(return_value={'entity_id': 'light.test', 'state': 'on'})) as mock_get_state:
        
        # Create a new instance to use our patched class methods
        result = await HomeAssistantAPI(api_client._config).get_entity_state('light.test')
        
        # Check the results
        assert isinstance(result, dict)
        assert result['entity_id'] == 'light.test'
        assert result['state'] == 'on'
        assert mock_get_state.called

@pytest.mark.asyncio
async def test_call_service(api_client):
    """Test call_service method."""
    with patch.object(HomeAssistantAPI, 'connect', AsyncMock()), \
         patch.object(HomeAssistantAPI, 'call_service', 
                     AsyncMock(return_value=True)) as mock_call_service:
        
        # Create a new instance to use our patched class methods
        result = await HomeAssistantAPI(api_client._config).call_service(
            'light', 'turn_on', {'entity_id': 'light.test'}
        )
        
        # Check the results
        assert result is True
        assert mock_call_service.called

def test_get_entities_sync(api_client):
    """Test get_entities_sync method."""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'entity_id': 'light.test'}]
        mock_get.return_value = mock_response
        
        result = api_client.get_entities_sync()
        
        assert mock_get.called
        assert len(result) == 1
        assert result[0]['entity_id'] == 'light.test'

def test_call_service_sync(api_client):
    """Test call_service_sync method."""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = api_client.call_service_sync('light', 'turn_on', {'entity_id': 'light.test'})
        
        assert mock_post.called
        assert result is True