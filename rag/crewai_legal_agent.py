from typing import Optional, List
from crewai import LLM, Agent, Task, Crew
from crewai.tools import BaseTool
import psycopg2
import os
import logging
from dotenv import load_dotenv

from rag.rag_engine import RAGEngine
from rag.streaming_callback import StreamingCallback

load_dotenv()
DATABASE_CONNECTION_STRING = os.getenv("DATABASE_CONNECTION_STRING")

# Set up logging
logger = logging.getLogger(__name__)

# Centralized singleton RAGEngine instance
def get_rag_engine():
    if not hasattr(get_rag_engine, "_instance"):
        get_rag_engine._instance = RAGEngine(collection_name="law-test")
    return get_rag_engine._instance

def get_document_names_by_case_id(case_id: int) -> List[dict]:
    """
    Get document names and IDs for a given case_id from the database.
    
    Args:
        case_id: The case ID to get documents for
        
    Returns:
        List of dictionaries with document_id and file_path
    """
    try:
        with psycopg2.connect(DATABASE_CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                cur.execute('SET SEARCH_PATH TO "schneider-poc";')
                cur.execute('SELECT id, file_path FROM document WHERE case_id = %s;', (case_id,))
                docs = cur.fetchall()
                return [{"document_id": row[0], "file_path": row[1]} for row in docs]
    except Exception as e:
        print(f"Error getting document names: {e}")
        return []

class RagTool(BaseTool):
    name: str = "RAG Legal Retrieval Tool"
    description: str = "Retrieves legal answers from the RAG system given a question and optional case_id."

    def _run(self, query: str, case_id: Optional[int] = None):
        rag_engine = get_rag_engine()
        result = rag_engine.query(query=query, case_id=case_id)
        # Return a structured response that includes both answer and citations
        return {
            "answer": result.get("answer", ""),
            "citations": result.get("citations", []),
            "retrieved_chunks": result.get("retrieved_chunks", 0),
            "case_id_filter": result.get("case_id_filter")
        }

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

def create_legal_agent(callbacks: List[StreamingCallback] = None) -> Agent:
    """
    Create a legal question answering agent with optional streaming callbacks.
    
    Args:
        callbacks: List of streaming callbacks for real-time event streaming
        
    Returns:
        Configured CrewAI Agent
    """
    agent_backstory = """
    Role: You are a meticulous and highly strategic Senior Legal Analyst. Your primary mission is to answer user questions with unparalleled precision and efficiency by intelligently querying a complex legal database. Your reputation is built on finding the exact piece of information needed without wading through irrelevant material. All documents are in german. This means that you should use german keywords and phrases in your queries to the rag engine and that you should translate your answer in german.

Core Directives:

STRATEGIZE FIRST, ACT SECOND: Before you use any tool, you must pause and formulate a clear plan. Your thought process must explicitly outline this plan.

LEVERAGE THE DOCUMENT MANIFEST: For every case-specific query, you will automatically receive a Document Manifest containing a list of documents with their documentIds and file_path titles. This manifest is your primary guide. Your first step is to analyze the user's question and cross-reference it with the document titles to form a hypothesis about which document(s) contain the answer.

PRECISION IS PARAMOUNT: Your default tool is the specialized RAG (Retrieval-Augmented Generation) Tool. It is your surgical scalpel. Only use the broad case_context_tool when absolutely necessary.

Tool Protocol & Workflow:

You must follow this exact sequence in your reasoning:

Step 1: Deconstruct the Question & Analyze the Document Manifest

Analyze: What specific information is the user asking for? Is it a fact, a date, a statement, an argument, a summary?

Hypothesize: Based on the document titles provided, which document is the most likely source for this information? For example, if the question is about the defendant's initial claims, a document titled "Defendant's Initial Answer" is the prime candidate.

State Your Plan: In your thought process, explicitly state your chosen document and why you chose it.

Step 2: Execute with the RAG Tool (Your Scalpel)

Action: Use the rag_tool.

Filtering: You MUST apply a documentId filter corresponding to the document you identified in Step 1. Use the exact documentId from the provided Document Manifest. This is non-negotiable for targeted questions.

Iterate if Necessary: If your first query doesn't yield the answer, analyze the results and consider if another document from the list might be a better target. Reformulate your query or choose a different documentId.

Step 3: Use the Case Context Tool (Your Last Resort)

This tool retrieves all chunks from all documents in the case. It is powerful but inefficient and should be avoided.

Permitted Use Cases:

The user asks an extremely broad question like, "Give me a full summary of the entire case."

You have already tried targeted searches with the rag_tool on the most likely documents and have failed to find a relevant answer. You must state in your thought process why you are escalating to this tool.

Example of a Good Thought Process for the Agent:
User Question: "What was the defendant's justification for their first counterclaim?"

Provided Document Manifest:

documentId: '1', title: 'Plaintiff's Initial Complaint'

documentId: '2', title: 'Defendant's Initial Answer and Counterclaims'

documentId: '3', title: 'Motion to Dismiss by Plaintiff'

Agent's Internal Monologue (Thought):

Deconstruct & Analyze: The user is asking for the "justification" of the "first counterclaim" made by the "defendant." This is a very specific piece of information.

Hypothesize using Manifest: I have three documents.

'Plaintiff's Initial Complaint' is unlikely to contain the defendant's reasoning.

'Motion to Dismiss by Plaintiff' is a response to the defendant, not the defendant's original statement.

'Defendant's Initial Answer and Counterclaims' is the perfect candidate. The title explicitly mentions both "Answer" and "Counterclaims."

State Plan & Tool Choice: My strategy is to use the rag_tool to search for the justification. I will apply a filter to search only within the document 'Defendant's Initial Answer and Counterclaims' (documentId: '2') to ensure precision and avoid contamination from other documents. The case_context_tool is completely inappropriate here.

Action Formulation: I will now call the rag_tool with the query "justification for counterclaim" and set the documentId filter to '2'.

(End of Thought process, agent proceeds to Action)
    """

    
    
    return Agent(
        role="Legal Question Answering Agent",
        goal="Answer legal questions accurately using all available legal documents and tools.",
        backstory=agent_backstory,
        tools=[RagTool(), CaseContextTool()],
        verbose=True,
        llm=LLM(
            model="gpt-5-2025-08-07",
            drop_params=True,
            additional_drop_params=["stop"]
        ),
        callbacks=callbacks or []
    )

# Create default agent for backward compatibility
legal_agent = create_legal_agent()

def answer_legal_question(question: str, case_id: Optional[int] = None):
    """
    Use the CrewAI legal agent to answer a legal question, leveraging the RAG tool for retrieval.
    """
    # Build query with document manifest if case_id is provided
    query = question
    if case_id is not None:
        documents = get_document_names_by_case_id(case_id)
        if documents:
            doc_manifest = "\n".join([f"documentId: '{doc['document_id']}', title: '{doc['file_path']}'" for doc in documents])
            query = f"[CASE {case_id}] Document Manifest:\n{doc_manifest}\n\nQuestion: {question}"
        else:
            query = f"[CASE {case_id}] {question}"
    
    # Log the query being sent to the agent
    logger.info(f"Sending query to legal agent: {query}")
    print(f"[AGENT QUERY] {query}")
    
    result = legal_agent.kickoff(query)
    
    # The agent's raw output is just the answer string, but we need to get the citations
    # from the RAG tool's execution. Let's call the RAG engine directly to get the full result
    rag_engine = get_rag_engine()
    rag_result = rag_engine.query(query=question, case_id=case_id)
    
    # Return the full result with the agent's answer and RAG citations
    return {
        "answer": result.raw,
        "citations": rag_result.get("citations", []),
        "retrieved_chunks": rag_result.get("retrieved_chunks", 0),
        "case_id_filter": rag_result.get("case_id_filter")
    }

def answer_legal_question_streaming(
    question: str, 
    case_id: Optional[int] = None, 
    callback: StreamingCallback = None
):
    """
    Use the CrewAI legal agent with streaming capabilities to answer a legal question.
    
    Args:
        question: The legal question to answer
        case_id: Optional case ID to filter documents
        callback: Streaming callback for real-time events
        
    Returns:
        Dictionary with answer and metadata
    """
    # Create agent with streaming callback
    agent = create_legal_agent(callbacks=[callback] if callback else [])
    
    # Build query with document manifest if case_id is provided
    query = question
    if case_id is not None:
        documents = get_document_names_by_case_id(case_id)
        if documents:
            doc_manifest = "\n".join([f"documentId: '{doc['document_id']}', title: '{doc['file_path']}'" for doc in documents])
            query = f"[CASE {case_id}] Document Manifest:\n{doc_manifest}\n\nQuestion: {question}"
        else:
            query = f"[CASE {case_id}] {question}"

    # Log the query being sent to the agent
    logger.info(f"Sending query to legal agent (streaming): {query}")
    print(f"[AGENT QUERY STREAMING] {query}")

    # Emit thinking_start event if callback is provided
    if callback:
        callback.on_thinking_start(
            agent_name="Legal Question Answering Agent",
            thought=f"Planning answer for query: {query}"
        )
    
    # Run agent
    result = agent.kickoff(query)

    # Emit thinking_end event if callback is provided
    if callback:
        callback.on_thinking_end(
            agent_name="Legal Question Answering Agent",
            conclusion="Completed reasoning and generated answer."
        )
    
    # Get RAG citations
    rag_engine = get_rag_engine()
    rag_result = rag_engine.query(query=question, case_id=case_id)
    
    # Return the full result with the agent's answer and RAG citations
    return {
        "answer": result.raw,
        "citations": rag_result.get("citations", []),
        "retrieved_chunks": rag_result.get("retrieved_chunks", 0),
        "case_id_filter": rag_result.get("case_id_filter")
    }

# Alias for backward compatibility
create_streaming_agent = create_legal_agent 