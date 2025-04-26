"""
Tests for the Claude Integration Tools for Home Assistant MCP.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from src.claude_integration.tools import (
    register_tools, get_entities, get_entity_state,
    control_entity, create_dashboard, validate_yaml,
    suggest_automations, generate_automation
)

@pytest.fixture
def config():
    """Fixture for tool configuration."""
    return {
        'home_assistant': {
            'url': 'http://test.local:8123',
            'token': 'test_token',
            'verify_ssl': True
        },
        'dashboard': {
            'default_theme': 'test_theme',
            'default_icon': 'mdi:test-icon'
        },
        'automation': {
            'suggestion_threshold': 3,
            'max_suggestions': 5
        }
    }

def test_register_tools(config):
    """Test registering Claude tools."""
    # Mock the component classes
    with patch('src.connection.api.HomeAssistantAPI') as mock_api, \
         patch('src.yaml_generator.dashboard.DashboardGenerator') as mock_dashboard, \
         patch('src.testing.validator.ConfigValidator') as mock_validator, \
         patch('src.automation.generator.AutomationGenerator') as mock_automation:
        
        tools = register_tools(config)
        
        # Check that all components were initialized
        assert mock_api.called
        assert mock_dashboard.called
        assert mock_validator.called
        assert mock_automation.called
        
        # Check that all expected tools are registered
        expected_tools = [
            'get_entities', 'get_entity_state', 'control_entity',
            'create_dashboard', 'validate_yaml',
            'suggest_automations', 'generate_automation'
        ]
        for tool in expected_tools:
            assert tool in tools

def test_get_entities():
    """Test get_entities tool."""
    # Mock the global api_client
    with patch('src.claude_integration.tools.api_client') as mock_api:
        entities = [
            {'entity_id': 'light.test', 'state': 'on'},
            {'entity_id': 'switch.test', 'state': 'off'}
        ]
        mock_api.get_entities_sync.return_value = entities
        
        result = get_entities()
        
        assert mock_api.get_entities_sync.called
        assert result['success'] is True
        assert result['entities'] == entities

def test_get_entity_state():
    """Test get_entity_state tool."""
    # Mock the global api_client
    with patch('src.claude_integration.tools.api_client') as mock_api:
        entities = [
            {'entity_id': 'light.test', 'state': 'on'},
            {'entity_id': 'switch.test', 'state': 'off'}
        ]
        mock_api.get_entities_sync.return_value = entities
        
        result = get_entity_state('light.test')
        
        assert mock_api.get_entities_sync.called
        assert result['success'] is True
        assert result['entity']['entity_id'] == 'light.test'
        assert result['entity']['state'] == 'on'

def test_get_entity_state_not_found():
    """Test get_entity_state tool with non-existent entity."""
    # Mock the global api_client
    with patch('src.claude_integration.tools.api_client') as mock_api:
        entities = [
            {'entity_id': 'light.test', 'state': 'on'},
            {'entity_id': 'switch.test', 'state': 'off'}
        ]
        mock_api.get_entities_sync.return_value = entities
        
        result = get_entity_state('light.nonexistent')
        
        assert mock_api.get_entities_sync.called
        assert result['success'] is False
        assert 'not found' in result['error']

def test_control_entity():
    """Test control_entity tool."""
    # Mock the global api_client
    with patch('src.claude_integration.tools.api_client') as mock_api:
        mock_api.call_service_sync.return_value = True
        
        result = control_entity('light.test', 'turn_on', {'brightness': 255})
        
        assert mock_api.call_service_sync.called
        mock_api.call_service_sync.assert_called_with('light', 'turn_on', 
                                                     {'entity_id': 'light.test', 'brightness': 255})
        assert result['success'] is True

def test_create_dashboard():
    """Test create_dashboard tool."""
    # Mock the global dashboard_generator and config_validator
    with patch('src.claude_integration.tools.dashboard_generator') as mock_generator, \
         patch('src.claude_integration.tools.config_validator') as mock_validator:
        
        yaml_content = "title: Test\nviews:\n  - title: Main"
        mock_generator.create_lovelace_dashboard.return_value = yaml_content
        mock_validator.validate_dashboard_config.return_value = (True, None)
        
        title = "Test Dashboard"
        views = [{"title": "Main View"}]
        
        result = create_dashboard(title, views)
        
        assert mock_generator.create_lovelace_dashboard.called
        assert mock_validator.validate_dashboard_config.called
        assert result['success'] is True
        assert result['yaml'] == yaml_content

def test_create_dashboard_invalid():
    """Test create_dashboard tool with invalid YAML."""
    # Mock the global dashboard_generator and config_validator
    with patch('src.claude_integration.tools.dashboard_generator') as mock_generator, \
         patch('src.claude_integration.tools.config_validator') as mock_validator:
        
        yaml_content = "title: Test\nviews:\n  - title: Main"
        mock_generator.create_lovelace_dashboard.return_value = yaml_content
        mock_validator.validate_dashboard_config.return_value = (False, "Missing required fields")
        
        title = "Test Dashboard"
        views = [{"title": "Main View"}]
        
        result = create_dashboard(title, views)
        
        assert mock_generator.create_lovelace_dashboard.called
        assert mock_validator.validate_dashboard_config.called
        assert result['success'] is False
        assert result['error'] == "Missing required fields"
        assert result['yaml'] == yaml_content

def test_validate_yaml_dashboard():
    """Test validate_yaml tool with dashboard configuration."""
    # Mock the global config_validator
    with patch('src.claude_integration.tools.config_validator') as mock_validator:
        mock_validator.validate_dashboard_config.return_value = (True, None)
        
        yaml_content = "title: Test\nviews:\n  - title: Main"
        
        result = validate_yaml(yaml_content, 'dashboard')
        
        assert mock_validator.validate_dashboard_config.called
        assert result['success'] is True
        assert result['error'] is None

def test_validate_yaml_automation():
    """Test validate_yaml tool with automation configuration."""
    # Mock the global config_validator
    with patch('src.claude_integration.tools.config_validator') as mock_validator:
        mock_validator.validate_automation_config.return_value = (True, None)
        
        yaml_content = "trigger:\n  platform: state\n  entity_id: binary_sensor.motion"
        
        result = validate_yaml(yaml_content, 'automation')
        
        assert mock_validator.validate_automation_config.called
        assert result['success'] is True
        assert result['error'] is None

def test_suggest_automations():
    """Test suggest_automations tool."""
    # Mock the global automation_generator
    with patch('src.claude_integration.tools.automation_generator') as mock_generator:
        patterns = [
            {
                'entity_id': 'light.living_room',
                'type': 'time',
                'trigger_time': '07:00',
                'action_state': 'on',
                'confidence': 0.9
            }
        ]
        mock_generator.analyze_entity_usage.return_value = patterns
        
        history_data = [
            {'entity_id': 'light.living_room', 'state': 'on', 'last_changed': '2023-01-01T07:00:00Z'}
        ]
        
        result = suggest_automations(history_data)
        
        assert mock_generator.analyze_entity_usage.called
        assert result['success'] is True
        assert result['suggestions'] == patterns

def test_generate_automation():
    """Test generate_automation tool."""
    # Mock the global automation_generator and config_validator
    with patch('src.claude_integration.tools.automation_generator') as mock_generator, \
         patch('src.claude_integration.tools.config_validator') as mock_validator:
        
        yaml_content = "trigger:\n  platform: time\n  at: '07:00'\naction:\n  service: light.turn_on"
        mock_generator.generate_automation_yaml.return_value = yaml_content
        mock_validator.validate_automation_config.return_value = (True, None)
        
        pattern = {
            'entity_id': 'light.living_room',
            'type': 'time',
            'trigger_time': '07:00',
            'action_state': 'on'
        }
        
        result = generate_automation(pattern)
        
        assert mock_generator.generate_automation_yaml.called
        assert mock_validator.validate_automation_config.called
        assert result['success'] is True
        assert result['yaml'] == yaml_content