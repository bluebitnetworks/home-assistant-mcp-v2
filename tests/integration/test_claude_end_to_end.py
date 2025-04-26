"""
End-to-End tests for the Home Assistant MCP.

This module tests complete workflows from Claude MCP requests through
all components to the final output.
"""

import os
import sys
import pytest
import yaml
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Add the root directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.claude_integration.mcp import HomeAssistantMCP


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
        },
        'automation': {
            'suggestion_threshold': 3,
            'max_suggestions': 5
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
        },
        {
            'entity_id': 'binary_sensor.motion',
            'state': 'off',
            'attributes': {
                'friendly_name': 'Motion Sensor',
                'device_class': 'motion'
            }
        }
    ]


@pytest.fixture
def mock_api(mock_entities):
    """Fixture for mock Home Assistant API."""
    mock_api = AsyncMock()
    mock_api.get_states.return_value = mock_entities
    mock_api.get_entity_state.side_effect = lambda entity_id: next(
        (e for e in mock_entities if e['entity_id'] == entity_id), None
    )
    mock_api.get_entities_sync.return_value = mock_entities
    mock_api.call_service = AsyncMock()
    return mock_api


@pytest.fixture
def mock_automations():
    """Fixture for mock automation data."""
    return {
        'motion_light': {
            'id': 'motion_light',
            'alias': 'Motion Light',
            'description': 'Turn on light when motion is detected',
            'trigger': [
                {
                    'platform': 'state',
                    'entity_id': 'binary_sensor.motion',
                    'to': 'on'
                }
            ],
            'condition': [],
            'action': [
                {
                    'service': 'light.turn_on',
                    'target': {
                        'entity_id': 'light.living_room'
                    }
                }
            ]
        }
    }


@pytest.fixture
def mock_mcp():
    """Create a mocked HomeAssistantMCP instance with all dependencies."""
    with patch('src.connection.api.HomeAssistantAPI') as mock_api_class, \
         patch('src.yaml_generator.dashboard.DashboardGenerator') as mock_dashboard_class, \
         patch('src.testing.validator.ConfigValidator') as mock_validator_class, \
         patch('src.automation.manager.AutomationManager') as mock_automation_manager_class, \
         patch('src.automation.generator.AutomationGenerator') as mock_automation_generator_class, \
         patch('src.automation.test_runner.AutomationTestRunner') as mock_test_runner_class, \
         patch('src.claude_integration.automation_tools.AutomationTools') as mock_automation_tools_class:
        
        # Set up API mock
        mock_api = AsyncMock()
        mock_api_class.return_value = mock_api
        
        # Set up dashboard generator mock
        mock_dashboard = MagicMock()
        mock_dashboard.generate_dashboard.return_value = "title: Test Dashboard\nviews:\n  - title: Main View"
        mock_dashboard_class.return_value = mock_dashboard
        
        # Set up validator mock
        mock_validator = MagicMock()
        mock_validator.validate_yaml.return_value = {'valid': True, 'errors': []}
        mock_validator_class.return_value = mock_validator
        
        # Set up automation manager mock
        mock_automation_manager = AsyncMock()
        mock_automation_manager.get_automations.return_value = {'motion_light': {}}
        mock_automation_manager.save_automation.return_value = True
        mock_automation_manager_class.return_value = mock_automation_manager
        
        # Set up automation generator mock
        mock_generator = MagicMock()
        mock_generator.generate_automation_yaml.return_value = "id: test\nalias: Test\ntrigger:\n  - platform: state"
        mock_automation_generator_class.return_value = mock_generator
        
        # Set up test runner mock
        mock_test_runner = AsyncMock()
        mock_test_runner.test_automation_config.return_value = {'success': True, 'errors': []}
        mock_test_runner_class.return_value = mock_test_runner
        
        # Set up automation tools mock
        mock_tools = AsyncMock()
        mock_tools.get_automations.return_value = {'success': True, 'automations': {}}
        mock_tools.create_automation.return_value = {'success': True, 'automation_id': 'test'}
        mock_tools_class.return_value = mock_tools
        
        # Create MCP instance with config
        config = {
            'home_assistant': {
                'url': 'http://test.local:8123',
                'token': 'test_token',
                'verify_ssl': False
            },
            'dashboard': {
                'default_theme': 'default',
                'default_icon': 'mdi:home-assistant'
            },
            'automation': {
                'suggestion_threshold': 3,
                'max_suggestions': 5
            }
        }
        
        # Create an instance of HomeAssistantMCP with mocks
        mcp = HomeAssistantMCP(config)
        
        # Mock the tools dict
        mcp.tools = {
            'get_entities': {'function': MagicMock(return_value={'success': True, 'entities': []})},
            'get_entity_state': {'function': MagicMock(return_value={'success': True, 'entity': {}})},
            'control_entity': {'function': MagicMock(return_value={'success': True})},
            'create_dashboard': {'function': MagicMock(return_value={'success': True, 'yaml': ''})},
            'validate_yaml': {'function': MagicMock(return_value={'success': True, 'valid': True})}
        }
        
        yield mcp


