from fastapi import FastAPI, APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from starlette.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import pandas as pd
import io

from database import get_db, engine, Base
from models import Employee
from ml_service import MLService


# ---------------- ENV ----------------
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env", override=True)

app = FastAPI(title="Payroll Analytics API", version="1.0.0")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------- ROOT ----------------
@app.get("/")
async def root():
    return {"message": "Payroll Analytics API running"}


# ---------------- HEALTH ----------------
@api_router.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ---------------- STARTUP ----------------
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")


@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()


# ---------------- RESPONSE MODELS ----------------
class EmployeeResponse(BaseModel):
    id: str
    employee_id: str
    name: str
    department: str
    monthly_income: float


class KPIResponse(BaseModel):
    total_employees: int
    total_payroll_cost: float
    avg_salary: float


# ---------------- KPI ----------------
@api_router.get("/kpis", response_model=KPIResponse)
async def get_kpis(db: AsyncSession = Depends(get_db)):
    total_employees = (await db.execute(
        select(func.count(Employee.id))
    )).scalar() or 0

    total_payroll_cost = (await db.execute(
        select(func.sum(Employee.monthly_income))
    )).scalar() or 0

    avg_salary = total_payroll_cost / total_employees if total_employees else 0

    return KPIResponse(
        total_employees=total_employees,
        total_payroll_cost=round(total_payroll_cost, 2),
        avg_salary=round(avg_salary, 2)
    )


# ---------------- EMPLOYEES ----------------
@api_router.get("/employees", response_model=List[EmployeeResponse])
async def get_employees(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Employee))
    employees = result.scalars().all()

    return [
        EmployeeResponse(
            id=e.id,
            employee_id=e.employee_id,
            name=e.name,
            department=e.department,
            monthly_income=e.monthly_income
        )
        for e in employees
    ]


# ---------------- DATASET UPLOAD (CSV + XLSX) ----------------
@api_router.post("/etl/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    contents = await file.read()

    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
        elif file.filename.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(400, "Upload CSV or XLSX only")
    except Exception as e:
        raise HTTPException(400, f"File error: {str(e)}")

    df.columns = df.columns.str.strip()

    for _, row in df.iterrows():
        employee = Employee(
            id=str(uuid.uuid4()),
            employee_id=row.get("EmployeeID"),
            name=row.get("Name"),
            department=row.get("Department"),
            monthly_income=float(row.get("MonthlyIncome", 0))
        )
        db.add(employee)

    await db.commit()

    return {
        "status": "success",
        "rows_inserted": len(df)
    }


# ---------------- ML TRAIN ----------------
@api_router.post("/ml/train")
async def train_ml(db: AsyncSession = Depends(get_db)):
    ml = MLService(db)
    return await ml.train_models()


# ---------------- INCLUDE ROUTER ----------------
app.include_router(api_router)


# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)