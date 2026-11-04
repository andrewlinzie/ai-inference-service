from pydantic import BaseModel, ConfigDict


class InferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    amount: float
    hour_of_day: float
    day_of_week: float
    merchant_risk: float
    device_trust: float
    is_international: float


class InferenceResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    request_id: str
    model_version: str
    is_fraud: int
    probability_fraud: float