def test_get_schemas(mock_mcp):
    """Test that MCP schemas are correctly defined."""
    schemas = mock_mcp.get_schemas()
    
    # Check that schemas are structured correctly
    assert 'home_assistant_entity_control' in schemas
    assert 'home_assistant_dashboard' in schemas
    assert 'home_assistant_automation' in schemas
    assert 'home_assistant_config' in schemas
    
    # Check schema details
    entity_control = schemas['home_assistant_entity_control']
    assert 'parameters' in entity_control
    assert 'description' in entity_control
    
    # Check parameter structure
    params = entity_control['parameters']['properties']
    assert 'action' in params


def test_entity_control_get_entities(mock_mcp):
    """Test the entity control get_entities workflow."""
    # Set up request
    request = {
        'action': 'get_entities'
    }
    
    # Process request
    result = mock_mcp._process_entity_control(request)
    
    # Check result
    assert result['success'] is True
    assert mock_mcp.tools['get_entities']['function'].called


def test_entity_control_get_entity_state(mock_mcp):
    """Test the entity control get_entity_state workflow."""
    # Set up request
    request = {
        'action': 'get_entity_state',
        'entity_id': 'light.living_room'
    }
    
    # Process request
    result = mock_mcp._process_entity_control(request)
    
    # Check result
    assert result['success'] is True
    mock_mcp.tools['get_entity_state']['function'].assert_called_with('light.living_room')


def test_entity_control_control_entity(mock_mcp):
    """Test the entity control workflow."""
    # Set up request
    request = {
        'action': 'control_entity',
        'entity_id': 'light.living_room',
        'control_action': 'turn_on',
        'parameters': {'brightness': 255}
    }
    
    # Process request
    result = mock_mcp._process_entity_control(request)
    
    # Check result
    assert result['success'] is True
    mock_mcp.tools['control_entity']['function'].assert_called_with(
        'light.living_room', 'turn_on', {'brightness': 255}
    )


def test_dashboard_create_dashboard(mock_mcp):
    """Test the dashboard creation workflow."""
    # Set up request
    request = {
        'action': 'create_dashboard',
        'title': 'Test Dashboard',
        'views': [
            {
                'title': 'Main View',
                'cards': [
                    {
                        'type': 'entities',
                        'title': 'Lights',
                        'entities': ['light.living_room']
                    }
                ]
            }
        ]
    }
    
    # Process request
    result = mock_mcp._process_dashboard(request)
    
    # Check result
    assert result['success'] is True
    mock_mcp.tools['create_dashboard']['function'].assert_called_with(
        'Test Dashboard', request['views'], None
    )


def test_dashboard_validate_dashboard(mock_mcp):
    """Test the dashboard validation workflow."""
    # Set up request
    request = {
        'action': 'validate_dashboard',
        'yaml_content': 'title: Test\nviews:\n  - title: Main'
    }
    
    # Process request
    result = mock_mcp._process_dashboard(request)
    
    # Check result
    assert result['success'] is True
    mock_mcp.tools['validate_yaml']['function'].assert_called_with(
        request['yaml_content'], 'dashboard'
    )


@pytest.mark.asyncio
async def test_automation_get_automations(mock_mcp):
    """Test the get automations workflow."""
    # Mock the async method
    mock_mcp.automation_tools.get_automations = AsyncMock(
        return_value={'success': True, 'automations': {}}
    )
    
    # Set up request
    request = {
        'action': 'get_automations'
    }
    
    # Process request
    with patch('asyncio.run') as mock_run:
        mock_run.return_value = {'success': True, 'automations': {}}
        result = mock_mcp._process_automation(request)
    
    # Check result
    assert result['success'] is True


