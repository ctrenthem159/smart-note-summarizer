import os, shutil, json
from datetime import datetime, timezone, timedelta
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from openai.types.responses import Response ,ResponseInputParam

load_dotenv()
app = FastAPI()
client = OpenAI()

SERVER_STARTTIME: datetime = datetime.now(timezone.utc)
LOG_DIR = "api_logs"

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

def save_log(filename: str, data: dict):
    os.makedirs(LOG_DIR, exist_ok=True)
    filepath= os.path.join(LOG_DIR, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f'Log saved to: {filepath}')

@app.post("/summarize")
async def summarize(request: SummarizeRequest) -> JSONResponse:
    _input_text = request.inputText.strip()

    if not _input_text:
        return JSONResponse(
            content={"summary":" Input text cannot be empty."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # !TODO Improve system prompt & message format
    messages: ResponseInputParam = [
        {"role": "system", "content": "You are a concise summarization assistant. Your task is to provide a brief, professional summary of the provided text. Your summary should be in prose format, designed for stakeholders who weren't in the meeting."},
        {"role": "user", "content": f'Summarize the following text:\n\n{_input_text}'}
    ]

    # !TODO Improve logging structure
    log_filename: str = datetime.now().strftime('req_%Y%m%d_%H%M%S.json')
    request_log = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_text_length": len(_input_text),
        "messages": messages,
        "model": "gpt-5"
    }
    save_log(log_filename, request_log)

    try:
        response: Response = client.responses.create(
            model="gpt-5",
            input=messages,
        )

        output:str = response.output_text

        response_log_filename: str = log_filename.replace("req_", "res_")
        response_log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "messages": response.model_dump(),
            "model": "gpt-5"
        }
        save_log(response_log_filename, response_log)

        return JSONResponse(
            content={"summary": output},
            status_code=status.HTTP_200_OK
            )
    except Exception as e:
        error_message = f'LLM API Error: {e}'
        print(error_message)
        error_log_filename = log_filename.replace("req_", "err_")
        save_log(error_log_filename, {"error": error_message, "request": request_log})

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

    return JSONResponse(content=response.model_dump(), status_code=_http_status)