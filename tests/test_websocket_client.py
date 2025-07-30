#!/usr/bin/env python3
"""
Test script for WebSocket streaming functionality.
This script connects to the WebSocket endpoint and sends test queries.
"""

import asyncio
import websockets
import json
import time
from typing import Dict, Any

# Configuration
WEBSOCKET_URL = "ws://localhost:8000/ws/query"

class WebSocketTester:
    def __init__(self, url: str):
        self.url = url
        self.connection_id = None
        self.events_received = []
    
    async def connect(self):
        """Connect to the WebSocket endpoint"""
        print(f"🔌 Connecting to {self.url}...")
        self.websocket = await websockets.connect(self.url)
        print("✅ Connected successfully!")
        
        # Wait for connection confirmation
        await self.wait_for_connection_confirmation()
    
    async def wait_for_connection_confirmation(self):
        """Wait for the connection establishment message"""
        try:
            message = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
            data = json.loads(message)
            
            if data.get("type") == "connection_established":
                self.connection_id = data.get("connection_id")
                print(f"🎯 Connection ID: {self.connection_id}")
                print(f"📝 Message: {data.get('message')}")
            else:
                print(f"⚠️ Unexpected message: {data}")
                
        except asyncio.TimeoutError:
            print("❌ Timeout waiting for connection confirmation")
            raise
    
    async def send_query(self, query: str, case_id: int = None):
        """Send a query to the WebSocket endpoint"""
        message = {
            "query": query,
            "case_id": case_id,
            "stream_thinking": True
        }
        
        print(f"\n📤 Sending query: {query}")
        if case_id:
            print(f"📁 Case ID: {case_id}")
        
        await self.websocket.send(json.dumps(message))
        
        # Wait for query received confirmation
        await self.wait_for_query_confirmation()
    
    async def wait_for_query_confirmation(self):
        """Wait for query received confirmation"""
        try:
            message = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
            data = json.loads(message)
            
            if data.get("type") == "query_received":
                print("✅ Query received by server")
            else:
                print(f"⚠️ Unexpected message: {data}")
                
        except asyncio.TimeoutError:
            print("❌ Timeout waiting for query confirmation")
            raise
    
    async def listen_for_events(self, timeout: int = 60):
        """Listen for streaming events"""
        print(f"\n🎧 Listening for events (timeout: {timeout}s)...")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    self.events_received.append(data)
                    
                    # Display event
                    await self.display_event(data)
                    
                    # Check if we're done
                    if data.get("type") in ["agent_execution_complete", "agent_execution_error"]:
                        print("\n🏁 Agent execution completed!")
                        break
                        
                except asyncio.TimeoutError:
                    # Continue listening
                    continue
                    
        except Exception as e:
            print(f"❌ Error listening for events: {e}")
    
    async def display_event(self, event: Dict[str, Any]):
        """Display a streaming event in a formatted way"""
        event_type = event.get("type", "unknown")
        timestamp = event.get("timestamp", 0)
        
        # Convert timestamp to readable format
        time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
        
        # Color coding for different event types
        colors = {
            "agent_start": "🟢",
            "agent_action": "🔵",
            "tool_start": "🟡",
            "tool_end": "🟠",
            "llm_start": "🟣",
            "llm_end": "🟣",
            "agent_end": "🟢",
            "agent_execution_start": "🚀",
            "agent_execution_complete": "✅",
            "agent_execution_error": "❌",
            "rag_query_start": "🔍",
            "rag_query_end": "📄",
            "thinking_start": "🧠",
            "thinking_end": "💭"
        }
        
        icon = colors.get(event_type, "📝")
        
        print(f"{icon} [{time_str}] {event_type}")
        
        # Display specific event details
        if event_type == "agent_start":
            print(f"   Agent: {event.get('agent_name', 'Unknown')}")
            print(f"   Task: {event.get('task', 'Unknown')}")
            
        elif event_type == "agent_action":
            print(f"   Agent: {event.get('agent_name', 'Unknown')}")
            print(f"   Action: {event.get('action', 'Unknown')}")
            
        elif event_type == "tool_start":
            print(f"   Tool: {event.get('tool_name', 'Unknown')}")
            input_data = event.get('input_data', {})
            if 'input' in input_data:
                print(f"   Input: {input_data['input'][:100]}...")
                
        elif event_type == "tool_end":
            print(f"   Tool: {event.get('tool_name', 'Unknown')}")
            output_data = event.get('output_data', {})
            if 'output' in output_data:
                print(f"   Output: {str(output_data['output'])[:100]}...")
                
        elif event_type == "llm_start":
            print(f"   LLM: {event.get('agent_name', 'Unknown')}")
            print("   🤔 LLM is thinking...")
            
        elif event_type == "llm_end":
            print(f"   LLM: {event.get('agent_name', 'Unknown')}")
            output_data = event.get('output_data', {})
            if 'response' in output_data:
                print(f"   Response: {output_data['response'][:100]}...")
                
        elif event_type == "agent_execution_complete":
            output_data = event.get('output_data', {})
            print(f"   Answer: {output_data.get('answer', 'No answer')[:200]}...")
            print(f"   Citations: {len(output_data.get('citations', []))}")
            print(f"   Retrieved chunks: {output_data.get('retrieved_chunks', 0)}")
            
        elif event_type == "agent_execution_error":
            print(f"   Error: {event.get('error', 'Unknown error')}")
            
        print()  # Empty line for readability
    
    async def disconnect(self):
        """Disconnect from the WebSocket"""
        if hasattr(self, 'websocket'):
            await self.websocket.close()
            print("🔌 Disconnected from WebSocket")
    
    def print_summary(self):
        """Print a summary of the test results"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total events received: {len(self.events_received)}")
        
        # Count event types
        event_counts = {}
        for event in self.events_received:
            event_type = event.get("type", "unknown")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        print("\nEvent breakdown:")
        for event_type, count in sorted(event_counts.items()):
            print(f"  {event_type}: {count}")
        
        # Check for errors
        errors = [e for e in self.events_received if e.get("type") == "agent_execution_error"]
        if errors:
            print(f"\n❌ Errors found: {len(errors)}")
            for error in errors:
                print(f"  - {error.get('error', 'Unknown error')}")
        else:
            print("\n✅ No errors found")

async def run_test():
    """Run the WebSocket test"""
    tester = WebSocketTester(WEBSOCKET_URL)
    
    try:
        # Connect to WebSocket
        await tester.connect()
        
        # Test queries
        test_queries = [
            {
                "query": "What was the defendant's first response?",
                "case_id": 1
            },
            {
                "query": "Summarize the main arguments in the case",
                "case_id": None
            }
        ]
        
        for i, test_query in enumerate(test_queries, 1):
            print(f"\n🧪 Test {i}/{len(test_queries)}")
            print("-" * 40)
            
            # Send query
            await tester.send_query(test_query["query"], test_query["case_id"])
            
            # Listen for events
            await tester.listen_for_events(timeout=30)
            
            # Small delay between tests
            if i < len(test_queries):
                print("⏳ Waiting 2 seconds before next test...")
                await asyncio.sleep(2)
        
        # Print summary
        tester.print_summary()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        await tester.disconnect()

if __name__ == "__main__":
    print("🚀 Starting WebSocket Streaming Test")
    print("=" * 60)
    
    # Run the test
    asyncio.run(run_test()) 