from pydantic import BaseModel


class uploadBody(BaseModel):
    userId: str
