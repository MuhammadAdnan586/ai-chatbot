import logging
import time
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from openai import OpenAIError

from . import llm
from .ratelimit import check_rate_limit
from .schemas import ChatRequest

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("chatbot")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# If the stream breaks AFTER it started (HTTP 200 already sent), we cannot change the
# status code, so we append this marker and the browser shows an error instead.
STREAM_ERROR_MARKER = "\n\n[[STREAM_ERROR]]"

app = FastAPI(title="AI Chatbot")


@app.middleware("http")
async def access_log(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    # Only metadata is logged. Message content is never logged (privacy).
    log.info(
        "%s %s -> %s (%.0f ms)",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - start) * 1000,
    )
    return response


@app.exception_handler(llm.LLMError)
async def llm_error_handler(request: Request, exc: llm.LLMError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    message = exc.errors()[0].get("msg", "Invalid request.")
    message = message.removeprefix("Value error, ")
    return JSONResponse(status_code=422, content={"detail": message})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/chat", dependencies=[Depends(check_rate_limit)])
async def chat(req: ChatRequest):
    # Raises LLMError (-> proper 4xx/5xx JSON) if the provider fails before streaming.
    stream = await llm.open_stream(req.messages)

    async def body():
        try:
            async for text in llm.iter_text(stream):
                yield text
        except OpenAIError as exc:
            log.error("Stream interrupted: %s", type(exc).__name__)
            yield STREAM_ERROR_MARKER

    return StreamingResponse(
        body(),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )