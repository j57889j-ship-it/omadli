from app.utils.question_parser import parse_txt


def test_parse_and_limit():
    content = "\n\n".join(f"{i}. Savol {i}\nA) A\nB) B\nC) C\nD) D\nANSWER: B\nDIFFICULTY: medium" for i in range(1, 106))
    questions, errors = parse_txt(content)
    assert len(questions) == 100
    assert any('100 tadan ko‘p' in x for x in errors)


def test_invalid_question():
    questions, errors = parse_txt('1. Savol\nA) A\nB) B\nC) C\nANSWER: A')
    assert not questions
    assert errors


def test_duplicate_question():
    content = "1. Bir savol\nA) A\nB) B\nC) C\nD) D\nANSWER: A\n\n2. Bir savol\nA) A\nB) B\nC) C\nD) D\nANSWER: B"
    questions, errors = parse_txt(content)
    assert len(questions) == 1
    assert any('duplicate' in x for x in errors)
