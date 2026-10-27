from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from routers import auth, measurements, sensors, series
from schemas import ProblemDetail

app = FastAPI(title="IoT API", version="1.0.0")

app.include_router(auth.router)
app.include_router(series.router)
app.include_router(sensors.router)
app.include_router(measurements.router)


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


def problem_response(request: Request, status_code: int, title: str, detail: str) -> JSONResponse:
    problem = ProblemDetail(
        type="about:blank",
        title=title,
        status=status_code,
        detail=detail,
        instance=str(request.url),
    )
    return JSONResponse(status_code=status_code, content=problem.model_dump(), media_type="application/problem+json")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return problem_response(request, exc.status_code, "HTTP error", str(exc.detail))


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return problem_response(request, 422, "Validation error", str(exc.errors()))


@app.exception_handler(Exception)
async def problem_details_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, ValueError):
        return problem_response(request, 422, "Validation error", str(exc))
    return problem_response(request, 500, "Internal Server Error", "An unexpected error occurred")
