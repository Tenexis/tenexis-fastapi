from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import create_db_and_tables
from app.routers import auth, users, colleges, products
from fastapi.staticfiles import StaticFiles

app = FastAPI()

origins = [
    "http://localhost:3000",
    "https://your-frontend-domain.pages.dev", # Your Cloudflare URL
    "https://hdtr68dq-3000.inc1.devtunnels.ms",
    "https://tenexis-thrift.tenexis.workers.dev",
    "https://tenexis.com",
]

# 3. Add the Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # Allows your Next.js app to talk to FastAPI
    allow_credentials=True,           # Allows cookies/auth headers
    allow_methods=["*"],              # Allows POST, GET, OPTIONS, etc.
    allow_headers=["*"],              # Allows Authorization, Content-Type, etc.
)

# Include Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(colleges.router)
app.include_router(products.router)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/")
def read_root():
    return {"message": "Tenexis Backend Running"}