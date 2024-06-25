import uvicorn
from fastapi import FastAPI
from routes.main_routes import router as main_router
from routes.ipinfo import router as ipinfo_router
from routes.pytauth import router as pytauth_router

app = FastAPI()

# Include your main router
app.include_router(main_router)
app.include_router(pytauth_router)
app.include_router(ipinfo_router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8611, access_log=False)