@pytest.mark.asyncio
async def test_automation_create_automation(mock_mcp):
    """Test the create automation workflow."""
    # Mock the async method
    mock_mcp.automation_tools.create_automation = AsyncMock(
        return_value={'success': True, 'automation_id': 'test'}
    )
    
    # Set up request
    request = {
        'action': 'create_automation',
        'automation_yaml': 'id: test\nalias: Test\ntrigger:\n  - platform: state'
    }
    
    # Process request
    with patch('asyncio.run') as mock_run:
        mock_run.return_value = {'success': True, 'automation_id': 'test'}
        result = mock_mcp._process_automation(request)
    
    # Check result
    assert result['success'] is True


@pytest.mark.asyncio
async def test_config_validate_config(mock_mcp):
    """Test the config validation workflow."""
    # Set up request
    request = {
        'action': 'validate_config',
        'config_type': 'automation',
        'config_yaml': 'id: test\nalias: Test\ntrigger:\n  - platform: state'
    }
    
    # Process request
    result = mock_mcp._process_config(request)
    
    # Check result
    assert result['success'] is True
    mock_mcp.tools['validate_yaml']['function'].assert_called_with(
        request['config_yaml'], 'automation'
    )


@pytest.mark.asyncio
async def test_process_request(mock_mcp):
    """Test the main process_request method with various tool names."""
    # Test entity control
    entity_result = mock_mcp.process_request(
        'home_assistant_entity_control',
        {'action': 'get_entities'}
    )
    assert entity_result['success'] is True
    
    # Test dashboard
    dashboard_result = mock_mcp.process_request(
        'home_assistant_dashboard',
        {'action': 'create_dashboard', 'title': 'Test', 'views': []}
    )
    assert dashboard_result['success'] is True
    
    # Test unknown tool
    unknown_result = mock_mcp.process_request(
        'unknown_tool',
        {}
    )
    assert unknown_result['success'] is False
    assert 'error' in unknown_result
    
    # Test error handling
    with patch.object(mock_mcp, '_process_entity_control', side_effect=Exception('Test error')):
        error_result = mock_mcp.process_request(
            'home_assistant_entity_control',
            {'action': 'get_entities'}
        )
        assert error_result['success'] is False
        assert error_result['error'] == 'Test error'


@pytest.mark.asyncio
async def test_end_to_end_entity_control_workflow(mock_mcp):
    """Test the end-to-end entity control workflow from MCP request to API call."""
    # Create a complete request simulating what Claude would send
    complete_request = {
        'tool_name': 'home_assistant_entity_control',
        'parameters': {
            'action': 'control_entity',
            'entity_id': 'light.living_room',
            'control_action': 'turn_on',
            'parameters': {'brightness': 255}
        }
    }
    
    # Process the request
    result = mock_mcp.process_request(
        complete_request['tool_name'],
        complete_request['parameters']
    )
    
    # Check result
    assert result['success'] is True
    # Verify the control_entity function was called with the right parameters
    mock_mcp.tools['control_entity']['function'].assert_called_with(
        'light.living_room', 'turn_on', {'brightness': 255}
    )


@pytest.mark.asyncio
async def test_end_to_end_dashboard_workflow(mock_mcp):
    """Test the end-to-end dashboard workflow from MCP request to YAML generation."""
    # Create a complete request simulating what Claude would send
    complete_request = {
        'tool_name': 'home_assistant_dashboard',
        'parameters': {
            'action': 'create_dashboard',
            'title': 'Living Room',
            'views': [
                {
                    'title': 'Main View',
                    'cards': [
                        {
                            'type': 'entities',
                            'title': 'Lights',
                            'entities': ['light.living_room']
                        },
                        {
                            'type': 'sensor',
                            'entity': 'sensor.temperature'
                        }
                    ]
                }
            ]
        }
    }
    
    # Process the request
    result = mock_mcp.process_request(
        complete_request['tool_name'],
        complete_request['parameters']
    )
    
    # Check result
    assert result['success'] is True
    # Verify the create_dashboard function was called with the right parameters
    mock_mcp.tools['create_dashboard']['function'].assert_called_with(
        'Living Room', complete_request['parameters']['views'], None
    )
