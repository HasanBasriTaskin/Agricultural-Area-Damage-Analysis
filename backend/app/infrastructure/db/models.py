from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from .database import Base

class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    aois = relationship("AOIModel", back_populates="owner")

class AOIModel(Base):
    __tablename__ = "aois"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    geom = Column(Geometry(geometry_type='GEOMETRY', srid=4326), nullable=False)
    properties = Column(JSON, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    owner = relationship("UserModel", back_populates="aois")
