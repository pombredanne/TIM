import os
import os.path
import subprocess
from argparse import ArgumentParser
from typing import List

info = {
    "help": "Run a docker-compose command on TIM containers",
    "description": """
Run a docker-compose command on TIM containers.
This is a wrapper around docker-compose commands that takes into account extra TIM environment variables.
""",
}


class Arguments:
    profile: str
    args: List[str]


def cmd(args: Arguments) -> None:
    cwd = os.getcwd()
    env = os.environ.copy()
    extra_args = ["-f", os.path.join(cwd, "docker-compose.yml")]
    if args.profile == "test":
        env["CSPLUGIN_TARGET"] = "base"
        extra_args.extend(["--profile", "test"])
    elif args.profile == "dev":
        env["CSPLUGIN_TARGET"] = "sudo"
        extra_args.extend(["-f", os.path.join(cwd, "docker-compose.dev.yml")])

    subprocess.run(["docker-compose", *extra_args, *args.args], env=env)


def init(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--profile",
        help="TIM run profile override. Default is the same as defined in timconfig.py",
        choices=["dev", "prod", "test"],
    )
    parser.add_argument("args", nargs="*", help="Arguments to pass to docker-compose")
    parser.set_defaults(func=cmd)
