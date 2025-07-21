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
        return result.get("answer", "")

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
    backstory="You are an expert legal assistant with access to a powerful retrieval system for legal documents. You have to judge how much information is needed to answer the question. You can use the RAG tool to retrieve information from the legal documents. If you want to summarize something then you would need to query all the chunks by caseId.",
    tools=[RagTool(), CaseContextTool()],
    verbose=True
)

def answer_legal_question(question: str, case_id: Optional[int] = None) -> str:
    """
    Use the CrewAI legal agent to answer a legal question, leveraging the RAG tool for retrieval.
    """
    query = question if case_id is None else f"[CASE {case_id}] {question}"
    result = legal_agent.kickoff(query)
    return result.raw 