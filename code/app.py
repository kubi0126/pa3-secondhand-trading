"""应用入口，兼容 flask --app app run。"""

from secondhand.scheduler import start_scheduler
from secondhand.web.app_factory import create_app

app = create_app({"SCHEDULER_ENABLED": True})
start_scheduler(app)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
