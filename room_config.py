from typing import List, Optional
from dataclasses import dataclass

@dataclass
class RoomConfig:
    years: List[int]
    genres: Optional[List[str]] = None
    voting_duration: Optional[int] = None

    def __post_init__(self):
        if not self.years:
            raise ValueError("Years list cannot be empty")
        
        if self.genres is None:
            self.genres = [] 