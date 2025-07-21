from rag.crewai_legal_agent import answer_legal_question

def test_answer_legal_question():
    question = "Kannst du diesen Fall für mich zusammenfassen?"
    case_id = 9
    answer = answer_legal_question(question, case_id)
    print(f"Answer: {answer}")
    assert isinstance(answer, str)
    assert len(answer.strip()) > 0

if __name__ == "__main__":
    test_answer_legal_question() 