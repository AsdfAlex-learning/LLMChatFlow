from __future__ import annotations

import json
import logging
import os
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Mapping, Optional


class JsonLineFormatter(logging.Formatter):
    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        ts = time.gmtime(record.created)
        return time.strftime("%Y-%m-%dT%H:%M:%S", ts) + f".{int(record.msecs):03d}Z"

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "file": record.pathname,
            "process": record.process,
            "thread": record.thread,
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class ProcessSafeRotatingFileHandler(RotatingFileHandler):
    _thread_lock = threading.Lock()

    def _acquire_process_lock(self) -> Any:
        if os.name != "nt":
            return None
        try:
            import msvcrt

            msvcrt.locking(self.stream.fileno(), msvcrt.LK_LOCK, 1)
            return msvcrt
        except Exception:
            return None

    def _release_process_lock(self, msvcrt_module: Any) -> None:
        if os.name != "nt":
            return
        if not msvcrt_module:
            return
        try:
            msvcrt_module.locking(self.stream.fileno(), msvcrt_module.LK_UNLCK, 1)
        except Exception:
            return

    def emit(self, record: logging.LogRecord) -> None:
        with self._thread_lock:
            if self.stream is None:
                self.stream = self._open()
            msvcrt_module = self._acquire_process_lock()
            try:
                super().emit(record)
            finally:
                self._release_process_lock(msvcrt_module)


def _parse_level(level: str) -> int:
    if not isinstance(level, str):
        return logging.INFO
    name = level.strip().upper()
    if not name:
        return logging.INFO
    value = getattr(logging, name, None)
    if isinstance(value, int):
        return value
    return logging.INFO


def _remove_managed_handlers(logger: logging.Logger) -> None:
    kept = []
    for h in logger.handlers:
        if getattr(h, "_llmchatflow_managed", False):
            try:
                h.close()
            except Exception:
                pass
            continue
        kept.append(h)
    logger.handlers[:] = kept


def configure_logging(
    *,
    level: str = "INFO",
    console: bool = True,
    file_path: str = "",
    json_logs: bool = False,
) -> None:
    logger = logging.getLogger("llmchatflow")
    _remove_managed_handlers(logger)

    parsed_level = _parse_level(level)
    logger.setLevel(parsed_level)
    logger.propagate = False

    formatter: logging.Formatter
    if json_logs:
        formatter = JsonLineFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    if console:
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        sh._llmchatflow_managed = True
        logger.addHandler(sh)

    if file_path and str(file_path).strip():
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        fh = ProcessSafeRotatingFileHandler(
            str(p),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
            delay=True,
        )
        fh.setFormatter(formatter)
        fh._llmchatflow_managed = True
        logger.addHandler(fh)

    if isinstance(level, str):
        name = level.strip().upper()
        if name and name not in logging._nameToLevel:
            logger.warning("Invalid logging_level value '%s'; using INFO", level)


def configure_logging_from_config(cfg: Optional[object]) -> None:
    if cfg is None:
        configure_logging()
        return
    try:
        if isinstance(cfg, Mapping):
            level = cfg.get("logging_level", "INFO")
            console = bool(cfg.get("logging_console", True))
            file_path = str(cfg.get("logging_file_path", "") or "")
            json_logs = bool(cfg.get("logging_json", False))
        else:
            level = getattr(cfg, "logging_level", "INFO")
            console = bool(getattr(cfg, "logging_console", True))
            file_path = str(getattr(cfg, "logging_file_path", "") or "")
            json_logs = bool(getattr(cfg, "logging_json", False))
    except Exception:
        configure_logging()
        return
    configure_logging(level=str(level), console=console, file_path=file_path, json_logs=json_logs)
