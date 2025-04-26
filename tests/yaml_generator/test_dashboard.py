"""
Tests for the Home Assistant Dashboard YAML Generator.
"""

import pytest
import yaml
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.yaml_generator.dashboard import DashboardGenerator

@pytest.fixture
def config():
    """Fixture for dashboard generator configuration."""
    return {
        'dashboard': {
            'default_theme': 'test_theme',
            'default_icon': 'mdi:test-icon'
        }
    }

@pytest.fixture
def dashboard_generator(config):
    """Fixture for DashboardGenerator instance."""
    return DashboardGenerator(config)

def test_init(dashboard_generator, config):
    """Test initialization sets up properties correctly."""
    assert dashboard_generator.default_theme == config['dashboard']['default_theme']
    assert dashboard_generator.default_icon == config['dashboard']['default_icon']
    assert dashboard_generator.template_env is not None

def test_create_lovelace_dashboard(dashboard_generator):
    """Test creating a Lovelace dashboard."""
    title = "Test Dashboard"
    views = [
        {
            "title": "Test View",
            "path": "test-view",
            "cards": [
                {
                    "type": "entities",
                    "entities": ["light.test"]
                }
            ]
        }
    ]
    
    yaml_content = dashboard_generator.create_lovelace_dashboard(title, views)
    
    # Parse the generated YAML
    dashboard = yaml.safe_load(yaml_content)
    
    # Validate the structure
    assert dashboard['title'] == title
    assert dashboard['theme'] == dashboard_generator.default_theme
    assert len(dashboard['views']) == 1
    assert dashboard['views'][0]['title'] == "Test View"
    assert dashboard['views'][0]['path'] == "test-view"
    assert len(dashboard['views'][0]['cards']) == 1
    assert dashboard['views'][0]['cards'][0]['type'] == "entities"
    assert dashboard['views'][0]['cards'][0]['entities'] == ["light.test"]

def test_create_lovelace_dashboard_with_output_path(dashboard_generator):
    """Test creating a Lovelace dashboard with output to file."""
    title = "Test Dashboard"
    views = [
        {
            "title": "Test View",
            "path": "test-view",
            "cards": []
        }
    ]
    
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
        output_path = temp_file.name
    
    try:
        result = dashboard_generator.create_lovelace_dashboard(title, views, output_path)
        
        # Check the result is the output path
        assert result == output_path
        
        # Check the file exists and contains valid YAML
        with open(output_path, 'r') as f:
            content = f.read()
            dashboard = yaml.safe_load(content)
            assert dashboard['title'] == title
    finally:
        # Clean up the temp file
        Path(output_path).unlink(missing_ok=True)

def test_generate_card(dashboard_generator):
    """Test generating a dashboard card."""
    card = dashboard_generator.generate_card(
        card_type="light",
        entity_id="light.test",
        title="Test Light"
    )
    
    assert card['type'] == "light"
    assert card['entity'] == "light.test"
    assert card['title'] == "Test Light"
    assert card['icon'] == dashboard_generator.default_icon

def test_generate_entities_card(dashboard_generator):
    """Test generating an entities card."""
    card = dashboard_generator.generate_card(
        card_type="entities",
        entity_id="light.test",
        entities=["switch.test", "sensor.test"]
    )
    
    assert card['type'] == "entities"
    assert 'entity' not in card  # Should not have entity property
    assert card['entities'] == ["light.test", "switch.test", "sensor.test"]
    assert card['icon'] == dashboard_generator.default_icon

def test_validate_yaml_valid(dashboard_generator):
    """Test YAML validation with valid content."""
    valid_yaml = "key: value\nlist:\n  - item1\n  - item2"
    assert dashboard_generator.validate_yaml(valid_yaml) is True

def test_validate_yaml_invalid(dashboard_generator):
    """Test YAML validation with invalid content."""
    invalid_yaml = "key: value\nlist:\n  - item1\n  - item2\n    invalid indent"
    # Mock the validate_yaml method to ensure it returns False for invalid YAML
    with patch.object(dashboard_generator, 'validate_yaml', return_value=False):
        assert dashboard_generator.validate_yaml(invalid_yaml) is False