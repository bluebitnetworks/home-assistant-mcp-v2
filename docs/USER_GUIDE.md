# Home Assistant MCP User Guide

This guide provides detailed instructions on how to use the Home Assistant Multi-agent Contextual Protocol (MCP) with Claude desktop.

## Introduction

Home Assistant MCP enables seamless interaction between Claude and your Home Assistant instance, allowing Claude to:

- View and control Home Assistant entities
- Create and modify dashboards
- Test and validate configurations
- Suggest and create automations based on your usage patterns

## Getting Started

Before using Home Assistant MCP, ensure you have:

1. Successfully [installed and configured](INSTALLATION.md) the Home Assistant MCP
2. A running Home Assistant instance
3. Claude desktop with MCP capability

## Core Functionality

### Entity Control

Claude can retrieve information about your entities and control them through MCP tools.

#### Viewing Entities

To view entities, ask Claude to show your Home Assistant entities. Examples:

- "Show me all my Home Assistant entities"
- "List all my lights"
- "What's the state of my living room thermostat?"

Claude will use the `home_assistant_entity_control` tool with the `get_entities` or `get_entity_state` action.

#### Controlling Entities

To control entities, ask Claude to perform actions on your devices. Examples:

- "Turn on the living room lights"
- "Set the kitchen thermostat to 72 degrees"
- "Close all blinds"

Claude will use the `home_assistant_entity_control` tool with the `control_entity` action.

### Dashboard Creation

Claude can help you create and validate Home Assistant dashboards.

#### Creating a Dashboard

To create a dashboard, describe what you want to include. Examples:

- "Create a dashboard for my living room devices"
- "Make a weather dashboard with temperature, humidity, and forecast"
- "Design a security dashboard with cameras and door sensors"

Claude will use the `home_assistant_dashboard` tool with the `create_dashboard` action.

#### Validating a Dashboard

To validate an existing dashboard configuration:

- "Check if this dashboard YAML is valid" (and provide the YAML)
- "Validate my dashboard configuration"

Claude will use the `home_assistant_dashboard` tool with the `validate_dashboard` action.

### Automation Management

Claude can suggest, create, and manage automations based on your Home Assistant usage patterns.

#### Viewing Automations

To view your existing automations:

- "Show me all my automations"
- "What automations do I have for the living room lights?"
- "Show me automations related to my thermostat"

Claude will use the `home_assistant_automation` tool with actions like `get_automations` or `get_entity_automations`.

#### Getting Automation Suggestions

To get automation suggestions based on your usage patterns:

- "Suggest automations based on my usage"
- "What automations would you recommend for my morning routine?"
- "Can you suggest any energy-saving automations?"

Claude will use the `home_assistant_automation` tool with the `suggest_automations` action.

#### Creating Automations

To create a new automation:

- "Create an automation that turns on the living room lights at sunset"
- "Make an automation to adjust the thermostat when no one is home"
- "Create a notification automation when my front door opens during the night"

Claude will use the `home_assistant_automation` tool with the `create_automation` action.

#### Testing Automations

To test an automation before implementing it:

- "Test this automation before adding it" (and provide the automation)
- "Verify this automation will work correctly"

Claude will use the `home_assistant_automation` tool with the `test_automation` action.

### Configuration Testing

Claude can validate Home Assistant configurations for correctness.

#### Validating Configurations

To validate a configuration:

- "Validate this YAML configuration" (and provide the YAML)
- "Check if this automation configuration is valid"

Claude will use the `home_assistant_config` tool with the `validate_config` action.

#### Testing Configurations

To test configurations before deploying:

- "Test this automation configuration" (and provide the configuration)
- "Check if this script will work properly"

Claude will use the `home_assistant_config` tool with the `test_config` action.

## Advanced Usage

### Batch Operations

To perform actions on multiple entities at once:

- "Turn off all lights on the first floor"
- "Set all thermostats to eco mode"

### Complex Automations

For complex automations that involve multiple triggers and conditions:

- "Create an automation that turns on the AC if the temperature is above 78 and someone is home"
- "Make a sequence automation that prepares my home for movie night"

### Integration with Other Systems

If you have additional integrations in Home Assistant:

- "Create an automation that flashes my Hue lights when my Ring doorbell detects motion"
- "Make a dashboard that shows both weather and calendar information"

## Troubleshooting

### Common Issues

#### Entity Not Found

If Claude reports that an entity can't be found:

1. Check that the entity exists in Home Assistant
2. Verify the exact entity ID (they are case-sensitive)
3. Ensure the entity is accessible via the Home Assistant API

#### Connection Issues

If Claude can't connect to Home Assistant:

1. Verify your Home Assistant is running
2. Check your `config.yaml` settings
3. Ensure your access token is valid
4. Verify network connectivity

#### Invalid Configurations

If a configuration validation fails:

1. Check the error message for specific issues
2. Verify syntax and indentation in YAML
3. Ensure entity IDs referenced are correct

## MCP Tool Reference

For developers and advanced users, here's a reference of the available MCP tools:

### home_assistant_entity_control

Actions:
- `get_entities`: List all entities
- `get_entity_state`: Get state of a specific entity
- `control_entity`: Control a specific entity

### home_assistant_dashboard

Actions:
- `create_dashboard`: Create a new dashboard
- `validate_dashboard`: Validate dashboard YAML

### home_assistant_automation

Actions:
- `get_automations`: List all automations
- `get_automation_details`: Get details of a specific automation
- `create_automation`: Create a new automation
- `update_automation`: Update an existing automation
- `delete_automation`: Delete an automation
- `test_automation`: Test an automation
- `suggest_automations`: Get automation suggestions
- `get_entity_automations`: Get automations for a specific entity

### home_assistant_config

Actions:
- `validate_config`: Validate configuration YAML
- `test_config`: Test a configuration
- `check_config_dependencies`: Check configuration dependencies

## Next Steps

For specific usage examples, see the [Examples](EXAMPLES.md) documentation.

For installation and configuration details, refer to the [Installation Guide](INSTALLATION.md).
