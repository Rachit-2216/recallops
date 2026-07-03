import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DATASET = "recallops_evidence_v1"
TEXT_SUFFIXES = {
    "",
    ".css",
    ".dockerignore",
    ".example",
    ".html",
    ".js",
    ".json",
    ".lock",
    ".log",
    ".md",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
COGNEE_KEY_PATTERN = re.compile(
    r"\bcognee_(?:key|sk)_[A-Za-z0-9_-]{12,}\b",
    re.IGNORECASE,
)
NONEMPTY_KEY_ASSIGNMENT = re.compile(
    r"COGNEE_API_KEY[ \t]*=[ \t]*[\"']?[A-Za-z0-9_-]{8,}",
)
DIRECT_COGNEE_IMPORT = re.compile(
    r"^\s*(?:from\s+cognee(?:\.|\s)|import\s+cognee(?:\.|\s|$))",
    re.MULTILINE,
)
FORGET_EVERYTHING = re.compile(r"forget\s*\([^)]*everything\s*=\s*True")
DATASET_PATTERN = re.compile(r"\brecallops_evidence_v[0-9]+\b")


def git_executable() -> str:
    executable = shutil.which("git")
    if executable is None:
        raise RuntimeError("git is required for repository preflight")
    return executable


def repository_files() -> list[Path]:
    result = subprocess.run(  # noqa: S603 - resolved git path, fixed arguments
        [
            git_executable(),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    paths = []
    for raw in result.stdout.decode("utf-8").split("\0"):
        if not raw:
            continue
        path = ROOT / raw
        if path.is_file() and path.suffix.casefold() in TEXT_SUFFIXES:
            paths.append(path)
    return paths


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_test(path: Path) -> bool:
    parts = {part.casefold() for part in path.parts}
    return "tests" in parts or "e2e" in parts


def run_checks() -> list[str]:
    failures: list[str] = []
    files = repository_files()
    tracked = {
        line.strip()
        for line in subprocess.run(  # noqa: S603 - resolved git path, fixed arguments
            [git_executable(), "ls-files"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        if line.strip()
    }

    if ".env" in tracked:
        failures.append(".env must never be tracked")

    configured_prefix = os.getenv("COGNEE_KEY_PREFIX", "").strip()
    for path in files:
        name = relative(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        if name != ".env.example" and NONEMPTY_KEY_ASSIGNMENT.search(text):
            failures.append(f"{name}: contains a non-empty COGNEE_API_KEY assignment")
        if COGNEE_KEY_PATTERN.search(text):
            failures.append(f"{name}: contains a Cognee-shaped key value")
        if configured_prefix and configured_prefix in text:
            failures.append(f"{name}: contains the configured Cognee key prefix")
        if FORGET_EVERYTHING.search(text) and not is_test(path):
            failures.append(f"{name}: account-wide forget is forbidden")
        if (
            name.startswith("backend/src/")
            and name != "backend/src/recallops/memory/cognee_cloud.py"
            and DIRECT_COGNEE_IMPORT.search(text)
        ):
            failures.append(f"{name}: imports Cognee outside the cloud adapter")
        for dataset in DATASET_PATTERN.findall(text):
            if dataset != EXPECTED_DATASET:
                failures.append(f"{name}: unexpected dataset constant {dataset}")

    integration_dir = ROOT / "backend" / "tests" / "integration"
    for path in integration_dir.glob("*live*.py"):
        text = path.read_text(encoding="utf-8")
        if (
            "RUN_COGNEE_INTEGRATION" not in text
            or "pytestmark" not in text
            or "skip" not in text
        ):
            failures.append(
                f"{relative(path)}: live test lacks an explicit opt-in skip gate",
            )

    router = (ROOT / "frontend" / "src" / "router.tsx").read_text(
        encoding="utf-8",
    )
    if 'path: "/app"' not in router:
        failures.append("frontend router does not preserve the /app boundary")

    return sorted(set(failures))


def main() -> int:
    failures = run_checks()
    if failures:
        print("RecallOps preflight failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("RecallOps preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
