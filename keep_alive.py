import os
from threading import Thread

from flask import Flask

app = Flask(__name__)


@app.get("/")
def health() -> tuple[str, int]:
    return "ok", 200


def _run() -> None:
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)


def start() -> None:
    Thread(target=_run, daemon=True).start()
