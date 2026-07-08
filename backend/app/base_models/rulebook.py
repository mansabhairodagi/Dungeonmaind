from pydantic import BaseModel


class FolderContent(BaseModel):
    folders: list[str]
    files: list[str]


FolderStructure = dict[str, FolderContent]


class FileContentResponse(BaseModel):
    content: str
