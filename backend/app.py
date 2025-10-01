import sys, os, shutil, logging, logging.handlers
from datetime import datetime, timezone, timedelta
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from openai.types.responses import Response ,ResponseInputParam

def setup_logging() -> logging.Logger:
    logger: logging.Logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    _log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    _log_file_handler = logging.handlers.TimedRotatingFileHandler(
        '.log',
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    _log_file_handler.setLevel(logging.DEBUG)
    _log_file_handler.setFormatter(_log_formatter)
    logger.addHandler(_log_file_handler)

    _log_console_handler: logging.StreamHandler = logging.StreamHandler(sys.stdout)
    _log_console_handler.setLevel(logging.INFO)
    _log_console_handler.setFormatter(_log_formatter)
    logger.addHandler(_log_console_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return logger

load_dotenv()
app = FastAPI()
client = OpenAI()
LOGGER: logging.Logger = setup_logging()
SERVER_STARTTIME: datetime = datetime.now(timezone.utc)

class HeartbeatResponse(BaseModel):
    status: str
    timestamp: str
    uptime: int
    app_ver: str
    app_env: str
    apikey_set: bool
    disk_free_bytes: int
    message: str | None

class SummarizeRequest(BaseModel):
    inputText: str

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

@app.post("/summarize")
async def summarize(request: SummarizeRequest) -> JSONResponse:
    _input_text: str = request.inputText.strip()
    _model: str = "gpt-5"

    if not _input_text:
        LOGGER.info(f'/summarize received invalid request. Missing inputText: {request}')
        return JSONResponse(
            content={"summary":" Input text cannot be empty."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # !TODO Improve system prompt & message format
    _messages: ResponseInputParam = [
        {"role": "system", "content": "You are a concise summarization assistant. Your task is to provide a brief, professional summary of the provided text. Your summary should be in prose format, designed for stakeholders who weren't in the meeting."},
        {"role": "user", "content": f'Summarize the following text:\n\n{_input_text}'}
    ]

    # !TODO Improve successful INFO log (add necessary request info, source, etc.)
    # LOGGER.info(f'Received valid request.')
    LOGGER.debug(f'Received valid request: {request}')

    try:
        response: Response = client.responses.create(
            model=_model,
            input=_messages,
        )

        output:str = response.output_text

        # !TODO improve INFO logger
        # LOGGER.info(f'API call successful.')
        LOGGER.debug(f'API call successful. {response}')

        return JSONResponse(
            content={"summary": output},
            status_code=status.HTTP_200_OK
            )

    except Exception as e:
        LOGGER.error(f'API call failed: {e}')

        return JSONResponse(
            content={"output": f'An error has occured: {e}'},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.get("/healthcheck", response_model=HeartbeatResponse, tags=["healthcheck"])
async def get_healthcheck() -> JSONResponse:
    _current_time: datetime = datetime.now(timezone.utc)
    _uptime: timedelta = _current_time - SERVER_STARTTIME
    _uptime_seconds: int = int(_uptime.total_seconds())

    # Check critical components
    _disk_space: int | None = get_available_disk_space()
    _apikey_set: bool = bool(os.getenv('OPENAI_API_KEY'))
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

    LOGGER.debug(f'Healtcheck report sent to client. {response}')
    return JSONResponse(content=response.model_dump(), status_code=_http_status)