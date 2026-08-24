from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class DeviceStartOut(BaseModel):
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int


class DeviceConfirmIn(BaseModel):
    user_code: str


class DevicePollOut(BaseModel):
    status: str  # "pending" | "confirmed"
    api_key: Optional[str] = None
    signing_key: Optional[str] = None
