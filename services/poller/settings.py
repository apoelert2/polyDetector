import os
from dataclasses import dataclass, field


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is not set")
    return value


@dataclass(frozen=True)
class DbSettings:
    host: str
    port: int
    name: str
    user: str
    password: str = field(repr=False)  # never in logs or tracebacks

    @classmethod
    def from_env(cls) -> "DbSettings":
        return cls(
            host=os.getenv("TIMESCALE_HOST", "localhost"),
            port=int(os.getenv("TIMESCALE_PORT", "5432")),
            name=_required("TIMESCALE_DB"),
            user=_required("TIMESCALE_USER"),
            password=_required("TIMESCALE_PASS"),
        )
