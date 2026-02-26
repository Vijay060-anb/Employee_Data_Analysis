from sqlalchemy import Column, String, Integer, Float, Boolean
from database import Base
import uuid


class Employee(Base):
    __tablename__ = "employees"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String, unique=True, index=True)
    name = Column(String)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    department = Column(String)
    job_role = Column(String, nullable=True)
    monthly_income = Column(Float)
    years_at_company = Column(Integer, nullable=True)
    overtime = Column(Boolean, default=False)
    attrition = Column(Boolean, default=False)
    performance_rating = Column(Integer, nullable=True)
