from fastapi import FastAPI
from app.database import create_db_and_tables
from app.routers import auth, users, colleges

app = FastAPI()

# Include Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(colleges.router)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/")
def read_root():
    return {"message": "Tenexis Backend Running"}