"""
Tests for the Home Assistant Configuration Testing Module.
"""

import unittest
import asyncio
import os
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.testing.validator import ConfigValidator
from src.testing.advanced_validator import AdvancedValidator
from src.testing.config_analyzer import ConfigAnalyzer
from src.testing.test_runner import ConfigTestRunner


class TestConfigValidator(unittest.TestCase):
    """Test cases for ConfigValidator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'home_assistant': {
                'url': 'http://localhost:8123',
                'token': 'test_token'
            }
        }
        self.validator = ConfigValidator(self.config)
        
        # Sample YAML contents for testing
        self.valid_dashboard_yaml = """
title: My Dashboard
views:
  - title: Main
    path: main
    cards:
      - type: entities
        title: Entities
        entities:
          - light.living_room
          - switch.kitchen
  - title: Secondary
    path: secondary
    cards:
      - type: weather-forecast
        entity: weather.home
"""
        
        self.invalid_dashboard_yaml = """
title: Invalid Dashboard
views:
  - title: Main
    path: main
    cards: not-a-list
"""
        
        self.valid_automation_yaml = """
- id: test_automation
  alias: Test Automation
  description: A test automation
  trigger:
    - platform: state
      entity_id: light.living_room
      to: 'on'
  condition:
    - condition: time
      after: '08:00:00'
      before: '23:00:00'
  action:
    - service: light.turn_on
      target:
        entity_id: light.kitchen
"""
        
        self.invalid_automation_yaml = """
- id: invalid_automation
  alias: Invalid Automation
  trigger: not-a-dictionary
  action: not-a-dictionary
"""

    def test_validate_yaml_syntax(self):
        """Test YAML syntax validation."""
        # Test valid YAML
        valid, error = self.validator.validate_yaml_syntax(self.valid_dashboard_yaml)
        self.assertTrue(valid)
        self.assertIsNone(error)
        
        # Test invalid YAML
        invalid_yaml = "key: [incomplete list"
        valid, error = self.validator.validate_yaml_syntax(invalid_yaml)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
    
    def test_validate_dashboard_config(self):
        """Test dashboard configuration validation."""
        # Test valid dashboard
        valid, error = self.validator.validate_dashboard_config(self.valid_dashboard_yaml)
        self.assertTrue(valid)
        self.assertIsNone(error)
        
        # Test invalid dashboard
        valid, error = self.validator.validate_dashboard_config(self.invalid_dashboard_yaml)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
    
    def test_validate_automation_config(self):
        """Test automation configuration validation."""
        # Test valid automation
        valid, error = self.validator.validate_automation_config(self.valid_automation_yaml)
        self.assertTrue(valid)
        self.assertIsNone(error)
        
        # Test invalid automation
        valid, error = self.validator.validate_automation_config(self.invalid_automation_yaml)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
    
    @patch('subprocess.run')
    def test_check_config_with_hass_cli(self, mock_run):
        """Test configuration check with Home Assistant CLI."""
        # Mock subprocess.run to simulate successful CLI check
        mock_process = MagicMock()
        mock_process.stdout = "Configuration valid!"
        mock_process.stderr = ""
        mock_run.return_value = mock_process
        
        valid, result = self.validator.check_config_with_hass_cli('/path/to/config')
        self.assertTrue(valid)
        
        # Mock subprocess.run to simulate failed CLI check
        mock_process.stdout = "ERROR Invalid config"
        mock_run.return_value = mock_process
        
        valid, result = self.validator.check_config_with_hass_cli('/path/to/config')
        self.assertFalse(valid)


class TestAdvancedValidator(unittest.TestCase):
    """Test cases for AdvancedValidator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'home_assistant': {
                'url': 'http://localhost:8123',
                'token': 'test_token'
            }
        }
        self.api = MagicMock()
        self.validator = AdvancedValidator(self.config, self.api)
        
        # Sample YAML contents for testing
        self.dashboard_yaml = """
title: Test Dashboard
views:
  - title: Main View
    cards:
      - type: entities
        title: Lights
        entities:
          - entity: light.living_room
          - entity: light.kitchen
      - type: thermostat
        entity: climate.living_room
"""
        
        self.automation_yaml = """
- id: test_automation
  alias: Test Automation
  trigger:
    - platform: state
      entity_id: light.living_room
      to: 'on'
  action:
    - service: light.turn_on
      entity_id: light.kitchen
"""

    @patch('src.testing.advanced_validator.AdvancedValidator.validate_entity_references')
    @patch('src.testing.advanced_validator.AdvancedValidator.validate_dashboard_card_types')
    async def test_validate_config_against_api(self, mock_validate_card_types, mock_validate_entity_refs):
        """Test validating configuration against API."""
        # Mock validation methods
        mock_validate_card_types.return_value = (True, {
            'valid': True,
            'errors': [],
            'warnings': [],
            'card_types': set(['entities', 'thermostat']),
            'invalid_card_types': set([])
        })
        
        mock_validate_entity_refs.return_value = (True, {
            'valid': True,
            'errors': [],
            'warnings': [],
            'referenced_entities': set(['light.living_room', 'light.kitchen', 'climate.living_room']),
            'invalid_entities': set([])
        })
        
        # Test dashboard validation
        valid, result = await self.validator.validate_config_against_api('dashboard', self.dashboard_yaml)
        self.assertTrue(valid)
        self.assertEqual(result['config_type'], 'dashboard')
        
        # Add a mock for service references
        with patch('src.testing.advanced_validator.AdvancedValidator.validate_service_references') as mock_validate_service_refs:
            mock_validate_service_refs.return_value = (True, {
                'valid': True,
                'errors': [],
                'warnings': [],
                'referenced_services': set(['light.turn_on']),
                'invalid_services': set([])
            })
            
            # Test automation validation
            valid, result = await self.validator.validate_config_against_api('automation', self.automation_yaml)
            self.assertTrue(valid)
            self.assertEqual(result['config_type'], 'automation')
            
            # Test with invalid entities
            mock_validate_entity_refs.return_value = (True, {
                'valid': True,
                'errors': [],
                'warnings': ["Referenced entity 'light.bedroom' doesn't exist"],
                'referenced_entities': set(['light.living_room', 'light.bedroom']),
                'invalid_entities': set(['light.bedroom'])
            })
            
            valid, result = await self.validator.validate_config_against_api('automation', self.automation_yaml)
            self.assertTrue(valid)
            self.assertTrue(any("Referenced entity 'light.bedroom' doesn't exist" in warning for warning in result['warnings']))


