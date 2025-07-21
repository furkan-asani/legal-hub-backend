from typing import Optional
from crewai import Agent, Task, Crew
# Placeholder: import your RAG system as a tool
# from .rag_tool import RagTool

class RagTool:
    """A CrewAI-compatible tool that wraps our RAG retrieval system."""
    def __init__(self):
        from .rag_engine import RAGEngine
        self.rag_engine = RAGEngine(collection_name="law-test")

    def run(self, query: str, case_id: Optional[int] = None) -> str:
        result = self.rag_engine.query_without_reranker(query=query)
        return result.get("answer", "")

# Define the legal question answering agent
legal_agent = Agent(
    role="Legal Question Answering Agent",
    goal="Answer legal questions accurately using all available legal documents and tools.",
    backstory="You are an expert legal assistant with access to a powerful retrieval system for legal documents.",
    tools=[RagTool()],
    verbose=True
)

def answer_legal_question(question: str, case_id: Optional[int] = None) -> str:
    """
    Use the CrewAI legal agent to answer a legal question, leveraging the RAG tool for retrieval.
    """
    # Optionally, you could pass case_id as context or part of the question
    query = question if case_id is None else f"[CASE {case_id}] {question}"
    result = legal_agent.kickoff(query)
    return result.raw 