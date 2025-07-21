"""
WebSocket endpoints for real-time streaming of CrewAI agent thinking and responses.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
import json
import asyncio
import logging
from datetime import datetime
import uuid
from dataclasses import asdict

from rag.crewai_legal_agent import create_streaming_agent
from rag.streaming_callback import StreamingCallback, StreamingEvent
from rag.rag_engine import RAGEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Connection management
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "connected_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }
        logger.info(f"WebSocket connected: {connection_id}")
    
    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_event(self, connection_id: str, event: StreamingEvent):
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                event_dict = asdict(event)
                await websocket.send_text(json.dumps(event_dict))
                self.connection_metadata[connection_id]["last_activity"] = datetime.now().isoformat()
            except Exception as e:
                logger.error(f"Error sending event to {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def send_json(self, connection_id: str, data: Dict[str, Any]):
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(data))
                self.connection_metadata[connection_id]["last_activity"] = datetime.now().isoformat()
            except Exception as e:
                logger.error(f"Error sending JSON to {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def send_error(self, connection_id: str, error_message: str, error_type: str = "error"):
        error_event = StreamingEvent(
            type=error_type,
            timestamp=datetime.now().timestamp(),
            error=error_message
        )
        await self.send_event(connection_id, error_event)

# Global connection manager
manager = ConnectionManager()

def get_current_user():
    """Placeholder for authentication - implement as needed"""
    # TODO: Implement proper authentication
    return {"user_id": "anonymous"}

@router.websocket("/ws/query")
async def websocket_query(websocket: WebSocket):
    """
    WebSocket endpoint for streaming legal agent queries.
    
    Expected message format:
    {
        "query": "What was the defendant's response?",
        "case_id": 1,
        "stream_thinking": true
    }
    """
    connection_id = str(uuid.uuid4())
    
    try:
        await manager.connect(websocket, connection_id)
        
        # Send connection confirmation
        await manager.send_json(connection_id, {
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": datetime.now().isoformat(),
            "message": "Connected to legal agent streaming service"
        })
        
        while True:
            # Receive message from client
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Validate message format
                if "query" not in message:
                    await manager.send_error(connection_id, "Missing 'query' field in message")
                    continue
                
                query = message["query"]
                case_id = message.get("case_id")
                stream_thinking = message.get("stream_thinking", True)
                
                # Send query received confirmation
                await manager.send_json(connection_id, {
                    "type": "query_received",
                    "query": query,
                    "case_id": case_id,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Create streaming callback
                async def event_callback(event: StreamingEvent):
                    await manager.send_event(connection_id, event)
                
                callback = StreamingCallback(event_callback=event_callback)
                
                # Run agent in background task
                await run_agent_with_streaming(connection_id, query, case_id, callback)
                
                # Send ready for next query message
                await manager.send_json(connection_id, {
                    "type": "ready_for_next_query",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Ready for next query"
                })
                
            except json.JSONDecodeError:
                await manager.send_error(connection_id, "Invalid JSON format")
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {connection_id}")
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await manager.send_error(connection_id, f"Processing error: {str(e)}")
                # Don't break here, allow for next query
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(connection_id)

async def run_agent_with_streaming(
    connection_id: str, 
    query: str, 
    case_id: Optional[int], 
    callback: StreamingCallback
):
    """
    Run the CrewAI agent with streaming callbacks.
    """
    try:
        # Send agent start event
        start_event = StreamingEvent(
            type="agent_execution_start",
            timestamp=datetime.now().timestamp(),
            input_data={"query": query, "case_id": case_id}
        )
        await manager.send_event(connection_id, start_event)
        
        # Create streaming agent
        agent = create_streaming_agent(callbacks=[callback])
        
        # Prepare query
        full_query = query if case_id is None else f"[CASE {case_id}] {query}"
        
        # Run agent
        result = agent.kickoff(full_query)
        
        # Get RAG citations
        rag_engine = RAGEngine(collection_name="law-test")
        rag_result = rag_engine.query(query=query, case_id=case_id)
        
        # Send final result
        final_event = StreamingEvent(
            type="agent_execution_complete",
            timestamp=datetime.now().timestamp(),
            output_data={
                "answer": result.raw,
                "citations": rag_result.get("citations", []),
                "retrieved_chunks": rag_result.get("retrieved_chunks", 0),
                "case_id_filter": rag_result.get("case_id_filter")
            }
        )
        await manager.send_event(connection_id, final_event)
        
    except Exception as e:
        logger.error(f"Agent execution error: {e}")
        error_event = StreamingEvent(
            type="agent_execution_error",
            timestamp=datetime.now().timestamp(),
            error=str(e)
        )
        await manager.send_event(connection_id, error_event)

@router.get("/ws/status")
async def websocket_status():
    """
    Get status of active WebSocket connections.
    """
    return {
        "active_connections": len(manager.active_connections),
        "connections": [
            {
                "connection_id": conn_id,
                "metadata": metadata
            }
            for conn_id, metadata in manager.connection_metadata.items()
        ]
    }

@router.post("/ws/broadcast")
async def broadcast_message(message: Dict[str, Any]):
    """
    Broadcast a message to all connected WebSocket clients.
    """
    broadcast_event = StreamingEvent(
        type="broadcast",
        timestamp=datetime.now().timestamp(),
        input_data=message
    )
    
    for connection_id in list(manager.active_connections.keys()):
        await manager.send_event(connection_id, broadcast_event)
    
    return {"message": f"Broadcast sent to {len(manager.active_connections)} connections"} 