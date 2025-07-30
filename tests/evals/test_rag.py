from deepeval import evaluate
from deepeval.test_case import LLMTestCase
import os
import sys
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.metrics import FaithfulnessMetric
from deepeval.metrics import ContextualPrecisionMetric
from dotenv import load_dotenv
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from rag.rag_engine import RAGEngine

load_dotenv()

faithfulness = FaithfulnessMetric(model="gpt-4o-mini")
answer_relevancy = AnswerRelevancyMetric(model="gpt-4o-mini")
contextual_precision = ContextualPrecisionMetric(model="gpt-4o-mini")

eval_questions = []
with open("tests/evals/questions.txt", "r") as file:
    for line in file:
        eval_questions.append(line.strip())

answers = []
with open("tests/evals/answers.txt", "r") as file:
    for line in file:
        answers.append(line.strip())

rag_engine = RAGEngine()
test_cases = []

for i, question in enumerate(eval_questions):
    response = rag_engine.query(question)
    retrieval_context = [sourceNode["text"] for sourceNode in response["citations"]]
    test_case = LLMTestCase(

        input=question,  # the input question
        actual_output=response["answer"],  # the model's generated answer
        expected_output=answers[i],
        retrieval_context=retrieval_context  # the supporting retrieved context
    )
    test_cases.append(test_case)

evaluate(test_cases, [answer_relevancy, faithfulness, contextual_precision])