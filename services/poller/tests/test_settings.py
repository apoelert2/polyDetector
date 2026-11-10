import pytest
from settings import DbSettings


def test_password_never_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMESCALE_DB", "db")
    monkeypatch.setenv("TIMESCALE_USER", "user")
    monkeypatch.setenv("TIMESCALE_PASS", "s3cr3t-value")
    settings = DbSettings.from_env()
    assert "s3cr3t-value" not in repr(settings)
    assert "s3cr3t-value" not in str(settings)


def test_missing_password_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMESCALE_DB", "db")
    monkeypatch.setenv("TIMESCALE_USER", "user")
    monkeypatch.delenv("TIMESCALE_PASS", raising=False)
    with pytest.raises(RuntimeError, match="TIMESCALE_PASS"):
        DbSettings.from_env()
