from pydantic import BaseModel
from typing import Optional

class TournamentInfoBase(BaseModel):
    name: str
    logo_path_local: Optional[str] = None
    logo_url_cloud: Optional[str] = None
    website_url: Optional[str] = None

class TournamentInfoCreate(TournamentInfoBase):
    pass

class TournamentInfo(TournamentInfoBase):
    id: int

    class Config:
        orm_mode = True
