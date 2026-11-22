"""python -m secondhand 入口。"""

from __future__ import annotations

from .scheduler import start_scheduler
from .web.app_factory import create_app

app = create_app({"SCHEDULER_ENABLED": True})


def main() -> None:
    start_scheduler(app)
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)


if __name__ == "__main__":
    main()
