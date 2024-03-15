from lf_toolkit.evaluation import Result


def test_result_equals():
    result1 = Result(
        is_correct=True,
        feedback_items=[("tag1", "feedback1")],
        latex="latex",
        simplified="simplified",
    )
    result2 = Result(
        is_correct=True,
        feedback_items=[("tag1", "feedback1")],
        latex="latex",
        simplified="simplified",
    )

    assert result1 == result2


def test_result_not_equals():
    result1 = Result(
        is_correct=True,
        feedback_items=[("tag1", "feedback1")],
        latex="latex1",
        simplified="simplified1",
    )
    result2 = Result(
        is_correct=False,
        feedback_items=[("tag2", "feedback2")],
        latex="latex2",
        simplified="simplified2",
    )

    assert result1 != result2


def test_result_repr():
    result = Result(
        is_correct=True,
        feedback_items=[("tag1", "feedback1")],
        latex="latex",
        simplified="simplified",
    )

    assert (
        repr(result)
        == "Result(is_correct=True, response_latex='latex', response_simplified='simplified', feedback='feedback1', tags=['tag1'])"
    )


def test_result_tags():
    result = Result(
        is_correct=True,
        feedback_items=[("tag1", "feedback1"), ("tag2", "feedback2")],
        latex="latex",
        simplified="simplified",
    )

    assert result.tags == ["tag1", "tag2"]


def test_result_get_feedback():
    result = Result(
        is_correct=True,
        feedback_items=[("tag1", "feedback1"), ("tag2", "feedback2")],
        latex="latex",
        simplified="simplified",
    )

    assert result.get_feedback("tag1") == ["feedback1"]
    assert result.get_feedback("tag2") == ["feedback2"]


def test_result_feedback_string():
    result = Result(
        is_correct=True,
        feedback_items=[("tag1", "feedback1"), ("tag2", "feedback2")],
        latex="latex",
        simplified="simplified",
    )

    assert result.feedback == "feedback1<br>feedback2"


def test_result_get_empty_feedback():
    result = Result(
        is_correct=True,
        feedback_items=[],
        latex="latex",
        simplified="simplified",
    )

    assert result.get_feedback("tag1") == []


def test_result_add_feedback():
    result = Result(
        is_correct=True,
        feedback_items=[],
        latex="latex",
        simplified="simplified",
    )

    result.add_feedback("tag1", "feedback1")
    result.add_feedback("tag2", "feedback2")

    assert result.get_feedback("tag1") == ["feedback1"]
    assert result.get_feedback("tag2") == ["feedback2"]


def test_result_add_fedback_multiple():
    result = Result(
        is_correct=True,
        feedback_items=[],
        latex="latex",
        simplified="simplified",
    )

    result.add_feedback("tag1", "feedback1")
    result.add_feedback("tag1", "feedback2")

    assert result.get_feedback("tag1") == ["feedback1", "feedback2"]


def test_result_converts_to_dict():
    result = Result(
        is_correct=True,
        feedback_items=[("tag1", "feedback1")],
        latex="latex",
        simplified="simplified",
    )

    expected = {
        "is_correct": True,
        "response_latex": "latex",
        "response_simplified": "simplified",
        "feedback": "feedback1",
    }

    assert result.to_dict() == expected


def test_result_converts_to_dict_with_test_data():
    result = Result(
        is_correct=True,
        feedback_items=[("tag1", "feedback1")],
        latex="latex",
        simplified="simplified",
    )

    expected = {
        "is_correct": True,
        "response_latex": "latex",
        "response_simplified": "simplified",
        "feedback": "feedback1",
        "tags": ["tag1"],
    }

    assert result.to_dict(include_test_data=True) == expected
