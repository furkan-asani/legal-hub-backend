# WebSocket Streaming for CrewAI Legal Agent

This document describes the WebSocket streaming implementation that provides real-time streaming of CrewAI agent thinking and responses.

## Overview

The WebSocket streaming feature allows clients to receive real-time updates as the legal agent processes queries, including:

- Agent thinking process
- Tool usage and results
- LLM interactions
- Final answers with citations

## Architecture

### Components

1. **StreamingCallback** (`rag/streaming_callback.py`)

   - Custom CrewAI callback that captures all agent events
   - Queues events for real-time streaming
   - Provides standardized event structure

2. **WebSocket Router** (`api/websocket.py`)

   - Manages WebSocket connections
   - Handles message routing and error handling
   - Provides connection status endpoints

3. **Enhanced Agent** (`rag/crewai_legal_agent.py`)
   - Modified to support streaming callbacks
   - Maintains backward compatibility
   - Provides both streaming and non-streaming interfaces

## API Endpoints

### WebSocket Endpoints

#### `/ws/query`

**WebSocket endpoint for streaming legal agent queries**

**Connection:**

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/query");
```

**Message Format:**

```json
{
  "query": "What was the defendant's response?",
  "case_id": 1,
  "stream_thinking": true
}
```

**Response Events:**
The WebSocket will stream events in real-time as the agent processes the query.

### REST Endpoints

#### `GET /ws/status`

Get status of active WebSocket connections.

**Response:**

```json
{
  "active_connections": 2,
  "connections": [
    {
      "connection_id": "uuid-here",
      "metadata": {
        "connected_at": "2024-01-01T12:00:00",
        "last_activity": "2024-01-01T12:05:00"
      }
    }
  ]
}
```

#### `POST /ws/broadcast`

Broadcast a message to all connected WebSocket clients.

**Request:**

```json
{
  "message": "System maintenance in 5 minutes",
  "type": "notification"
}
```

## Event Types

### Connection Events

- `connection_established` - WebSocket connection established
- `query_received` - Query received and validated

### Agent Execution Events

- `agent_execution_start` - Agent execution started
- `agent_execution_complete` - Agent execution completed successfully
- `agent_execution_error` - Agent execution failed

### Agent Lifecycle Events

- `agent_start` - Agent started processing
- `agent_action` - Agent performed an action
- `agent_observation` - Agent received an observation
- `agent_end` - Agent finished processing

### Tool Events

- `tool_start` - Tool execution started
- `tool_end` - Tool execution completed

### LLM Events

- `llm_start` - LLM started thinking
- `llm_end` - LLM finished thinking
- `llm_error` - LLM encountered an error

### Custom Events

- `rag_query_start` - RAG query started
- `rag_query_end` - RAG query completed
- `thinking_start` - Agent started thinking
- `thinking_end` - Agent finished thinking

## Event Structure

All events follow this standardized structure:

```json
{
  "type": "event_type",
  "timestamp": 1704067200.123,
  "agent_name": "Legal Question Answering Agent",
  "task": "Answer legal question",
  "action": "tool_usage",
  "tool_name": "RAG Legal Retrieval Tool",
  "input_data": {
    "query": "What was the defendant's response?",
    "case_id": 1
  },
  "output_data": {
    "answer": "Based on the documents...",
    "citations": [...]
  },
  "error": "Error message if applicable",
  "metadata": {
    "additional_info": "value"
  }
}
```

## Client Implementation

### JavaScript Example

```javascript
class LegalAgentWebSocket {
  constructor(url = "ws://localhost:8000/ws/query") {
    this.url = url;
    this.ws = null;
    this.connectionId = null;
    this.eventHandlers = new Map();
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log("Connected to legal agent streaming service");
      };

      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.handleEvent(data);
      };

      this.ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        reject(error);
      };

      this.ws.onclose = () => {
        console.log("Disconnected from legal agent streaming service");
      };

      // Wait for connection confirmation
      this.on("connection_established", (data) => {
        this.connectionId = data.connection_id;
        resolve(data);
      });
    });
  }

  sendQuery(query, caseId = null) {
    const message = {
      query: query,
      case_id: caseId,
      stream_thinking: true,
    };

    this.ws.send(JSON.stringify(message));
  }

  on(eventType, handler) {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, []);
    }
    this.eventHandlers.get(eventType).push(handler);
  }

  handleEvent(event) {
    const handlers = this.eventHandlers.get(event.type) || [];
    handlers.forEach((handler) => handler(event));

    // Default event logging
    console.log(`[${event.type}]`, event);
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Usage example
async function example() {
  const client = new LegalAgentWebSocket();

  try {
    await client.connect();

    // Set up event handlers
    client.on("agent_start", (event) => {
      console.log(`Agent ${event.agent_name} started: ${event.task}`);
    });

    client.on("tool_start", (event) => {
      console.log(`Tool ${event.tool_name} started`);
    });

    client.on("llm_start", (event) => {
      console.log("LLM is thinking...");
    });

    client.on("agent_execution_complete", (event) => {
      console.log("Final answer:", event.output_data.answer);
      console.log("Citations:", event.output_data.citations);
    });

    // Send a query
    client.sendQuery("What was the defendant's response?", 1);
  } catch (error) {
    console.error("Error:", error);
  }
}
```

### Python Example

```python
import asyncio
import websockets
import json

async def legal_agent_client():
    uri = "ws://localhost:8000/ws/query"

    async with websockets.connect(uri) as websocket:
        # Wait for connection confirmation
        message = await websocket.recv()
        data = json.loads(message)
        print(f"Connected: {data}")

        # Send query
        query = {
            "query": "What was the defendant's response?",
            "case_id": 1,
            "stream_thinking": True
        }
        await websocket.send(json.dumps(query))

        # Listen for events
        while True:
            try:
                message = await websocket.recv()
                event = json.loads(message)

                print(f"[{event['type']}] {event}")

                # Check if execution is complete
                if event['type'] in ['agent_execution_complete', 'agent_execution_error']:
                    break

            except websockets.exceptions.ConnectionClosed:
                break

# Run the client
asyncio.run(legal_agent_client())
```

## Testing

### Test Script

Use the provided test script to verify WebSocket functionality:

```bash
python test_websocket_client.py
```

The test script will:

1. Connect to the WebSocket endpoint
2. Send test queries
3. Display real-time events
4. Provide a summary of events received

### Manual Testing with curl

Test the status endpoint:

```bash
curl -X GET http://localhost:8000/ws/status
```

Test broadcast functionality:

```bash
curl -X POST http://localhost:8000/ws/broadcast \
     -H "Content-Type: application/json" \
     -d '{"message": "Test broadcast", "type": "test"}'
```

## Error Handling

### Common Errors

1. **Connection Timeout**

   - Ensure the server is running
   - Check firewall settings
   - Verify WebSocket URL

2. **Invalid Message Format**

   - Ensure JSON is properly formatted
   - Include required "query" field
   - Validate data types

3. **Agent Execution Errors**
   - Check RAG engine configuration
   - Verify document availability
   - Review agent backstory and tools

### Error Event Structure

```json
{
  "type": "agent_execution_error",
  "timestamp": 1704067200.123,
  "error": "Detailed error message",
  "metadata": {
    "query": "Original query",
    "case_id": 1
  }
}
```

## Performance Considerations

### Connection Management

- WebSocket connections are managed automatically
- Inactive connections are cleaned up
- Connection metadata is tracked for monitoring

### Event Streaming

- Events are streamed in real-time as they occur
- No buffering or batching to ensure immediate feedback
- Events include timestamps for performance analysis

### Scalability

- Multiple concurrent WebSocket connections supported
- Each connection is independent
- Connection manager handles connection lifecycle

## Security Considerations

### Authentication

Currently, authentication is a placeholder. Implement proper authentication as needed:

```python
def get_current_user():
    # TODO: Implement proper authentication
    # Example: JWT token validation, session management, etc.
    return {"user_id": "authenticated_user"}
```

### Input Validation

- All incoming messages are validated
- JSON format is enforced
- Required fields are checked
- Data types are validated

### Rate Limiting

Consider implementing rate limiting for WebSocket connections:

```python
# Add to WebSocket router
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.websocket("/ws/query")
@limiter.limit("10/minute")  # Limit connections per IP
async def websocket_query(websocket: WebSocket):
    # ... implementation
```

## Monitoring and Debugging

### Logging

The WebSocket implementation includes comprehensive logging:

```python
import logging
logging.getLogger("api.websocket").setLevel(logging.DEBUG)
```

### Connection Monitoring

Monitor active connections:

```bash
curl http://localhost:8000/ws/status
```

### Event Analysis

Analyze event patterns and performance:

```python
# Collect events for analysis
events = []
client.on('*', lambda event: events.append(event))

# Analyze event timing
import pandas as pd
df = pd.DataFrame(events)
df['duration'] = df.groupby('session_id')['timestamp'].diff()
```

## Future Enhancements

### Planned Features

1. **Event Filtering**

   - Client-side event filtering
   - Selective event streaming

2. **Event Persistence**

   - Store events for analysis
   - Event replay functionality

3. **Advanced Monitoring**

   - Real-time performance metrics
   - Connection health monitoring

4. **Authentication Integration**
   - JWT token validation
   - User session management

### Customization

The streaming system is designed to be extensible:

- Add new event types in `StreamingCallback`
- Customize event structure
- Implement custom event handlers
- Add new WebSocket endpoints

## Troubleshooting

### Common Issues

1. **WebSocket Connection Fails**

   ```
   Solution: Check server is running, verify URL, check firewall
   ```

2. **No Events Received**

   ```
   Solution: Verify agent configuration, check callback setup
   ```

3. **Events Not in Real-time**

   ```
   Solution: Check network latency, verify event callback implementation
   ```

4. **Memory Leaks**
   ```
   Solution: Ensure proper connection cleanup, monitor connection count
   ```

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Profiling

Profile event processing:

```python
import time
import cProfile

def profile_events():
    profiler = cProfile.Profile()
    profiler.enable()

    # Run your WebSocket client

    profiler.disable()
    profiler.print_stats(sort='cumulative')
```

## Conclusion

The WebSocket streaming implementation provides real-time visibility into the CrewAI legal agent's thinking process, enabling better user experience and debugging capabilities. The modular design allows for easy extension and customization while maintaining backward compatibility with existing REST endpoints.
