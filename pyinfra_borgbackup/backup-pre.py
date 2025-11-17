#!/usr/bin/env python3

import argparse
import os


def cmd(command: str) -> int:
    """Run a command and return its exit code. """
    return os.waitstatus_to_exitcode(os.system(command))


services = {
    "isolationbot": "isolationbot.service",
    "root": "docker.service",
}

parser = argparse.ArgumentParser()
parser.add_argument(
    "command",
    type=str,
    default="start",
    help="Whether to 'stop' or 'start' the services",
)
args = parser.parse_args()

for user in services:
    if user == "root":
        returncode = cmd(f"systemctl {args.command} {services[user]}")
    else:
        returncode = cmd(
            f"su -l {user} -c 'systemctl --user {args.command} {services[user]}'"
        )
    if returncode != 0:
        print(f"WARNING: Failed to {args.command} {services[user]} as {user} user")
