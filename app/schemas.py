from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

USER_ID_PATTERN = r"^[a-z0-9_-]{1,32}$"

UserId = Annotated[str, StringConstraints(pattern=USER_ID_PATTERN)]
JobStatus = Literal["queued", "processing", "succeeded", "failed"]


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    credits: int = Field(ge=0, le=10000, strict=True)


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UserId
    prompt: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    resolution: Literal[512, 1024, 2048] = 1024


class WebhookEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    status: Literal["succeeded", "failed"]
    image_url: Optional[str] = None
    error: Optional[str] = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def succeeded_requires_https_image(self):
        if self.status == "succeeded":
            if not self.image_url or not self.image_url.startswith("https://"):
                raise ValueError("succeeded exige image_url https")
        return self
