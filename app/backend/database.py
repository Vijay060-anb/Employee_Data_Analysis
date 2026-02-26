from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite+aiosqlite:///./payroll.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

# This is the missing function causing your error
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