class TestConfigAnalyzer(unittest.TestCase):
    """Test cases for ConfigAnalyzer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = ConfigAnalyzer()
        
        # Sample validation results for testing
        self.dashboard_validation = {
            'valid': True,
            'errors': [],
            'warnings': ["View 'Main' has no cards"],
            'config_type': 'dashboard',
            'yaml_content': """
title: Test Dashboard
views:
  - title: Main
    path: main
"""
        }
        
        self.automation_validation = {
            'valid': True,
            'errors': [],
            'warnings': ["Automation 'Test' has no conditions"],
            'config_type': 'automation',
            'yaml_content': """
- id: test
  alias: Test
  trigger:
    - platform: state
      entity_id: light.living_room
      to: 'on'
  action:
    - service: light.turn_on
      entity_id: light.kitchen
"""
        }

    def test_analyze_validation_results(self):
        """Test analyzing validation results."""
        # Test dashboard analysis
        analysis = self.analyzer.analyze_validation_results(self.dashboard_validation)
        self.assertEqual(analysis['config_type'], 'dashboard')
        self.assertTrue(any('View' in rec.get('issue', '') for rec in analysis.get('recommendations', [])))
        
        # Test automation analysis
        analysis = self.analyzer.analyze_validation_results(self.automation_validation)
        self.assertEqual(analysis['config_type'], 'automation')
        self.assertTrue(any('condition' in rec.get('issue', '').lower() for rec in analysis.get('recommendations', [])))
    
    def test_analyze_yaml_content(self):
        """Test analyzing YAML content."""
        # Test dashboard YAML analysis
        dashboard_yaml = """
title: Test Dashboard
views:
  - title: Main
    path: main
    cards:
      - type: custom:invalid-card
        entity: light.living_room
"""
        analysis = self.analyzer.analyze_yaml_content(dashboard_yaml, 'dashboard')
        self.assertEqual(analysis['config_type'], 'dashboard')
        
        # Test automation YAML analysis
        automation_yaml = """
