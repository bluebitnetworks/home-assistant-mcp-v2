# @home-assistant/mcp-client-sdk

Client SDK for interacting with the Home Assistant MCP service.

## Installation

```bash
npm install @home-assistant/mcp-client-sdk
```

## Usage

```ts
import { MCPClient } from '@home-assistant/mcp-client-sdk';

const client = new MCPClient({
  baseUrl: 'http://localhost:8000',
  token: 'YOUR_ACCESS_TOKEN',
});

// List all entity states
const states = await client.listStates();
console.log(states);

// Get a specific entity state
const light = await client.getState('light.kitchen_light');
console.log(light);

// Call a service
await client.callService('light', 'turn_on', { entity_id: 'light.kitchen_light' });
```

## Publishing

To publish a new version to npm (public):

```bash
cd packages/client-sdk
npm publish --access public
```
