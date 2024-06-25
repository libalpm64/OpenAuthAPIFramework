from fastapi import APIRouter

# Create an instance of APIRouter
router = APIRouter()

# Example Route - Libalpm Instructional.
@router.get("/hello")
async def read_root():
    return {"message": "Hello, World!"}