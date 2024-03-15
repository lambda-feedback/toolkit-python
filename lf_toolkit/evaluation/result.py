from typing import Any
from typing import Dict
from typing import List
from typing import Tuple
from typing import Union


FeedbackItem = Tuple[str, str]


def update_feedback(
    feedback: Dict[str, List[str]], feedback_items: List[FeedbackItem]
) -> Dict[str, List[str]]:
    for item in feedback_items:
        if (isinstance(item, tuple) or isinstance(item, list)) and len(item) == 2:
            feedback.setdefault(item[0], []).append(item[1])
        else:
            raise TypeError("Feedback item must be a tuple of (tag, feedback).")

    return feedback


class Result:
    __slots__ = ("is_correct", "response_latex", "response_simplified", "_feedback")
    __fields__ = (
        "is_correct",
        "response_latex",
        "response_simplified",
        "feedback",
        "tags",
    )

    is_correct: bool
    response_latex: str
    response_simplified: str

    _feedback: Dict[str, List[str]]

    def __init__(
        self,
        is_correct: bool = False,
        latex: str = "",
        simplified: str = "",
        feedback_items: List[FeedbackItem] = [],
    ):
        self.is_correct = is_correct
        self.response_latex = latex
        self.response_simplified = simplified
        self._feedback = update_feedback({}, feedback_items)

    @property
    def feedback(self) -> str:
        return "<br>".join(
            [
                feedback_str
                for lists in self._feedback.values()
                for feedback_str in lists
            ]
        )

    @property
    def tags(self) -> Union[List[str], None]:
        return list(self._feedback.keys())

    def get_feedback(self, tag: str) -> List[str]:
        return self._feedback.get(tag, [])

    def add_feedback(self, tag: str, feedback: str) -> None:
        self._feedback.setdefault(tag, []).append(feedback)

    def to_dict(self, include_test_data: bool = False) -> Dict[str, Any]:
        res = {
            "is_correct": self.is_correct,
            "feedback": self.feedback,
        }

        if self.response_simplified:
            res["response_simplified"] = self.response_simplified
        if self.response_latex:
            res["response_latex"] = self.response_latex
        if include_test_data:
            res["tags"] = self.tags

        return res

    def __repr__(self):
        members = ", ".join(f"{k}={repr(getattr(self, k))}" for k in self.__fields__)
        return f"Result({members})"

    def __eq__(self, other):
        if type(self) is not type(other):
            return False

        for k in self.__slots__:
            if getattr(self, k) != getattr(other, k):
                return False

        return True
