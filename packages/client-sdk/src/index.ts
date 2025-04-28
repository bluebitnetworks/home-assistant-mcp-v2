import axios, { AxiosInstance } from 'axios';
import WebSocket from 'ws';

export interface MCPClientOptions {
  baseUrl?: string;
  wsUrl?: string;
  token?: string;
}

export class MCPClient {
  private http: AxiosInstance;
  private ws?: WebSocket;

  constructor(private options: MCPClientOptions = {}) {
    const baseURL = options.baseUrl || process.env.HA_MCP_API_URL || '';
    this.http = axios.create({ baseURL, headers: {
      Authorization: options.token || process.env.HA_MCP_TOKEN,
    }});
  }

  async get(path: string, params?: any) {
    return this.http.get(path, { params });
  }

  async post(path: string, data?: any) {
    return this.http.post(path, data);
  }

  connectWebSocket() {
    const url = this.options.wsUrl || process.env.HA_MCP_WS_URL || '';
    this.ws = new WebSocket(url, {
      headers: { Authorization: this.options.token || process.env.HA_MCP_TOKEN || '' },
    });
    return this.ws;
  }

  // Convenience methods for common API calls
  async listStates(): Promise<any> {
    const response = await this.get('/states');
    return response.data;
  }
  async getState(entityId: string): Promise<any> {
    const response = await this.get(`/states/${entityId}`);
    return response.data;
  }
  async callService(domain: string, service: string, serviceData?: any): Promise<any> {
    const response = await this.post(`/services/${domain}/${service}`, serviceData);
    return response.data;
  }
}
