from dataclasses import dataclass
from dataclasses import field


@dataclass
class Result:
    is_correct: bool = False
    latex: str = ""
    simplified: str = ""
    _feedback: list = field(default_factory=list)
    _feedback_tags: dict = field(default_factory=dict)

    def get_feedback(self, tag):
        return self._feedback_tags.get(tag, None)

    def get_tags(self):
        return list(self._feedback_tags.keys())

    def add_feedback(self, feedback_item):
        if isinstance(feedback_item, tuple):
            self._feedback.append(feedback_item[1])
            if feedback_item[0] not in self._feedback_tags.keys():
                self._feedback_tags.update(
                    {feedback_item[0]: [len(self._feedback) - 1]}
                )
            else:
                self._feedback_tags[feedback_item[0]].append(len(self._feedback) - 1)
        else:
            raise TypeError("Feedback must be on the form (tag, feedback).")
        self._feedback_tags

    def _serialise_feedback(self) -> str:
        return "<br>".join(x[1] if isinstance(x, tuple) else x for x in self._feedback)

    def serialise(self, include_test_data=False) -> dict:
        out = dict(is_correct=self.is_correct, feedback=self._serialise_feedback())
        if include_test_data is True:
            out.update(dict(tags=self._feedback_tags))
        if self.latex is not None:
            out.update(dict(response_latex=self.latex))
        if self.simplified is not None:
            out.update(dict(response_simplified=self.simplified))
        return out

    def __getitem__(self, key):
        return self.serialise(include_test_data=True)[key]
