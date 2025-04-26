"""
Integration tests for the Automation and Testing modules.

This module tests the integration between the Automation Management module
and the Testing/Validation module for automation creation and validation.
"""

import os
import sys
import pytest
import yaml
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Add the root directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.automation.generator import AutomationGenerator
from src.automation.manager import AutomationManager
from src.testing.validator import ConfigValidator
from src.automation.test_runner import AutomationTestRunner


@pytest.fixture
def config():
    """Fixture for test configuration."""
    return {
        'home_assistant': {
            'url': 'http://test.local:8123',
            'token': 'test_token',
            'verify_ssl': False
        },
        'automation': {
            'suggestion_threshold': 3,
            'max_suggestions': 5
        }
    }


@pytest.fixture
def mock_api():
    """Fixture for mock Home Assistant API."""
    mock_api = AsyncMock()
    mock_api.get_states.return_value = [
        {
            'entity_id': 'light.living_room',
            'state': 'on',
            'attributes': {'friendly_name': 'Living Room Light'}
        },
        {
            'entity_id': 'binary_sensor.motion',
            'state': 'off',
            'attributes': {'friendly_name': 'Motion Sensor'}
        }
    ]
    mock_api.call_service = AsyncMock()
    return mock_api


@pytest.fixture
def automation_yaml():
    """Fixture for sample automation YAML."""
    return """
id: test_automation
alias: "Test Automation"
description: "Test automation for motion-activated light"
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: 'on'
condition: []
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
mode: single
"""


@pytest.mark.asyncio
async def test_automation_generator_with_validator(config):
    """
    Test that the AutomationGenerator creates valid automations according to ConfigValidator.
    """
    # Create instances with mocks
    with patch('src.testing.validator.ConfigValidator') as mock_validator_class:
        mock_validator = MagicMock()
        mock_validator.validate_yaml.return_value = {'valid': True, 'errors': []}
        mock_validator_class.return_value = mock_validator
        
        automation_generator = AutomationGenerator(config)
        
        # Generate a time-based automation
        pattern = {
            'type': 'time',
            'entity_id': 'light.living_room',
            'state': 'on',
            'time': '07:00:00',
            'days': ['mon', 'tue', 'wed', 'thu', 'fri']
        }
        
        automation_yaml = automation_generator.generate_automation_yaml(pattern)
        
        # Validate the automation
        result = mock_validator.validate_yaml(automation_yaml, 'automation')
        
        # Check that validation was called and returned valid
        assert mock_validator.validate_yaml.called
        assert result['valid']


@pytest.mark.asyncio
async def test_automation_test_runner_with_generator(config, mock_api, automation_yaml):
    """
    Test that the AutomationTestRunner properly validates automations created by the generator.
    """
    # Create instances with mocks
    with patch('src.connection.api.HomeAssistantAPI', return_value=mock_api):
        # Initialize components
        test_runner = AutomationTestRunner(config, mock_api)
        
        # Patch the test_runner's methods
        with patch.object(test_runner, 'validate_automation_yaml') as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'errors': [],
                'warnings': []
            }
            
            with patch.object(test_runner, 'test_trigger') as mock_test_trigger:
                mock_test_trigger.return_value = {
                    'success': True,
                    'triggered': True,
                    'entity_states': {
                        'binary_sensor.motion': 'on',
                        'light.living_room': 'on'
                    }
                }
                
                # Test validation and execution prediction
                validation_result = await test_runner.validate_automation_yaml(automation_yaml)
                assert validation_result['valid']
                
                # Test trigger testing
                trigger_result = await test_runner.test_trigger(yaml.safe_load(automation_yaml))
                assert trigger_result['success']
                assert trigger_result['triggered']


@pytest.mark.asyncio
async def test_automation_manager_with_validator(config, mock_api, automation_yaml):
    """
    Test that the AutomationManager validates before saving automations.
    """
    # Create instances with mocks
    with patch('src.connection.api.HomeAssistantAPI', return_value=mock_api):
        # Create a mock validator
        with patch('src.testing.validator.ConfigValidator') as mock_validator_class:
            mock_validator = MagicMock()
            mock_validator.validate_yaml.return_value = {'valid': True, 'errors': []}
            mock_validator_class.return_value = mock_validator
            
            # Create the automation manager
            automation_manager = AutomationManager(config, mock_api)
            
            # Patch the save method to avoid actual API calls
            with patch.object(automation_manager, '_save_automation_to_ha') as mock_save:
                mock_save.return_value = True
                
                # Test saving an automation
                automation = yaml.safe_load(automation_yaml)
                result = await automation_manager.save_automation(automation)
                
                # Check that validation was called
                assert mock_validator.validate_yaml.called
                assert result is True


@pytest.mark.asyncio
async def test_end_to_end_automation_workflow(config, mock_api):
    """
    Test the end-to-end workflow of generating, validating, testing, and saving an automation.
    """
    # Create instances with mocks
    with patch('src.connection.api.HomeAssistantAPI', return_value=mock_api):
        # Create a pattern for automation generation
        pattern = {
            'type': 'state',
            'trigger_entity_id': 'binary_sensor.motion',
            'trigger_state': 'on',
            'action_entity_id': 'light.living_room',
            'action_state': 'on'
        }
        
        # Create the components
        generator = AutomationGenerator(config)
        validator = ConfigValidator(config)
        test_runner = AutomationTestRunner(config, mock_api)
        
        # Patch the test_runner and validator methods
        with patch.object(validator, 'validate_yaml') as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'errors': []
            }
            
            with patch.object(test_runner, 'test_trigger') as mock_test_trigger:
                mock_test_trigger.return_value = {
                    'success': True,
                    'triggered': True,
                    'entity_states': {
                        'binary_sensor.motion': 'on',
                        'light.living_room': 'on'
                    }
                }
                
                # Generate the automation
                automation_yaml = generator.generate_automation_yaml(pattern)
                
                # Validate the automation
                validation_result = validator.validate_yaml(automation_yaml, 'automation')
                assert validation_result['valid']
                
                # Test the trigger
                automation = yaml.safe_load(automation_yaml)
                trigger_result = await test_runner.test_trigger(automation)
                assert trigger_result['success']
                
                # Create manager and mock save
                automation_manager = AutomationManager(config, mock_api)
                with patch.object(automation_manager, '_save_automation_to_ha') as mock_save:
                    mock_save.return_value = True
                    
                    # Save the automation
                    save_result = await automation_manager.save_automation(automation)
                    assert save_result is True
