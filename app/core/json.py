# app/core/json.py
from typing import Any
import json
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse

class UTF8JSONResponse(JSONResponse):
    """
    Respuesta JSON garantizada en UTF-8, sin escapes ASCII y con
    jsonable_encoder previo (convierte datetime, etc.).
    """
    media_type = "application/json; charset=utf-8"

    def render(self, content: Any) -> bytes:
        payload = jsonable_encoder(content, exclude_none=False)
        return json.dumps(
            payload,
            ensure_ascii=False,   # 👈 no escapar \uXXXX
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
