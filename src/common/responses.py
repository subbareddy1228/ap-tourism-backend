import math
from typing import Any, List
from fastapi import HTTPException
from fastapi.responses import JSONResponse


def success_response(data: Any = None, message: str = "", status_code: int = 200):
    return JSONResponse(
        status_code=status_code,
        content={"success": True, "data": data, "message": message}
    )


def created_response(data: Any = None, message: str = "Created successfully"):
    return JSONResponse(
        status_code=201,
        content={"success": True, "data": data, "message": message}
    )


def list_response(data: List[Any], total: int, page: int, limit: int, message: str = ""):
    pages = math.ceil(total / limit) if total > 0 else 1
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "data": data,
            "total": total,
            "page": page,
            "pages": pages,
            "message": message
        }
    )


def error_response(message: str, code: int = 400):
    return JSONResponse(
        status_code=code,
        content={"success": False, "error": message, "code": code}
    )


def not_found(msg: str = "Not found"):         raise HTTPException(404, msg)
def bad_request(msg: str = "Bad request"):     raise HTTPException(400, msg)
def forbidden(msg: str = "Forbidden"):         raise HTTPException(403, msg)
def unauthorized(msg: str = "Unauthorized"):   raise HTTPException(401, msg)
def conflict(msg: str = "Already exists"):     raise HTTPException(409, msg)
def server_error(msg: str = "Server error"):   raise HTTPException(500, msg)
