from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IncidentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    severity: str
    service: str
    status: str
    session_id: str
    started_at: datetime
    resolved_at: datetime | None


class EvidenceItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    data_id: str
    dataset: str
    name: str
    kind: str
    source_uri: str | None
    status: str
    content_hash: str
    is_stale: bool
