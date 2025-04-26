# Home Assistant MCP

A Home Assistant Multi-agent Contextual Protocol (MCP) for integration with Claude desktop.

## Overview

Home Assistant MCP enables seamless interaction between Claude and your Home Assistant instance. This powerful integration allows Claude to understand, control, and enhance your smart home setup through natural language.

### Key Features

- **Entity Control**: View states and control all Home Assistant entities
- **Dashboard Creation**: Generate customized dashboards through YAML generation
- **Configuration Testing**: Validate configurations before deployment
- **Automation Management**: Get intelligent suggestions and create automations based on usage patterns
- **Natural Language Interface**: Interact with your smart home using conversational language

## Documentation

Detailed documentation is available in the `docs` directory:

- [Installation Guide](docs/INSTALLATION.md): Complete setup instructions
- [User Guide](docs/USER_GUIDE.md): Comprehensive usage instructions
- [Examples](docs/EXAMPLES.md): Practical usage scenarios and examples

## Quick Start

### Requirements

- Python 3.8+
- Home Assistant instance with API access
- Claude desktop with MCP capability
- Long-Lived Access Token for Home Assistant

### Basic Installation

1. Clone this repository
2. Create and activate a virtual environment (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy and configure your connection settings:
   ```bash
   cp config.yaml.template config.yaml
   # Edit config.yaml with your Home Assistant URL and token
   ```
5. Run the application to generate MCP schemas:
   ```bash
   python src/main.py
   ```

### Basic Usage

1. Ensure your Home Assistant instance is running
2. Make sure the application is configured correctly
3. Access the MCP tools through Claude desktop
4. Start interacting with your Home Assistant by asking Claude questions or giving commands

## MCP Tools

Home Assistant MCP provides the following tools for Claude:

- **home_assistant_entity_control**: View and control Home Assistant entities
- **home_assistant_dashboard**: Create and validate dashboards
- **home_assistant_automation**: Manage automations with suggestions and testing
- **home_assistant_config**: Test and validate configurations

## Project Structure

- `src/connection/`: Home Assistant API connection module
- `src/yaml_generator/`: YAML configuration generator for dashboards
- `src/testing/`: Configuration testing and validation tools
- `src/automation/`: Automation suggestion and creation module
- `src/claude_integration/`: Claude MCP tool integration
- `tests/`: Test files for each module
- `docs/`: Detailed documentation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Home Assistant community for their excellent documentation
- Claude for enabling natural language interaction with smart home systems