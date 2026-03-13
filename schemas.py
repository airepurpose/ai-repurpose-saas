from pydantic import BaseModel

class UserLogin(BaseModel):
    email: str
    password: str
from pydantic import BaseModel
from typing import List

class RepurposeRequest(BaseModel):
    text: str
    targets: List[str]
    n_variations: int = 1
