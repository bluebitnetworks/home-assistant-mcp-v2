# Home Assistant MCP Usage Examples

This document provides practical examples of using the Home Assistant Multi-agent Contextual Protocol (MCP) with Claude desktop.

## Table of Contents

1. [Entity Control Examples](#entity-control-examples)
2. [Dashboard Creation Examples](#dashboard-creation-examples)
3. [Automation Examples](#automation-examples)
4. [Configuration Testing Examples](#configuration-testing-examples)
5. [Complex Multi-Step Scenarios](#complex-multi-step-scenarios)

## Entity Control Examples

### Example 1: Retrieving Entity States

**User Query:**
"Show me the status of all my lights."

**Claude's Process:**
1. Claude uses the `home_assistant_entity_control` tool with `get_entities` action
2. Filters the results for entities with domain "light"
3. Presents a formatted list of lights and their states

**Sample Response:**
```
Here are your lights and their current states:

- light.living_room: ON (Brightness: 80%)
- light.kitchen: OFF
- light.bedroom: ON (Brightness: 50%, Color: Warm White)
- light.hallway: OFF
- light.bathroom: OFF
```

### Example 2: Controlling Multiple Entities

**User Query:**
"Turn off all the lights downstairs."

**Claude's Process:**
1. Claude uses `home_assistant_entity_control` with `get_entities` to find lights
2. Identifies lights that are likely downstairs based on naming
3. Uses `control_entity` for each light with action "turn_off"
4. Reports the results

**Sample Response:**
```
I've turned off the following lights:
- light.living_room
- light.kitchen
- light.dining_room
- light.hallway_downstairs

All downstairs lights are now off.
```

### Example 3: Adjusting Climate Settings

**User Query:**
"Set the bedroom thermostat to 72 degrees and turn on fan mode."

**Claude's Process:**
1. Claude uses `home_assistant_entity_control` with `get_entity_state` to find the bedroom thermostat
2. Uses `control_entity` with parameters for temperature and fan mode
3. Confirms the new settings

**Sample Response:**
```
I've updated your bedroom thermostat:
- Set temperature to 72°F
- Turned on fan mode

The changes have been applied successfully.
```

## Dashboard Creation Examples

### Example 1: Creating a Room Dashboard

**User Query:**
"Create a dashboard for my living room with lights, television, and temperature."

**Claude's Process:**
1. Claude uses `home_assistant_entity_control` to identify relevant entities
2. Creates a dashboard structure with appropriate cards
3. Uses `home_assistant_dashboard` with `create_dashboard` action
4. Provides the generated YAML and confirmation

**Sample Response:**
```
I've created a living room dashboard with the following components:

1. Light controls
2. Television/media controls
3. Temperature display

The dashboard has been generated and saved. Here's a preview of the configuration:

```yaml
title: Living Room
views:
  - title: Main View
    cards:
      - type: light
        name: Living Room Lights
        entity: light.living_room
      - type: media-control
        entity: media_player.living_room_tv
      - type: sensor
        entity: sensor.living_room_temperature
        name: Temperature
```

You can find the complete dashboard configuration in `/config/dashboards/living_room.yaml`
```

### Example 2: Creating a Multi-View Dashboard

**User Query:**
"Create a home overview dashboard with separate tabs for each room and a summary view."

**Claude's Process:**
1. Claude identifies rooms and important entities
2. Creates a multi-view dashboard structure
3. Uses `home_assistant_dashboard` with `create_dashboard` action
4. Provides the generated YAML and confirmation

**Sample Dashboard Structure:**
```yaml
title: Home Overview
views:
  - title: Summary
    path: summary
    cards:
      - type: entities
        title: Quick Status
        entities:
          - sensor.home_temperature
          - sensor.outside_temperature
          - binary_sensor.front_door
          - alarm_control_panel.home_alarm
  - title: Living Room
    path: living-room
    cards:
      # Living room cards
  - title: Kitchen
    path: kitchen
    cards:
      # Kitchen cards
  - title: Bedroom
    path: bedroom
    cards:
      # Bedroom cards
```

## Automation Examples

### Example 1: Creating a Time-Based Automation

**User Query:**
"Create an automation to turn on my porch lights at sunset and turn them off at sunrise."

**Claude's Process:**
1. Claude uses `home_assistant_automation` with `create_automation` action
2. Creates a properly structured automation with sun triggers
3. Tests the automation before applying
4. Provides the YAML and confirms creation

**Sample Automation:**
```yaml
id: porch_lights_sun_based
alias: "Porch Lights - Sun Based"
description: "Turn porch lights on at sunset and off at sunrise"
trigger:
  - platform: sun
    event: sunset
    offset: "-00:15:00"
  - platform: sun
    event: sunrise
    offset: "00:15:00"
condition: []
action:
  - service: >
      {% if trigger.platform == 'sun' and trigger.event == 'sunset' %}
        light.turn_on
      {% else %}
        light.turn_off
      {% endif %}
    target:
      entity_id: light.porch
mode: single
```

### Example 2: Creating a Presence-Based Automation

**User Query:**
"Create an automation that turns on the hallway light when motion is detected, but only when it's dark."

**Claude's Process:**
1. Claude uses `home_assistant_automation` with `create_automation` action
2. Creates an automation with motion trigger and illuminance condition
3. Uses appropriate testing and validation
4. Provides the YAML and confirms creation

**Sample Automation:**
```yaml
id: hallway_motion_light
alias: "Hallway Motion Light"
description: "Turn on hallway light with motion when dark"
trigger:
  - platform: state
    entity_id: binary_sensor.hallway_motion
    to: "on"
condition:
  - condition: numeric_state
    entity_id: sensor.illuminance
    below: 10
action:
  - service: light.turn_on
    target:
      entity_id: light.hallway
  - wait_for_trigger:
      - platform: state
        entity_id: binary_sensor.hallway_motion
        to: "off"
        for: "00:02:00"
  - service: light.turn_off
    target:
      entity_id: light.hallway
mode: restart
```

### Example 3: Creating an Automation Based on Suggestions

**User Query:**
"Suggest automations based on my daily patterns."

**Claude's Process:**
1. Claude uses `home_assistant_automation` with `suggest_automations` action
2. Analyzes usage patterns from the past week
3. Presents suggestions with explanations
4. Offers to implement selected suggestions

**Sample Suggestions:**
```
Based on your usage patterns, here are some automation suggestions:

1. Morning Routine (7:00-8:00 AM weekdays):
   - Turn on kitchen lights
   - Set thermostat to 72°F
   - Turn on coffee maker

2. Evening Wind Down (10:00-11:00 PM daily):
   - Dim living room lights to 30%
   - Set thermostat to 68°F
   - Turn off TV if on for more than 30 minutes of inactivity

3. Away Mode Pattern:
   - When all phones disconnect from WiFi
   - Turn off all lights
   - Set thermostat to eco mode
   - Arm security system

Would you like me to implement any of these suggestions?
```

## Configuration Testing Examples

### Example 1: Validating a Custom Automation

**User Query:**
"Check if this automation will work correctly" (with provided YAML)

**Claude's Process:**
1. Claude uses `home_assistant_config` with `validate_config` action
2. Checks syntax and structure
3. Verifies entity IDs exist
4. Tests for logical issues
5. Reports findings

**Sample Response:**
```
I've analyzed your automation configuration:

✅ Valid YAML syntax
✅ Correct automation structure
✅ All referenced entities exist
⚠️ Potential logic issue: Your condition will always evaluate to true
⚠️ Missing delay after service call

Here are my recommendations:
1. Refine your condition to check for a specific state
2. Add a delay between service calls to prevent rapid toggling

Would you like me to fix these issues for you?
```

### Example 2: Testing Complex Dependencies

**User Query:**
"Make sure this script doesn't have any dependency issues" (with provided YAML)

**Claude's Process:**
1. Claude uses `home_assistant_config` with `check_config_dependencies` action
2. Identifies all dependencies and their requirements
3. Verifies all referenced entities and services exist
4. Reports any missing dependencies

**Sample Response:**
```
I've checked dependencies for your script:

✅ All core entities exist
✅ All service calls are valid
⚠️ Missing dependency: This script requires the Spotify integration
❌ Referenced entity not found: media_player.spotify_kitchen

To resolve these issues:
1. Install the Spotify integration in Home Assistant
2. Configure the Spotify media player or correct the entity ID
```

## Complex Multi-Step Scenarios

### Scenario 1: Creating a "Vacation Mode" Setup

**User Interaction:**

*User:* "Help me set up a vacation mode for when I'm away next week."

*Claude:* Asks for details about the duration and preferences.

*User:* "I'll be gone July 10-17. I want lights to turn on/off randomly in the evening, maintain temperature between 65-75°F, and get notifications of any motion events."

**Claude's Process:**
1. Create a comprehensive plan using multiple automations
2. Generate presence simulation for lights
3. Create climate control automation
4. Set up notification system
5. Create a single "vacation mode" switch to activate/deactivate all automations

**Implementation Highlights:**
- Creates a template `input_boolean.vacation_mode` helper
- Implements randomized light patterns using templates
- Sets up conditional temperature controls
- Creates notification automations for security events
- Generates dashboard with one-click activation

### Scenario 2: Building an Energy Monitoring Dashboard

**User Interaction:**

*User:* "Create a comprehensive energy monitoring dashboard for my home."

*Claude:* Asks about available energy sensors and monitoring goals.

*User:* "I have smart plugs on major appliances, a whole-home energy monitor, and solar production data. I want to track usage, costs, and identify energy hogs."

**Claude's Process:**
1. Inventory all energy-related sensors
2. Design multi-view dashboard with different perspectives
3. Create energy usage cards with historical data
4. Add cost calculations and projections
5. Create comparative views to identify inefficiencies

**Implementation Example:**
Creates a structured dashboard with:
- Summary view with current usage and cost
- Historical view with graphs and trends
- Appliance comparison view
- Solar production vs. consumption
- Energy-saving recommendations

### Scenario 3: Complete Home Arrival/Departure Sequence

**User Interaction:**

*User:* "Design a complete sequence of events for when I arrive home or leave."

**Claude's Process:**
1. Creates a presence detection system using multiple triggers
2. Designs differentiated sequences for arrival vs. departure
3. Implements contextual awareness (time of day, weather, etc.)
4. Creates appropriate test scenarios
5. Implements and validates the full system

**Sample Implementation:**
- Presence detection using phone GPS, WiFi connection, and door sensors
- Arrival sequence with lighting, climate, music, and security adjustments
- Departure sequence with energy savings and security measures
- Contextual variations for different times of day
- Simple activation through presence changes or voice commands
