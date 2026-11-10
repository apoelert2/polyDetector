# Repo-wide guard: no secrets, passwords, keys or IPs in any tracked (or about-to-be-tracked) file.
# Run from the repo root: `python -m pytest`.

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

SECRET_KEY = re.compile(r"(PASS|PASSWORD|SECRET|TOKEN|API_?KEY|PRIVATE_?KEY|COOKIE)", re.IGNORECASE)
# key = "literal" in code, or KEY=value in env/yaml files; ${VAR} and empty values are fine.
QUOTED_ASSIGNMENT = re.compile(r"(?i)\b\w*(pass(word)?|secret|token|api_?key)\w*\s*[:=]\s*[\"']([^\"'\s$<{*]{4,})[\"']")
BARE_ASSIGNMENT = re.compile(r"(?im)^\s*\w*(PASS|SECRET|TOKEN|API_?KEY|COOKIE)\w*\s*[:=]\s*([^\s\"'$<{#*][^\s#]*)\s*$")
CONFIG_SUFFIXES = {".env", ".example", ".yaml", ".yml", ".properties", ".ini", ".toml", ".cfg", ".conf"}
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
ALLOWED_IPS = {"127.0.0.1", "0.0.0.0", "203.0.113.7"}  # noqa: S104 - last one is the RFC 5737 doc range
# Values that tests use on purpose to prove masking works.
TEST_FIXTURE_VALUES = {"s3cr3t-value", "wrong", "hunter22", "abcd1234"}


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    files = [ROOT / line for line in out.splitlines() if line]
    return [f for f in files if f.is_file() and f.suffix not in {".png", ".jpg", ".jar", ".ico"}]


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def env_secret_values() -> set[str]:
    env = ROOT / ".env"
    if not env.exists():
        return set()
    values = set()
    for line in read(env).splitlines():
        key, sep, value = line.partition("=")
        value = value.strip().strip("\"'")
        if sep and SECRET_KEY.search(key) and len(value) >= 4:
            values.add(value)
    return values


def test_env_file_is_ignored() -> None:
    result = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=ROOT)
    assert result.returncode == 0, ".env must be listed in .gitignore"


def test_no_local_env_secret_appears_in_repo() -> None:
    secrets = env_secret_values()
    if not secrets:
        pytest.skip("no local .env with secret values")
    leaks = [str(f.relative_to(ROOT)) for f in tracked_files() if any(s in read(f) for s in secrets)]
    assert not leaks, f"values from .env found in: {leaks}"


def test_no_hardcoded_credentials() -> None:
    findings = []
    for f in tracked_files():
        text = read(f)
        for m in QUOTED_ASSIGNMENT.finditer(text):
            if m.group(3) not in TEST_FIXTURE_VALUES:
                findings.append(f"{f.relative_to(ROOT)}: {m.group(0)[:40]}")
        if f.suffix in CONFIG_SUFFIXES or f.name.startswith(".env"):  # unquoted values only exist in config files
            findings += [f"{f.relative_to(ROOT)}: {m.group(0)[:40]}" for m in BARE_ASSIGNMENT.finditer(text)]
        if PRIVATE_KEY.search(text):
            findings.append(f"{f.relative_to(ROOT)}: private key")
    assert not findings, "possible credentials:\n" + "\n".join(findings)


def test_no_ip_addresses() -> None:
    findings = []
    for f in tracked_files():
        for line in read(f).splitlines():
            # shortcut: lines with "version" are skipped, since 4-part versions (4.8.6.6) look like IPs.
            if "version" in line.lower():
                continue
            findings += [f"{f.relative_to(ROOT)}: {ip}" for ip in IPV4.findall(line) if ip not in ALLOWED_IPS]
    assert not findings, "IP addresses found:\n" + "\n".join(findings)


def test_scanner_catches_known_leaks() -> None:
    # Self-check: the patterns must fire on obvious leaks, or the tests above prove nothing.
    assert QUOTED_ASSIGNMENT.search('password = "hunter22"')
    assert QUOTED_ASSIGNMENT.search('api_key: "abcd1234"')
    assert BARE_ASSIGNMENT.search("TIMESCALE_PASS=hunter22")
    assert BARE_ASSIGNMENT.search("  POSTGRES_PASSWORD: hunter22")
    assert not BARE_ASSIGNMENT.search("TIMESCALE_PASS=")
    assert not BARE_ASSIGNMENT.search("POSTGRES_PASSWORD: ${TIMESCALE_PASS:?set it}")
    assert IPV4.search("host=203.0.113.7")
