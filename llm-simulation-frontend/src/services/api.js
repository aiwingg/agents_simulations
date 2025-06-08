// API service for LLM Simulation backend
const API_BASE_URL = import.meta.env.VITE_API_URL || window.location.origin;

class ApiError extends Error {
  constructor(message, status, response) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.response = response;
  }
}

const handleResponse = async (response) => {
  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.error || errorMessage;
    } catch {
      // If we can't parse the error response, use the status text
      errorMessage = response.statusText || errorMessage;
    }
    throw new ApiError(errorMessage, response.status, response);
  }
  return response.json();
};

// Health check
export const checkHealth = async () => {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  return handleResponse(response);
};

// Launch a new batch
export const launchBatch = async (data) => {
  const response = await fetch(`${API_BASE_URL}/api/batches`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  return handleResponse(response);
};

// Get batch status
export const getBatchStatus = async (batchId) => {
  const response = await fetch(`${API_BASE_URL}/api/batches/${batchId}`);
  return handleResponse(response);
};

// Get batch results
export const getBatchResults = async (batchId, format = 'json') => {
  const url = new URL(`${API_BASE_URL}/api/batches/${batchId}/results`);
  if (format !== 'json') {
    url.searchParams.set('format', format);
  }
  
  const response = await fetch(url);
  
  if (format === 'json') {
    return handleResponse(response);
  } else {
    // For CSV/NDJSON, return the blob
    if (!response.ok) {
      throw new ApiError(`HTTP ${response.status}`, response.status, response);
    }
    return response.blob();
  }
};

// Get batch summary
export const getBatchSummary = async (batchId) => {
  const response = await fetch(`${API_BASE_URL}/api/batches/${batchId}/summary`);
  return handleResponse(response);
};

// Get batch cost
export const getBatchCost = async (batchId) => {
  const response = await fetch(`${API_BASE_URL}/api/batches/${batchId}/cost`);
  return handleResponse(response);
};

// List all batches
export const listBatches = async () => {
  const response = await fetch(`${API_BASE_URL}/api/batches`);
  return handleResponse(response);
};

// WebSocket connection for real-time updates
export class BatchWebSocket {
  constructor(batchId, onUpdate, onError) {
    this.batchId = batchId;
    this.onUpdate = onUpdate;
    this.onError = onError;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
  }

  connect() {
    try {
      const wsUrl = `${API_BASE_URL.replace('http', 'ws')}/ws/batch/${this.batchId}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.onUpdate(data);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.onError(error);
      };
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      this.onError(err);
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        this.connect();
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// Polling fallback for batch status
export class BatchPoller {
  constructor(batchId, onUpdate, interval = 2000) {
    this.batchId = batchId;
    this.onUpdate = onUpdate;
    this.interval = interval;
    this.intervalId = null;
  }

  start() {
    this.intervalId = setInterval(async () => {
      try {
        const status = await getBatchStatus(this.batchId);
        this.onUpdate(status);
        
        // Stop polling if batch is completed or failed
        if (status.status === 'completed' || status.status === 'failed') {
          this.stop();
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, this.interval);
  }

  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }
}

export default {
  checkHealth,
  launchBatch,
  getBatchStatus,
  getBatchResults,
  getBatchSummary,
  getBatchCost,
  listBatches,
  BatchWebSocket,
  BatchPoller,
};

