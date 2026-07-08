from pydantic import BaseModel, Field


class EmbeddRequest(BaseModel):
    input_string: str = Field(..., description='Text to be embedded')


class EmbeddResponse(BaseModel):
    markdown_texts: list[str]


class EmbeddingSearch(BaseModel):
    input_string: str = Field(..., description='Search string for embedding search')
