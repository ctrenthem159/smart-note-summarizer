import os, shutil
from datetime import datetime, timezone, timedelta
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()
api_key: str = os.environ["OPENAI_APIKEY"]

class HeartbeatResponse(BaseModel):
    status: str
    timestamp: str
    uptime: int
    app_ver: str
    app_env: str
    apikey_set: bool
    disk_free_bytes: int
    message: str | None

SERVER_STARTTIME: datetime = datetime.now(timezone.utc)
app = FastAPI()

origins: list[str] = [
    "http://localhost:5173", # Svelte dev server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_available_disk_space(path: str = ".") -> Optional[int]:
    try:
        _usage = shutil.disk_usage(path)
        return _usage.free
    except Exception:
        return None

# @app.get("/summarize")
# async def summarize(inputText: str) -> JSONResponse:
#     pass

@app.get("/healthcheck", response_model=HeartbeatResponse, tags=["healthcheck"])
async def get_healthcheck() -> JSONResponse:
    _current_time: datetime = datetime.now(timezone.utc)
    _uptime: timedelta = _current_time - SERVER_STARTTIME
    _uptime_seconds: int = int(_uptime.total_seconds())

    # Check critical components
    _disk_space: int | None = get_available_disk_space()
    _apikey_set: bool = bool(os.getenv('OPENAI_APIKEY'))
    _is_healthy: bool = True
    _fail_reasons: list[str]=  []

    if _disk_space is None:
        _is_healthy = False
        _disk_space = 0
        _fail_reasons.append('Critical: Hard disk read error.')
    elif _disk_space < (1 * 1024 * 1024 * 1024): # Set minimum disk space to 1GB
        _is_healthy = False
        _fail_reasons.append('Critical: Insufficient storage space on disk.')

    if not _apikey_set:
        _is_healthy = False
        _fail_reasons.append('Critical: OPENAI_APIKEY missing.')

    if _is_healthy:
        _status_check: str = "Healthy"
        _http_status = status.HTTP_200_OK
    else:
        _status_check: str = "Unhealthy"
        _http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    # Compile response
    response = HeartbeatResponse(
        status = _status_check,
        timestamp = _current_time.isoformat(timespec='seconds'),
        uptime = _uptime_seconds,
        # !TODO validate app_ver complies with semantic versioning
        app_ver = os.environ['APP_VERSION'],
        # !TODO validate app_env is one of "dev" or "prod"
        app_env = os.environ['APP_ENVIRONMENT'],
        apikey_set = _apikey_set,
        disk_free_bytes = _disk_space if _disk_space is not None else 0,
        message = ", ".join(_fail_reasons) if _fail_reasons else None,
    )

    return JSONResponse(content=response.model_dump(), status_code=_http_status)