from typing import Any
from typing import Dict
from typing import List
from typing import Tuple
from typing import Union

ResponseItem = Tuple[str, str]

def update_response(
    response: Dict[str, List[str]], response_items: List[ResponseItem]
) -> Dict[str, List[str]]:
    for item in response_items:
        if (isinstance(item, tuple) or isinstance(item, list)) and len(item) == 2:
            response.setdefault(item[0], []).append(item[1])
        else:
            raise TypeError("Response item must be a tuple of (tag, chatbot_response).")

    return response


class ChatResult:
    __slots__ = ("_response",
                 "_metadata", 
                 "_processing_time")
    __fields__ = (
        "response",
        "tags",
        "metadata",
        "processing_time",
    )

    _response: Dict[str, List[str]]

    _metadata: Dict[str, Any]
    _processing_time: float

    def __init__(
        self,
        response_items: List[ResponseItem] = [],
        metadata: Dict[str, Any] = {},
        processing_time: float = 0,
    ):
        self._response = update_response({}, response_items)
        self._metadata = metadata
        self._processing_time = processing_time

    @property
    def response(self) -> str:
        return "<br>".join(
            [
                response_str
                for lists in self._response.values()
                for response_str in lists
            ]
        )

    @property
    def tags(self) -> Union[List[str], None]:
        return list(self._response.keys())
    
    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata


    def get_response(self, tag: str) -> List[str]:
        return self._response.get(tag, [])
    
    def get_processing_time(self) -> float:
        return self._processing_time

    def add_response(self, tag: str, response: str) -> None:
        self._response.setdefault(tag, []).append(response)

    def add_metadata(self, name: str, data: Any) -> None:
        self._metadata[name] = data

    def add_processing_time(self, time: float) -> None:
        self._processing_time = time

    def to_dict(self, include_test_data: bool = False) -> Dict[str, Any]:
        res = {
            "chatbot_response": self.response,
        }

        if include_test_data:
            res["tags"] = self.tags
            if len(self.metadata) > 0:
                res["metadata"] = self.metadata
            if self._processing_time >= 0:
                res["processing_time"] = self._processing_time

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