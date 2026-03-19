from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def aerospace_placeholder():
    return {"message": "Aerospace route working"}
