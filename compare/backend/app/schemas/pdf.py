from pydantic import BaseModel
from typing import List

class ImageRegionRequest(BaseModel):
    page_number: int
    bbox: List[float] 