"""
Test module for Claude Integration MCP interface.

This module tests the functionality of the Claude Integration MCP interface.
"""

import os
import sys
import unittest
import json
from unittest.mock import patch, MagicMock

# Add the root directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.claude_integration.mcp import HomeAssistantMCP


class TestHomeAssistantMCP(unittest.TestCase):
    """Test case for the HomeAssistantMCP class."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'home_assistant': {
                'url': 'http://homeassistant.local:8123',
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
        
        # Mock dependencies
        self.api_mock = MagicMock()
        self.dashboard_generator_mock = MagicMock()
        self.config_validator_mock = MagicMock()
        self.automation_tools_mock = MagicMock()
        
        # Apply patches
        self.api_patcher = patch('src.claude_integration.mcp.HomeAssistantAPI', return_value=self.api_mock)
        self.dashboard_patcher = patch('src.claude_integration.mcp.DashboardGenerator', return_value=self.dashboard_generator_mock)
        self.validator_patcher = patch('src.claude_integration.mcp.ConfigValidator', return_value=self.config_validator_mock)
        self.automation_patcher = patch('src.claude_integration.mcp.AutomationTools', return_value=self.automation_tools_mock)
        self.tools_patcher = patch('src.claude_integration.mcp.register_tools', return_value={
            'get_entities': {'function': MagicMock(return_value={'success': True})},
            'get_entity_state': {'function': MagicMock(return_value={'success': True})},
            'control_entity': {'function': MagicMock(return_value={'success': True})},
            'create_dashboard': {'function': MagicMock(return_value={'success': True})},
            'validate_yaml': {'function': MagicMock(return_value={'success': True})}
        })
        
        # Start patches
        self.api_patcher.start()
        self.dashboard_patcher.start()
        self.validator_patcher.start()
        self.automation_patcher.start()
        self.tools_patcher.start()
        
        # Create instance
        self.mcp = HomeAssistantMCP(self.config)
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Stop patches
        self.api_patcher.stop()
        self.dashboard_patcher.stop()
        self.validator_patcher.stop()
        self.automation_patcher.stop()
        self.tools_patcher.stop()
    
    def test_get_schemas(self):
        """Test the get_schemas method."""
        schemas = self.mcp.get_schemas()
        
        # Check schemas structure
        self.assertIsInstance(schemas, dict)
        self.assertIn('home_assistant_entity_control', schemas)
        self.assertIn('home_assistant_dashboard', schemas)
        self.assertIn('home_assistant_automation', schemas)
        self.assertIn('home_assistant_config', schemas)
        
        # Check parameters
        self.assertIn('parameters', schemas['home_assistant_entity_control'])
        self.assertIn('description', schemas['home_assistant_entity_control'])
    
    def test_process_entity_control(self):
        """Test the _process_entity_control method."""
        # Test get_entities
        result = self.mcp._process_entity_control({'action': 'get_entities'})
        self.assertTrue(result['success'])
        
        # Test get_entity_state
        result = self.mcp._process_entity_control({
            'action': 'get_entity_state', 
            'entity_id': 'light.living_room'
        })
        self.assertTrue(result['success'])
        
        # Test missing entity_id
        result = self.mcp._process_entity_control({'action': 'get_entity_state'})
        self.assertFalse(result['success'])
        
        # Test control_entity
        result = self.mcp._process_entity_control({
            'action': 'control_entity',
            'entity_id': 'light.living_room',
            'control_action': 'turn_on'
        })
        self.assertTrue(result['success'])
        
        # Test unknown action
        result = self.mcp._process_entity_control({'action': 'unknown_action'})
        self.assertFalse(result['success'])
    
    def test_process_dashboard(self):
        """Test the _process_dashboard method."""
        # Test create_dashboard
        result = self.mcp._process_dashboard({
            'action': 'create_dashboard',
            'title': 'My Dashboard',
            'views': [{'title': 'Main View'}]
        })
        self.assertTrue(result['success'])
        
        # Test missing title
        result = self.mcp._process_dashboard({
            'action': 'create_dashboard',
            'views': [{'title': 'Main View'}]
        })
        self.assertFalse(result['success'])
        
        # Test validate_dashboard
        result = self.mcp._process_dashboard({
            'action': 'validate_dashboard',
            'yaml_content': 'title: My Dashboard\nviews:\n  - title: Main View'
        })
        self.assertTrue(result['success'])
        
        # Test unknown action
        result = self.mcp._process_dashboard({'action': 'unknown_action'})
        self.assertFalse(result['success'])
    
    def test_process_request(self):
        """Test the process_request method."""
        # Test entity control
        result = self.mcp.process_request('home_assistant_entity_control', {'action': 'get_entities'})
        self.assertTrue(result['success'])
        
        # Test dashboard
        result = self.mcp.process_request('home_assistant_dashboard', {
            'action': 'create_dashboard',
            'title': 'My Dashboard',
            'views': [{'title': 'Main View'}]
        })
        self.assertTrue(result['success'])
        
        # Test unknown tool
        result = self.mcp.process_request('unknown_tool', {})
        self.assertFalse(result['success'])
        
        # Test exception handling
        with patch.object(self.mcp, '_process_entity_control', side_effect=Exception('Test error')):
            result = self.mcp.process_request('home_assistant_entity_control', {'action': 'get_entities'})
            self.assertFalse(result['success'])
            self.assertEqual(result['error'], 'Test error')


if __name__ == '__main__':
    unittest.main()
