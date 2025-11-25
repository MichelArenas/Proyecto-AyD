"""
Entry point for running the FastAPI application using Uvicorn.
"""

import uvicorn

from app.core import config


def main():
    """
    Run the FastAPI application with Uvicorn server.
    """
    uvicorn.run(
        "app.api:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.debug,
    )


if __name__ == "__main__":
    main()
