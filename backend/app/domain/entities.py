from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class User:
    email: str
    hashed_password: str
    role: str
    is_active: bool = True
    id: Optional[int] = None
    created_at: Optional[datetime] = None

@dataclass
class AOI:
    name: str
    geom: Any  # PostGIS geometry (e.g. Polygon/MultiPolygon mapping)
    user_id: int
    id: Optional[int] = None
    properties: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
