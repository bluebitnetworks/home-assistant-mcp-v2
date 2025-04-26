"""
Tests for the Home Assistant Configuration Validator.
"""

import pytest
import yaml
from unittest.mock import patch, MagicMock
from src.testing.validator import ConfigValidator

@pytest.fixture
def config():
    """Fixture for validator configuration."""
    return {
        'home_assistant': {
            'url': 'http://test.local:8123',
            'token': 'test_token'
        }
    }

@pytest.fixture
def validator(config):
    """Fixture for ConfigValidator instance."""
    return ConfigValidator(config)

def test_validate_yaml_syntax_valid(validator):
    """Test YAML syntax validation with valid content."""
    valid_yaml = "key: value\nlist:\n  - item1\n  - item2"
    result, error = validator.validate_yaml_syntax(valid_yaml)
    assert result is True
    assert error is None

def test_validate_yaml_syntax_invalid(validator):
    """Test YAML syntax validation with invalid content."""
    invalid_yaml = "key: value\nlist:\n  - item1\n  -   invalid indent\n  more invalid"
    result, error = validator.validate_yaml_syntax(invalid_yaml)
    assert result is False
    assert error is not None
    assert "YAML syntax error" in error

def test_validate_dashboard_config_valid(validator):
    """Test dashboard configuration validation with valid content."""
    valid_dashboard = """
title: Test Dashboard
views:
  - title: Main View
    path: main
    cards:
      - type: entities
        entities:
          - light.test
    """
    result, error = validator.validate_dashboard_config(valid_dashboard)
    assert result is True
    assert error is None

def test_validate_dashboard_config_invalid_syntax(validator):
    """Test dashboard configuration validation with invalid syntax."""
    invalid_dashboard = """
title: Test Dashboard
views:
  - title: Main View
    path: main
    cards:
      - type: entities
        entities:
          - light.test
        invalid indent
    """
    result, error = validator.validate_dashboard_config(invalid_dashboard)
    assert result is False
    assert error is not None

def test_validate_dashboard_config_invalid_structure(validator):
    """Test dashboard configuration validation with invalid structure."""
    invalid_dashboard = """
title: Test Dashboard
# Missing views key
"""
    result, error = validator.validate_dashboard_config(invalid_dashboard)
    assert result is False
    assert error is not None
    assert "must contain 'views' key" in error

def test_validate_automation_config_valid(validator):
    """Test automation configuration validation with valid content."""
    valid_automation = """
id: test_automation
alias: Test Automation
trigger:
  platform: state
  entity_id: binary_sensor.motion
  to: 'on'
action:
  service: light.turn_on
  target:
    entity_id: light.test
"""
    result, error = validator.validate_automation_config(valid_automation)
    assert result is True
    assert error is None

def test_validate_automation_config_invalid_syntax(validator):
    """Test automation configuration validation with invalid syntax."""
    invalid_automation = """
id: test_automation
alias: Test Automation
trigger:
  platform: state
  entity_id: binary_sensor.motion
  to: 'on'
action:
  service: light.turn_on
  target:
    entity_id: light.test
  invalid indent
"""
    result, error = validator.validate_automation_config(invalid_automation)
    assert result is False
    assert error is not None

def test_validate_automation_config_invalid_structure(validator):
    """Test automation configuration validation with invalid structure."""
    invalid_automation = """
id: test_automation
alias: Test Automation
# Missing trigger key
action:
  service: light.turn_on
  target:
    entity_id: light.test
"""
    result, error = validator.validate_automation_config(invalid_automation)
    assert result is False
    assert error is not None
    assert "missing required keys" in error

def test_validate_automation_config_multiple(validator):
    """Test automation configuration validation with multiple automations."""
    multiple_automations = """
- id: test_automation_1
  alias: Test Automation 1
  trigger:
    platform: state
    entity_id: binary_sensor.motion
    to: 'on'
  action:
    service: light.turn_on
    target:
      entity_id: light.test
- id: test_automation_2
  alias: Test Automation 2
  trigger:
    platform: time
    at: '07:00:00'
  action:
    service: light.turn_on
    target:
      entity_id: light.bedroom
"""
    result, error = validator.validate_automation_config(multiple_automations)
    assert result is True
    assert error is None