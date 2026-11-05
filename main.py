from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from routers import auth, measurements, sensors, series
from schemas import ProblemDetail
from initial_database_seed import initialize_database


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="IoT API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _problem(request: Request, status_code: int, title: str, detail: str) -> JSONResponse:
    return problem_response(request, status_code, title, detail)


# Decorator for content negotiation and request validation rules
@app.middleware("http")
async def contract_middleware(request: Request, call_next):
    accept = request.headers.get("accept", "*/*")
    accepted = {item.split(";", 1)[0].strip().lower() for item in accept.split(",")}
    if "*/*" not in accepted and not accepted.intersection({"application/json", "application/problem+json"}):
        return _problem(request, 406, "Not Acceptable", "Only JSON responses are supported")

    if request.method in {"POST", "PUT", "PATCH"} and request.url.path != "/api/auth/logout":
        content_length = request.headers.get("content-length")
        try:
            has_body = content_length is None or int(content_length) > 0
        except ValueError:
            return _problem(request, 400, "Bad Request", "Invalid Content-Length header")
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if has_body and content_type != "application/json":
            return _problem(request, 415, "Unsupported Media Type", "Request body must use application/json")

    return await call_next(request)

app.include_router(auth.router)
app.include_router(series.router)
app.include_router(sensors.router)
app.include_router(measurements.router)


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


def problem_response(
    request: Request,
    status_code: int,
    title: str,
    detail: str,
    errors: list[dict[str, str]] | None = None,
) -> JSONResponse:
    problem = ProblemDetail(
        type="about:blank",
        title=title,
        status=status_code,
        detail=detail,
        instance=str(request.url),
        errors=errors,
    )
    return JSONResponse(status_code=status_code, content=problem.model_dump(), media_type="application/problem+json")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return problem_response(request, exc.status_code, "HTTP error", str(exc.detail))


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {
            "field": ".".join(str(part) for part in error["loc"] if part != "body"),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return problem_response(
        request,
        422,
        "Validation error",
        "Request validation failed",
        errors=errors,
    )


@app.exception_handler(Exception)
async def problem_details_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, ValueError):
        return problem_response(request, 422, "Validation error", str(exc))
    return problem_response(request, 500, "Internal Server Error", "An unexpected error occurred")
