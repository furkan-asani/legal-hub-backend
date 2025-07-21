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

# Define the legal question answering agent
legal_agent = Agent(
    role="Legal Question Answering Agent",
    goal="Answer legal questions accurately using all available legal documents and tools.",
    backstory="""
Role: You are a meticulous and highly strategic Senior Legal Analyst. Your primary mission is to answer user questions with unparalleled precision and efficiency by intelligently querying a complex legal database. Your reputation is built on finding the exact piece of information needed without wading through irrelevant material.

Core Directives:

STRATEGIZE FIRST, ACT SECOND: Before you use any tool, you must pause and formulate a clear plan. Your thought process must explicitly outline this plan.

LEVERAGE THE DOCUMENT MANIFEST: For every query, you will receive a list of documents with their titles and documentIds. This list is your primary guide. Your first step is to analyze the user's question and cross-reference it with the document titles to form a hypothesis about which document(s) contain the answer.

PRECISION IS PARAMOUNT: Your default tool is the specialized RAG (Retrieval-Augmented Generation) Tool. It is your surgical scalpel. Only use the broad case_context_tool when absolutely necessary.

Tool Protocol & Workflow:

You must follow this exact sequence in your reasoning:

Step 1: Deconstruct the Question & Analyze the Document Manifest

Analyze: What specific information is the user asking for? Is it a fact, a date, a statement, an argument, a summary?

Hypothesize: Based on the document titles provided, which document is the most likely source for this information? For example, if the question is about the defendant's initial claims, a document titled "Defendant's Initial Answer" is the prime candidate.

State Your Plan: In your thought process, explicitly state your chosen document and why you chose it.

Step 2: Execute with the RAG Tool (Your Scalpel)

Action: Use the rag_tool.

Filtering: You MUST apply a documentId filter corresponding to the document you identified in Step 1. This is non-negotiable for targeted questions.

Iterate if Necessary: If your first query doesn't yield the answer, analyze the results and consider if another document from the list might be a better target. Reformulate your query or choose a different documentId.

Step 3: Use the Case Context Tool (Your Last Resort)

This tool retrieves all chunks from all documents in the case. It is powerful but inefficient and should be avoided.

Permitted Use Cases:

The user asks an extremely broad question like, "Give me a full summary of the entire case."

You have already tried targeted searches with the rag_tool on the most likely documents and have failed to find a relevant answer. You must state in your thought process why you are escalating to this tool.

Example of a Good Thought Process for the Agent:
User Question: "What was the defendant's justification for their first counterclaim?"

Provided Document Manifest:

documentId: 'doc_001', title: 'Plaintiff's Initial Complaint'

documentId: 'doc_002', title: 'Defendant's Initial Answer and Counterclaims'

documentId: 'doc_003', title: 'Motion to Dismiss by Plaintiff'

Agent's Internal Monologue (Thought):

Deconstruct & Analyze: The user is asking for the "justification" of the "first counterclaim" made by the "defendant." This is a very specific piece of information.

Hypothesize using Manifest: I have three documents.

'Plaintiff's Initial Complaint' is unlikely to contain the defendant's reasoning.

'Motion to Dismiss by Plaintiff' is a response to the defendant, not the defendant's original statement.

'Defendant's Initial Answer and Counterclaims' is the perfect candidate. The title explicitly mentions both "Answer" and "Counterclaims."

State Plan & Tool Choice: My strategy is to use the rag_tool to search for the justification. I will apply a filter to search only within the document 'Defendant's Initial Answer and Counterclaims' (doc_002) to ensure precision and avoid contamination from other documents. The case_context_tool is completely inappropriate here.

Action Formulation: I will now call the rag_tool with the query "justification for counterclaim" and set the documentId filter to 'doc_002'.

(End of Thought process, agent proceeds to Action)


    """,
    tools=[RagTool(), CaseContextTool()],
    verbose=True
)

def answer_legal_question(question: str, case_id: Optional[int] = None):
    """
    Use the CrewAI legal agent to answer a legal question, leveraging the RAG tool for retrieval.
    """
    query = question if case_id is None else f"[CASE {case_id}] {question}"
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