- id: test
  alias: Test
  trigger:
    - platform: state
      entity_id: light.living_room
      to: 'on'
  action:
    - service: light.turn_on
      entity_id: light.kitchen
    - service: light.turn_on
      entity_id: light.bedroom
    - service: light.turn_on
      entity_id: light.bathroom
    - service: light.turn_on
      entity_id: light.hallway
    - service: light.turn_on
      entity_id: light.dining_room
    - service: light.turn_on
      entity_id: light.office
"""
        analysis = self.analyzer.analyze_yaml_content(automation_yaml, 'automation')
        self.assertEqual(analysis['config_type'], 'automation')
        self.assertTrue(any('complex' in rec.get('issue', '').lower() or 'actions' in rec.get('issue', '').lower() 
                           for rec in analysis.get('recommendations', [])))


class TestConfigTestRunner(unittest.TestCase):
    """Test cases for ConfigTestRunner class."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'home_assistant': {
                'url': 'http://localhost:8123',
                'token': 'test_token',
                'verify_ssl': True
            }
        }
        self.test_runner = ConfigTestRunner(self.config)
        
        # Sample YAML contents for testing
        self.dashboard_yaml = """
title: Test Dashboard
views:
  - title: Main
    path: main
    cards:
      - type: entities
        title: Lights
        entities:
          - entity: light.living_room
          - entity: light.kitchen
"""
        
        self.automation_yaml = """
- id: test_automation
  alias: Test Automation
  trigger:
    - platform: state
      entity_id: light.living_room
      to: 'on'
  action:
    - service: light.turn_on
      entity_id: light.kitchen
"""

    @patch('src.testing.validator.ConfigValidator.validate_dashboard_config')
    @patch('src.testing.validator.ConfigValidator.validate_config_against_api')
    @patch('src.testing.config_analyzer.ConfigAnalyzer.analyze_validation_results')
    async def test_test_dashboard_config(self, mock_analyze, mock_validate_api, mock_validate):
        """Test testing dashboard configuration."""
        # Mock validation and analysis methods
        mock_validate.return_value = (True, None)
        mock_validate_api.return_value = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        mock_analyze.return_value = {
            'recommendations': [
                {'issue': "Dashboard doesn't specify a theme", 'recommendation': "Add a theme", 'severity': 'low'}
            ],
            'best_practices': ['Group related entities into separate views'],
            'performance_suggestions': [],
            'security_suggestions': []
        }
        
        # Test dashboard testing without applying suggestions
        results = await self.test_runner.test_dashboard_config(self.dashboard_yaml)
        self.assertTrue(results['valid'])
        self.assertTrue(any('theme' in s['issue'] for s in results['suggestions'] if 'issue' in s))
        
        # Test dashboard testing with applying suggestions
        with patch('src.testing.test_runner.ConfigTestRunner._apply_dashboard_suggestions') as mock_apply:
            mock_apply.return_value = """
title: Test Dashboard
theme: default
views:
  - title: Main
    path: main
    cards:
      - type: entities
        title: Lights
        entities:
          - entity: light.living_room
          - entity: light.kitchen
"""
            results = await self.test_runner.test_dashboard_config(self.dashboard_yaml, True)
            self.assertTrue(results['valid'])
            self.assertNotEqual(results['yaml_content'], results['yaml_content_updated'])
            self.assertTrue(any('Applied automated suggestions' in change for change in results['applied_changes']))
    
    @patch('src.testing.validator.ConfigValidator.validate_automation_config')
    @patch('src.testing.validator.ConfigValidator.validate_config_against_api')
    @patch('src.testing.config_analyzer.ConfigAnalyzer.analyze_validation_results')
    async def test_test_automation_config(self, mock_analyze, mock_validate_api, mock_validate):
        """Test testing automation configuration."""
        # Mock validation and analysis methods
        mock_validate.return_value = (True, None)
        mock_validate_api.return_value = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        mock_analyze.return_value = {
            'recommendations': [
                {'issue': "Automation 'Test Automation' doesn't specify a mode", 'recommendation': "Add mode: single", 'severity': 'medium'}
            ],
            'best_practices': ['Add conditions to prevent unnecessary triggering'],
            'performance_suggestions': [],
            'security_suggestions': []
        }
        
        # Test automation testing
        results = await self.test_runner.test_automation_config(self.automation_yaml)
        self.assertTrue(results['valid'])
        self.assertTrue(any('mode' in s['issue'] for s in results['suggestions'] if 'issue' in s))


if __name__ == '__main__':
    unittest.main()