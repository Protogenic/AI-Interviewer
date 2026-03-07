from fastapi import APIRouter


router = APIRouter(
    prefix = "/health",
    tags = ["health"]
)


@router.get("/health")
async def get_health() -> dict[str, str]:
    return {"status": "ok"}
