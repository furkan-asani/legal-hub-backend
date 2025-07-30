from rag.crewai_legal_agent import answer_legal_question

def test_answer_legal_question():
    question = "Was war die erste Antwort des Angeklagten?"
    case_id = 9
    answer = answer_legal_question(question, case_id)
    print(f"Answer: {answer}")
    assert isinstance(answer, str)
    assert len(answer.strip()) > 0

if __name__ == "__main__":
    test_answer_legal_question() 