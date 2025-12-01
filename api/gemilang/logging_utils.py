import logging
from typing import Any, Dict, Optional

LOG_NAMESPACE = "api.gemilang"


def _sanitize_log_input(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("\n", " ").replace("\r", " ")
    return value


class GemilangLogger(logging.LoggerAdapter):
    def __init__(self, component: str, extra: Optional[Dict[str, Any]] = None):
        base_logger = logging.getLogger(LOG_NAMESPACE)
        merged_extra = {"component": component}
        if extra:
            merged_extra.update(extra)
        super().__init__(base_logger, merged_extra)

    def process(self, msg, kwargs):
        msg = _sanitize_log_input(msg)
        extra = kwargs.pop("extra", {})
        component = _sanitize_log_input(self.extra.get("component", "gemilang"))
        operation = extra.get("operation") or self.extra.get("operation")
        prefix_parts = [f"[gemilang][component={component}]"]
        if operation:
            prefix_parts.append(f"[op={_sanitize_log_input(operation)}]")
        prefixed = " ".join(prefix_parts) + f" {msg}"
        kwargs["extra"] = {**self.extra, **extra}
        return prefixed, kwargs

    def log(self, level, msg, *args, **kwargs):
        if not self.isEnabledFor(level):
            return
        msg, kwargs = self.process(_sanitize_log_input(msg), kwargs)
        clean_args = tuple(_sanitize_log_input(arg) for arg in args)
        self.logger.log(level, msg, *clean_args, **kwargs)


def get_gemilang_logger(component: str, extra: Optional[Dict[str, Any]] = None) -> GemilangLogger:
    return GemilangLogger(component, extra)
