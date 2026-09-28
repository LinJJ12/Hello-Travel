"""开发环境启动脚本。

用法：python run.py
生产环境请使用 uvicorn/gunicorn 直接拉起 `app.api.main:app`（见 Dockerfile）。
"""

import uvicorn

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "app.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
