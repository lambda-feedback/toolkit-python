from typing import TypedDict
from typing import List

class ChatParams(TypedDict):
    include_test_data: bool | None
    conversation_history: List[str] | None
    summary: str | None
    conversational_style: str | None
    question_response_details: str | None
    conversation_id: str | None