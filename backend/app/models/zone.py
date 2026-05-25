\"\"\"models/zone.py\"\"\"
from __future__ import annotations
from typing import List, Tuple
from sqlalchemy import Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.session import Base

class Zone(Base):
    __tablename__ = \"zones\"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    polygon: Mapped[List[Tuple[int, int]]] = mapped_column(JSON, nullable=False) # List of [x, y] points
    current_occupancy: Mapped[int] = mapped_column(Integer, default=0)
    threshold: Mapped[int] = mapped_column(Integer, default=5)
