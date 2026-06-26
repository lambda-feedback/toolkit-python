# Examples

## Basic correct/incorrect result

```python
from lf_toolkit.evaluation import Result, Params

def eval_function(response: str, answer: str, params: Params) -> Result:
    is_correct = response.strip() == answer.strip()
    return Result(is_correct=is_correct)
```

## Adding feedback

```python
def eval_function(response: str, answer: str, params: Params) -> Result:
    is_correct = response.strip() == answer.strip()
    result = Result(is_correct=is_correct)

    if not is_correct:
        result.add_feedback("hint", "Check your spelling.")
        result.add_feedback("hint", f'The correct answer starts with "{answer[0]}".')

    return result
```

Feedback items are grouped by tag. Common tags are `"hint"` and `"error"`. All messages for a tag are joined with `<br>` when displayed to the student.

## Feedback in the constructor

```python
result = Result(
    is_correct=False,
    feedback_items=[
        ("hint", "Try simplifying your fraction first."),
        ("error", "Sign error in the second term."),
    ],
)
```

## Comparing numbers

```python
def eval_function(response: str, answer: str, params: Params) -> Result:
    try:
        is_correct = float(response.strip()) == float(answer.strip())
    except ValueError:
        result = Result(is_correct=False)
        result.add_feedback("error", "Your answer must be a number.")
        return result

    result = Result(is_correct=is_correct)
    if not is_correct:
        result.add_feedback("hint", f"The expected answer is {answer}.")
    return result
```

## Reading Params

`Params` carries configuration set by the question author. Always provide a default in case the key is not set.

```python
def eval_function(response: str, answer: str, params: Params) -> Result:
    is_latex = params.get("is_latex", False)
    should_simplify = params.get("simplify", True)
    symbols = params.get("symbols", {})

    # symbols looks like:
    # {"x": {"latex": "x", "aliases": []}, "alpha": {"latex": r"\alpha", "aliases": ["a"]}}
    ...
```

## Using symbols from Params

```python
def eval_function(response: str, answer: str, params: Params) -> Result:
    symbols = params.get("symbols", {})

    allowed_names = set(symbols.keys())
    for name, data in symbols.items():
        allowed_names.update(data.get("aliases", []))

    # check response only uses allowed symbol names
    ...
```

## Including parsed representations in Result

If you parse the student's response, include the canonical forms so the platform can display them.

```python
result = Result(
    is_correct=True,
    latex=r"\frac{1}{2}",
    simplified="1/2",
)
```

## Async eval function

```python
async def eval_function(response: str, answer: str, params: Params) -> Result:
    result = await some_async_check(response, answer)
    return Result(is_correct=result)
```

## Testing a Result

```python
from lf_toolkit.evaluation import Result

def test_correct_answer():
    result = eval_function("42", "42", {})
    assert result.is_correct

def test_wrong_answer_has_hint():
    result = eval_function("41", "42", {})
    assert not result.is_correct
    assert result.get_feedback("hint") != []
```
