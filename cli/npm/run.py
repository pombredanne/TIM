import platform
import subprocess
from pathlib import Path
from typing import List, Optional

from cli.docker.run import run_compose
from cli.util.errors import CLIError
from cli.util.logging import log_debug
from cli.util.proc import run_cmd

MAX_NPM_MAJOR_VERSION = 6

_npm_ok = False
_npm_version_ok = False


def reset_npm_version() -> None:
    global _npm_version_ok
    global _npm_ok
    _npm_version_ok = False
    _npm_ok = False


def verify_npm(assert_version: bool = True) -> bool:
    global _npm_ok
    global _npm_version_ok
    if _npm_ok:
        return _npm_version_ok
    try:
        res = run_cmd(
            ["npm", "--version"],
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )
        version = res.stdout.strip()
        version_parts = [int(x) for x in version.split(".")]
        _npm_version_ok = version_parts[0] <= MAX_NPM_MAJOR_VERSION
        if not _npm_version_ok and assert_version:
            raise CLIError(
                f"TIM requires NPM version {MAX_NPM_MAJOR_VERSION}.x to run locally. "
                f"Run `npm i -g npm@{MAX_NPM_MAJOR_VERSION}` to install it."
            )
        _npm_ok = True
        return _npm_version_ok
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise CLIError(
            "npm not found; see https://docs.npmjs.com/getting-started/installing-node/ to install it"
        )


def run_npm(
    args: List[str],
    workdir: str,
    run_in_container: Optional[bool] = None,
) -> None:
    if run_in_container is None:
        log_debug(f"OS identifier: {platform.system()}")
        run_in_container = platform.system() != "Windows"
    log_debug(f"Running npm with args: {args}; running in docker: {run_in_container}")
    if not run_in_container:
        verify_npm()
        run_cmd(
            ["npm", *args],
            shell=True,
            cwd=(Path.cwd() / workdir).as_posix(),
        )
    else:
        run_compose(
            [
                "run",
                "--rm",
                "--no-deps",
                "--workdir",
                f"/service/{workdir}",
                "tim",
                "npm",
                *args,
            ]
        )
