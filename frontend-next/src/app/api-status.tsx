'use client';

import { useState, useEffect } from 'react';
import { checkApiStatus } from '@/lib/mcp-api';

export default function ApiStatus() {
  const [status, setStatus] = useState<{
    available: boolean;
    version?: string;
    message?: string;
    error?: string;
  } | null>(null);
  
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStatus() {
      try {
        const result = await checkApiStatus();
        setStatus(result);
      } catch (error) {
        setStatus({
          available: false,
          error: error instanceof Error ? error.message : 'Failed to connect to API'
        });
      } finally {
        setLoading(false);
      }
    }

    fetchStatus();
  }, []);

  return (
    <div className="p-4 rounded-md border border-gray-200 dark:border-gray-800 mb-6">
      <h2 className="text-lg font-medium mb-2">MCP API Status</h2>
      
      {loading ? (
        <p className="text-gray-500">Checking API connection...</p>
      ) : status?.available ? (
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          <p className="text-green-600 dark:text-green-400">
            Connected to MCP API {status.version && `(v${status.version})`}
          </p>
        </div>
      ) : (
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-red-500 rounded-full"></div>
          <p className="text-red-600 dark:text-red-400">
            {status?.error || 'Failed to connect to MCP API'}
          </p>
        </div>
      )}
    </div>
  );
}
