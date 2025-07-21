"""
Streaming callback system for CrewAI agents to enable real-time streaming of agent thinking and actions.
"""

from typing import List, Dict, Any, Optional, Callable
import json
import time
import asyncio
from queue import Queue
import threading
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class StreamingEvent:
    """Standardized event structure for streaming"""
    type: str
    timestamp: float
    agent_name: Optional[str] = None
    task: Optional[str] = None
    action: Optional[str] = None
    tool_name: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class StreamingCallback:
    """
    Custom CrewAI callback that captures all agent events and queues them for streaming.
    Compatible with current CrewAI version that uses callbacks as functions.
    """
    
    def __init__(self, event_callback: Optional[Callable[[StreamingEvent], None]] = None):
        self.events = Queue()
        self.event_callback = event_callback
        self.thinking_buffer = []
        self._lock = threading.Lock()
    
    def _emit_event(self, event: StreamingEvent):
        """Emit an event to the queue and callback if provided"""
        with self._lock:
            self.events.put(event)
            if self.event_callback:
                try:
                    self.event_callback(event)
                except Exception as e:
                    print(f"Error in event callback: {e}")
    
    def _create_event(self, event_type: str, **kwargs) -> StreamingEvent:
        """Create a standardized event"""
        return StreamingEvent(
            type=event_type,
            timestamp=time.time(),
            **kwargs
        )
    
    # Main callback function for CrewAI
    def __call__(self, event_type: str, **kwargs):
        """Main callback function that CrewAI will call"""
        event = self._create_event(event_type, **kwargs)
        self._emit_event(event)
    
    # Agent lifecycle events
    def on_agent_start(self, agent_name: str, task: str):
        event = self._create_event(
            "agent_start",
            agent_name=agent_name,
            task=task
        )
        self._emit_event(event)
    
    def on_agent_action(self, agent_name: str, action: str, **kwargs):
        event = self._create_event(
            "agent_action",
            agent_name=agent_name,
            action=action,
            input_data=kwargs
        )
        self._emit_event(event)
    
    def on_agent_observation(self, agent_name: str, observation: str):
        event = self._create_event(
            "agent_observation",
            agent_name=agent_name,
            output_data={"observation": observation}
        )
        self._emit_event(event)
    
    def on_agent_end(self, agent_name: str, result: str):
        event = self._create_event(
            "agent_end",
            agent_name=agent_name,
            output_data={"result": result}
        )
        self._emit_event(event)
    
    # Chain events
    def on_chain_start(self, chain_name: str, inputs: Dict[str, Any]):
        event = self._create_event(
            "chain_start",
            agent_name=chain_name,
            input_data=inputs
        )
        self._emit_event(event)
    
    def on_chain_end(self, chain_name: str, outputs: Dict[str, Any]):
        event = self._create_event(
            "chain_end",
            agent_name=chain_name,
            output_data=outputs
        )
        self._emit_event(event)
    
    # Tool events
    def on_tool_start(self, tool_name: str, input_str: str):
        event = self._create_event(
            "tool_start",
            tool_name=tool_name,
            input_data={"input": input_str}
        )
        self._emit_event(event)
    
    def on_tool_end(self, tool_name: str, output: str):
        event = self._create_event(
            "tool_end",
            tool_name=tool_name,
            output_data={"output": output}
        )
        self._emit_event(event)
    
    # LLM events
    def on_llm_start(self, llm_name: str, messages: List[Dict[str, Any]]):
        event = self._create_event(
            "llm_start",
            agent_name=llm_name,
            input_data={"messages": messages}
        )
        self._emit_event(event)
    
    def on_llm_end(self, llm_name: str, response: str):
        event = self._create_event(
            "llm_end",
            agent_name=llm_name,
            output_data={"response": response}
        )
        self._emit_event(event)
    
    def on_llm_error(self, llm_name: str, error: str):
        event = self._create_event(
            "llm_error",
            agent_name=llm_name,
            error=error
        )
        self._emit_event(event)
    
    # Custom events for legal agent specific actions
    def on_rag_query_start(self, query: str, case_id: Optional[int] = None):
        event = self._create_event(
            "rag_query_start",
            input_data={"query": query, "case_id": case_id}
        )
        self._emit_event(event)
    
    def on_rag_query_end(self, result: Dict[str, Any]):
        event = self._create_event(
            "rag_query_end",
            output_data=result
        )
        self._emit_event(event)
    
    def on_thinking_start(self, agent_name: str, thought: str):
        event = self._create_event(
            "thinking_start",
            agent_name=agent_name,
            input_data={"thought": thought}
        )
        self._emit_event(event)
    
    def on_thinking_end(self, agent_name: str, conclusion: str):
        event = self._create_event(
            "thinking_end",
            agent_name=agent_name,
            output_data={"conclusion": conclusion}
        )
        self._emit_event(event)
    
    # Utility methods
    def get_events(self):
        """Generator to yield events as they come"""
        while True:
            try:
                event = self.events.get(timeout=0.1)
                yield event
            except:
                break
    
    def get_all_events(self) -> List[StreamingEvent]:
        """Get all events currently in the queue"""
        events = []
        while not self.events.empty():
            try:
                events.append(self.events.get_nowait())
            except:
                break
        return events
    
    def clear_events(self):
        """Clear all events from the queue"""
        while not self.events.empty():
            try:
                self.events.get_nowait()
            except:
                break
    
    def event_to_dict(self, event: StreamingEvent) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization"""
        return asdict(event)
    
    def event_to_json(self, event: StreamingEvent) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.event_to_dict(event), default=str) 