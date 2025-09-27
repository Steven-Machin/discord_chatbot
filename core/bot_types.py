from __future__ import annotations

import logging
from typing import Any

from typing_extensions import Protocol


class BotWithLogger(Protocol):
    logger: logging.Logger
    error_logger: logging.Logger
    command_logger: logging.Logger

    def __getattr__(self, name: str) -> Any:  # pragma: no cover - structural helper
        ...
