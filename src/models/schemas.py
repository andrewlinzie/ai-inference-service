from pydantic import BaseModel
from typing import List


class InferenceRequest(BaseModel):
    request_id: str
    input_type: str
    content: str


class InferenceResponse(BaseModel):
    summary: str
    signals: List[str]
    recommendation: str