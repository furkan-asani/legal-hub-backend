from typing import Optional
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool

from rag.rag_engine import RAGEngine

# Centralized singleton RAGEngine instance
def get_rag_engine():
    if not hasattr(get_rag_engine, "_instance"):
        get_rag_engine._instance = RAGEngine(collection_name="law-test")
    return get_rag_engine._instance

class RagTool(BaseTool):
    name: str = "RAG Legal Retrieval Tool"
    description: str = "Retrieves legal answers from the RAG system given a question and optional case_id."

    def _run(self, query: str, case_id: Optional[int] = None):
        rag_engine = get_rag_engine()
        result = rag_engine.query(query=query, case_id=case_id)
        return result  # Return the full dict, not just the answer string

class CaseContextTool(BaseTool):
    name: str = "Case Context Retrieval Tool"
    description: str = "Retrieves all context chunks (all info) for a given case ID from the RAG system. Use this when you need all information about a case."

    def _run(self, case_id: int):
        rag_engine = get_rag_engine()
        chunks = rag_engine.get_chunks_by_case_id(case_id)
        # Return only the text for each chunk, or include metadata if needed
        return [
            {"text": chunk["text"], "metadata": chunk["metadata"]}
            for chunk in chunks
        ]

# Define the legal question answering agent
legal_agent = Agent(
    role="Legal Question Answering Agent",
    goal="Answer legal questions accurately using all available legal documents and tools.",
    backstory="You are an expert legal assistant with access to a powerful retrieval system for legal documents. You also have access to the case context tool to retrieve all information about a case. Only use that if you need all of the information about a case. The rag engine in general will be a better fit for specialized questions",
    tools=[RagTool(), CaseContextTool()],
    verbose=True
)

def answer_legal_question(question: str, case_id: Optional[int] = None):
    """
    Use the CrewAI legal agent to answer a legal question, leveraging the RAG tool for retrieval.
    """
    query = question if case_id is None else f"[CASE {case_id}] {question}"
    result = legal_agent.kickoff(query)
    return result.raw  # Return the full dict, including answer and citations 