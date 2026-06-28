from app.scorer import score_complexity, Complexity


def test_simple_what_is_question():
    complexity, reason = score_complexity("What is the capital of France?")
    assert complexity == Complexity.LOW
    assert "keyword" in reason.lower() or "short" in reason.lower()


def test_code_generation_is_high():
    complexity, reason = score_complexity(
        "Write a complete Python class for a binary search tree with insert, delete, and search methods."
    )
    assert complexity == Complexity.HIGH


def test_long_prompt_is_high():
    long_prompt = "Explain " + "this complex topic " * 200
    complexity, reason = score_complexity(long_prompt)
    assert complexity == Complexity.HIGH


def test_medium_prompt():
    complexity, reason = score_complexity(
        "Can you help me understand how HTTPS works and why it's important for web security?"
    )
    assert complexity in (Complexity.LOW, Complexity.MEDIUM)


def test_refactor_keyword():
    complexity, reason = score_complexity("Please refactor this function to be more readable.")
    assert complexity == Complexity.HIGH


def test_system_prompt_included_in_scoring():
    # High-complexity system prompt should raise the bar
    complexity, _ = score_complexity(
        prompt="Hello",
        system_prompt="You are an expert system. Analyze, debug, and optimize all user code.",
    )
    assert complexity == Complexity.HIGH


def test_empty_system_prompt():
    complexity, reason = score_complexity("Hi", "")
    assert complexity == Complexity.LOW


def test_summarize_is_low():
    complexity, _ = score_complexity("Summarize this article in 3 sentences.")
    assert complexity == Complexity.LOW
