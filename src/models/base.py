import uuid
from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from src.core.database import Base


class BaseModel(Base):
    __abstract__ = True

    id         = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        result = {}
        for c in self.__table__.columns:
            val = getattr(self, c.name)
            if hasattr(val, 'isoformat'):
                result[c.name] = val.isoformat()
            elif hasattr(val, 'value'):
                result[c.name] = val.value
            else:
                result[c.name] = val
        return result
