"""Development entrypoint."""

import logging

from rich.logging import RichHandler


def create_debug_app():
    """Workaround to use different logger for debug."""
    import fastapi
    import starlette
    import uvicorn

    rich_handler = RichHandler(
        rich_tracebacks=True, tracebacks_suppress=[fastapi, starlette, uvicorn]
    )
    file_handler = logging.FileHandler("dev.log", mode="a", encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
    )

    logging.basicConfig(
        handlers=[rich_handler, file_handler],
        level=logging.NOTSET,
    )
    logging.getLogger("src").setLevel(logging.DEBUG)

    from src import create_app

    return create_app()


if __name__ == "__main__":
    import uvicorn

    rich_handler = RichHandler(rich_tracebacks=True)
    file_handler = logging.FileHandler("dev.log", mode="a", encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
    )

    logging.basicConfig(
        handlers=[rich_handler, file_handler],
        level=logging.NOTSET,
    )

    uvicorn.run(
        "dev:create_debug_app",
        host="localhost",
        port=3000,
        log_level=logging.INFO,
        reload=True,
        factory=True,
        log_config=None,
    )
