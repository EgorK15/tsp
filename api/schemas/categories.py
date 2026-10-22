from pydantic import BaseModel, ConfigDict, Field


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class StageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    kind: str
    sort_order: int
