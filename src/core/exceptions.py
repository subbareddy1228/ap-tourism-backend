"""

core/exceptions.py

Global exception handlers — registered in main.py.

Prevents raw stack traces from being exposed to clients.

"""
 
import logging

from fastapi import FastAPI, Request, status

from fastapi.responses import JSONResponse

from fastapi.exceptions import RequestValidationError

from sqlalchemy.exc import SQLAlchemyError
 
logger = logging.getLogger(__name__)
 
 
# ═══════════════════════════════════════════════════════════════

# REGISTER ALL HANDLERS

# ═══════════════════════════════════════════════════════════════
 
def register_exception_handlers(app: FastAPI) -> None:

    """

    Call this in main.py after creating the FastAPI app:

        from src.core.exceptions import register_exception_handlers

        register_exception_handlers(app)

    """
 
    # ── 422 Pydantic Validation Error ────────────────────────

    @app.exception_handler(RequestValidationError)

    async def validation_exception_handler(request: Request, exc: RequestValidationError):

        errors = []

        for error in exc.errors():

            field = " → ".join(str(loc) for loc in error["loc"])

            errors.append({"field": field, "message": error["msg"]})
 
        logger.warning(

            "Validation error url=%s errors=%s",

            request.url.path, errors

        )
 
        return JSONResponse(

            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,

            content={

                "success": False,

                "error":   "Validation failed",

                "code":    422,

                "details": errors,

            }

        )
 
    # ── 500 SQLAlchemy DB Error ───────────────────────────────

    @app.exception_handler(SQLAlchemyError)

    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):

        logger.error(

            "Database error url=%s error=%s",

            request.url.path, str(exc)

        )
 
        return JSONResponse(

            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

            content={

                "success": False,

                "error":   "A database error occurred. Please try again.",

                "code":    500,

            }

        )
 
    # ── 500 Catch-All Unhandled Exception ────────────────────

    @app.exception_handler(Exception)

    async def generic_exception_handler(request: Request, exc: Exception):

        logger.error(

            "Unhandled exception url=%s error=%s",

            request.url.path, str(exc),

            exc_info=True

        )
 
        return JSONResponse(

            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

            content={

                "success": False,

                "error":   "An unexpected error occurred. Please try again.",

                "code":    500,

            }

        )
 