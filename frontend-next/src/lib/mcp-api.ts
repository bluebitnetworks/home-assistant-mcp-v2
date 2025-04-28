/**
 * MCP API Client
 * 
 * This module provides functions for interacting with the Home Assistant MCP API
 * deployed on Railway.
 */

// API base URL from environment variable
const API_BASE_URL = process.env.NEXT_PUBLIC_MCP_API_URL || 'http://localhost:8080';
const API_KEY = process.env.NEXT_PUBLIC_MCP_API_KEY || '';

/**
 * Make an API request to the MCP backend
 */
async function fetchFromMcp(endpoint: string, method: string = 'GET', data?: Record<string, unknown>) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  // Add API key if available
  if (API_KEY) {
    headers['X-API-Key'] = API_KEY;
  }
  
  const options: RequestInit = {
    method,
    headers,
    cache: 'no-store',
  };
  
  // Add body for POST requests
  if (data && method !== 'GET') {
    options.body = JSON.stringify(data);
  }
  
  try {
    const response = await fetch(url, options);
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API error (${response.status}): ${errorText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('MCP API request failed:', error);
    throw error;
  }
}

/**
 * Get all entity states from Home Assistant
 */
export async function getEntities() {
  return fetchFromMcp('/api/entities', 'POST', {
    action: 'get_states'
  });
}

/**
 * Get a specific entity state
 */
export async function getEntity(entityId: string) {
  return fetchFromMcp('/api/entities', 'POST', {
    action: 'get_state',
    entity_id: entityId
  });
}

/**
 * Control an entity (turn on/off, etc.)
 */
export async function controlEntity(entityId: string, action: string, parameters?: Record<string, unknown>) {
  return fetchFromMcp('/api/entities', 'POST', {
    action: 'control',
    entity_id: entityId,
    control_action: action,
    parameters: parameters || {}
  });
}

/**
 * Get available dashboards
 */
export async function getDashboards() {
  return fetchFromMcp('/api/dashboards', 'POST', {
    action: 'list'
  });
}

/**
 * Get automation suggestions
 */
export async function getAutomationSuggestions(entityId: string, days: number = 7) {
  return fetchFromMcp('/api/automations', 'POST', {
    action: 'suggest',
    entity_id: entityId,
    days: days
  });
}

/**
 * Check if the MCP API is available
 */
export async function checkApiStatus() {
  try {
    const response = await fetchFromMcp('/');
    return {
      available: true,
      version: response.version || 'unknown',
      message: response.message || 'API running'
    };
  } catch (error) {
    return {
      available: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}
