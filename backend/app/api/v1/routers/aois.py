from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from app.infrastructure.db.database import get_db
from app.infrastructure.db.models import AOIModel

router = APIRouter(prefix="/aois", tags=["AOIs"])

class AOICreate(BaseModel):
    name: str
    geom: Dict[str, Any]  # GeoJSON dict
    properties: Optional[Dict[str, Any]] = None

class AOIResponse(BaseModel):
    id: int
    name: str
    properties: Optional[Dict[str, Any]] = None
    # For a full response, geom might be serialized from WKB to GeoJSON, 
    # but for simplicity we'll just return basic info here.
    
    class Config:
        from_attributes = True

@router.post("/", response_model=AOIResponse, status_code=status.HTTP_201_CREATED)
async def create_aoi(aoi: AOICreate, db: AsyncSession = Depends(get_db)):
    # In a real scenario, you'd get the user_id from the authenticated token
    # For now, hardcoding user_id=1
    user_id = 1 
    
    import json
    geom_str = json.dumps(aoi.geom)
    
    # Using ST_GeomFromGeoJSON for PostGIS insertion
    from sqlalchemy import func
    
    new_aoi = AOIModel(
        name=aoi.name,
        geom=func.ST_SetSRID(func.ST_GeomFromGeoJSON(geom_str), 4326),
        properties=aoi.properties,
        user_id=user_id
    )
    
    db.add(new_aoi)
    await db.commit()
    await db.refresh(new_aoi)
    
    return new_aoi

@router.get("/", response_model=List[AOIResponse])
async def list_aois(db: AsyncSession = Depends(get_db)):
    stmt = select(AOIModel)
    result = await db.execute(stmt)
    aois = result.scalars().all()
    return aois
