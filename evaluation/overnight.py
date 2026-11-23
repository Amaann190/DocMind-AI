"""Resumable overnight driver for the research experiments.

Runs the jobs in ``evaluation/overnight_jobs.json`` one after another. A job whose output file
already exists is skipped, so the driver can be restarted at any time. Before every job Ollama is
health-checked (and restarted with ``ollama serve`` when it is down) and the job's models are
checked; a failed job is logged and the driver moves on. Windows is kept awake (system and
display) while it runs. Events go to ``<out>/overnight.log``; each job's full console output goes
to ``<out>/overnight-logs/<job>.log``.

  python -m evaluation.overnight               # run everything that is not done yet
  python -m evaluation.overnight --dry-run     # list what would run
  python -m evaluation.overnight --only answers-qwen2.5-3b
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
JOBS_FILE = Path(__file__).with_name("overnight_jobs.json")
DEFAULT_OUT = REPO / "output" / "research"
ENDPOINT = "http://localhost:11434"
ES_CONTINUOUS, ES_SYSTEM_REQUIRED, ES_DISPLAY_REQUIRED = 0x80000000, 0x00000001, 0x00000002
DEFAULT_TIMEOUT_MINUTES = 360


# ---------------------------------------------------------------- pure logic

def load_jobs(path=JOBS_FILE):
    jobs = json.loads(Path(path).read_text(encoding="utf-8"))["jobs"]
    names = [job["name"] for job in jobs]
    if len(set(names)) != len(names):
        raise ValueError("job names must be unique")
    for job in jobs:
        if not job.get("args") or not job.get("output"):
            raise ValueError(f"job {job.get('name')!r} needs args and output")
    return jobs


def is_done(job, out_dir):
    return (Path(out_dir) / job["output"]).exists()


def pending_jobs(jobs, out_dir, only=None):
    """(to_run, skipped): jobs whose output file is missing, and those already done."""
    chosen = [job for job in jobs if not only or any(token in job["name"] for token in only)]
    return ([job for job in chosen if not is_done(job, out_dir)], [job for job in chosen if is_done(job, out_dir)])


def command_for(job, python=None):
    return [python or sys.executable, "-m", "evaluation.research", *job["args"], "--out", "{out}"]


# ---------------------------------------------------------------- environment

def ollama_up(endpoint=ENDPOINT):
    try:
        with urllib.request.urlopen(endpoint + "/api/version", timeout=5):  # noqa: S310 - local Ollama
            return True
    except OSError:
        return False


def installed_models(endpoint=ENDPOINT):
    try:
        with urllib.request.urlopen(endpoint + "/api/tags", timeout=10) as response:  # noqa: S310 - local Ollama
            return {m["name"] for m in json.load(response)["models"]}
    except (OSError, ValueError, KeyError):
        return set()


def missing_models(job, installed):
    """Models a job needs that Ollama does not have (a bare name matches its ``:latest`` tag)."""
    have = installed | {name.removesuffix(":latest") for name in installed}
    return [m for m in job.get("requires", []) if m not in have and f"{m}:latest" not in have]


def start_ollama(wait_seconds=90):
    """Start ``ollama serve`` detached and wait until it answers; True on success."""
    exe = shutil.which("ollama") or str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe")
    flags = (getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)) if os.name == "nt" else 0
    try:
        subprocess.Popen([exe, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)  # noqa: S603
    except OSError:
        return False
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if ollama_up():
            return True
        time.sleep(2)
    return False


def keep_awake(on):
    """Hold (or release) SetThreadExecutionState(system + display required) on this thread."""
    if os.name != "nt":
        return
    import ctypes
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED if on else ES_CONTINUOUS)


def execute_job(job, out_dir, timeout_minutes=None):
    """Run one job as a subprocess; returns (exit_code, log_path). Exit code None means timeout."""
    log_dir = Path(out_dir) / "overnight-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{job['name']}.log"
    command = [part.replace("{out}", str(out_dir)) for part in command_for(job)]
    with log_path.open("w", encoding="utf-8", errors="replace") as handle:
        try:
            result = subprocess.run(command, cwd=REPO, stdout=handle, stderr=subprocess.STDOUT, text=True,  # noqa: S603
                                    timeout=60 * (job.get("timeout_minutes") or timeout_minutes or DEFAULT_TIMEOUT_MINUTES),
                                    env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        except subprocess.TimeoutExpired:
            return None, log_path
    return result.returncode, log_path


def tail(path, lines=6):
    """Last few meaningful lines of a job log, joined for the one-line log entry."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return " | ".join([line.strip() for line in text if line.strip() and "HTTP Request" not in line][-lines:])[-600:]


# ---------------------------------------------------------------- driver

def run(jobs, out_dir, *, only=None, health=ollama_up, restart=start_ollama, models=installed_models,
        execute=execute_job, log=None, now=time.time):
    """Run pending jobs in order; return {"done": [...], "skipped": [...], "failed": [...]}.

    Every collaborator is injectable so the control flow is testable without Ollama or subprocesses.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_file = out_dir / "overnight.log"

    def write(message):
        line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}"
        print(line, flush=True)
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    log = log or write
    to_run, skipped = pending_jobs(jobs, out_dir, only)
    outcome = {"done": [], "skipped": [job["name"] for job in skipped], "failed": []}
    for job in skipped:
        log(f"SKIP  {job['name']} (output exists: {job['output']})")
    for number, job in enumerate(to_run, 1):
        name = job["name"]
        try:
            if not health():
                log(f"WARN  Ollama is not responding before {name}; restarting it")
                if not restart():
                    raise RuntimeError("Ollama did not come back after restart")
                log("INFO  Ollama restarted")
            missing = missing_models(job, models())
            if missing:
                raise RuntimeError(f"models not installed: {', '.join(missing)}")
            log(f"START {name} [{number}/{len(to_run)}] {' '.join(job['args'])}")
            began = now()
            code, log_path = execute(job, out_dir)
            minutes = (now() - began) / 60
            if code is None:
                raise RuntimeError(f"timed out after {minutes:.0f} min; see {log_path}")
            if code != 0 or not is_done(job, out_dir):
                raise RuntimeError(f"exit {code}, output {'present' if is_done(job, out_dir) else 'missing'}: {tail(log_path)}")
            log(f"END   {name} ok in {minutes:.1f} min -> {job['output']}")
            outcome["done"].append(name)
        except Exception as error:  # noqa: BLE001 - one failed job must not stop the night
            log(f"ERROR {name}: {error}")
            outcome["failed"].append(name)
    log(f"DONE  {len(outcome['done'])} ran, {len(outcome['skipped'])} skipped, {len(outcome['failed'])} failed"
        + (f": {', '.join(outcome['failed'])}" if outcome["failed"] else ""))
    return outcome


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--jobs", default=str(JOBS_FILE))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--only", nargs="*", help="Run only jobs whose name contains one of these strings")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    jobs = load_jobs(args.jobs)
    if args.dry_run:
        to_run, skipped = pending_jobs(jobs, args.out, args.only)
        for job in skipped:
            print(f"skip  {job['name']}")
        for job in to_run:
            print(f"run   {job['name']}: {' '.join(job['args'])}")
        return 0
    keep_awake(True)
    try:
        outcome = run(jobs, args.out, only=args.only)
    finally:
        keep_awake(False)
    return 1 if outcome["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
