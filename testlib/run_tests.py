#!/usr/bin/env python3

import argparse
import subprocess
import sys
import time
import signal
import os

from copy import deepcopy
from threading import Thread

class Command:
    RUN_ENDPOINT_TEST = ["docker", "exec", "-iu", "0", "api", "/usr/local/bin/nosetests", "--with-id", "-w", "/var/gator/api/testlib/endpoint/"]
    RUN_INTERNAL_TEST = ["docker", "exec", "-iu", "0", "api", "/usr/local/bin/nosetests", "--with-id", "-w", "/var/gator/api/testlib/internal/"]
    RUN_NOTIFIER_TEST = ["docker", "exec", "-iu", "0", "ntfy", "/usr/local/bin/nosetests", "--with-id", "-w", "/var/gator/api/testlib/notifier/"]

    def __init__(self):
        self.active_cmds = []

    def garbage_collect(f):
        def decorated(self, *args, **kwargs):
            cmd = f(self, *args, **kwargs)
            self.active_cmds.append(cmd)
            return cmd
        return decorated

    @garbage_collect
    def run_nb(self, command, stdout=sys.stdout, stderr=sys.stderr):
        return subprocess.Popen(command, stdout=stdout, stderr=stderr)

    @garbage_collect
    def run_shell_nb(self, command):
        return subprocess.Popen(" ".join(command))

    @garbage_collect
    def run_shell(self, command):
        return subprocess.call(" ".join(command), shell=True)

    # The following commands perform actions on all of the commands executed
    def reap(self):
        for process in self.active_cmds:
            if process.poll() is None:
                process.kill()

    def wait(self):
        for process in self.active_cmds:
            if process.poll() is None:
                process.wait()

        self.active_cmds = []

####################
# Global Variables #
####################

VALID_SUITES = ["endpoint", "internal", "notifier"]
TINY_TIMEOUT = 2
SHORT_TIMEOUT = 5
LONG_TIMEOUT  = 60 # NOTE : tests need to finish in less than this timeout

def setup_build_dir():
    global out, err

    build_dir_f = os.path.abspath("./build/")
    stdout_f = "%s/stdout.txt" % build_dir_f
    stderr_f = "%s/stderr.txt" % build_dir_f

    # Ensure that the state of the build dir is clean
    if not os.path.exists(build_dir_f):
        os.makedirs(build_dir_f)
    else:
        os.remove(stdout_f)
        os.remove(stderr_f)

    out = open(stdout_f, "w")
    err = open(stderr_f, "w")

# Used for container output
out, err = None, None
setup_build_dir()

command = Command()

def cleanup(timeout_time=SHORT_TIMEOUT):
    # Wait for the commands to finish and kill them if they don't
    wait_lambda = lambda: command.wait()
    thread = Thread(target=wait_lambda)
    thread.start()
    thread.join(timeout_time)

    # If all commands exited then return
    if len(command.active_cmds) == 0:
        return

    print ("¡¡¡REAPING ZOMBIES!!!")
    command.reap()

def sigint_handler(signal, frame):
    cleanup(timeout_time=TINY_TIMEOUT)
    exit(0)

def run_suites(suites, noseargs):
    actions = {
        "endpoint": (command.run_nb, [command.RUN_ENDPOINT_TEST + noseargs]),
        "internal": (command.run_nb, [command.RUN_INTERNAL_TEST + noseargs]),
        "notifier": (command.run_nb, [command.RUN_NOTIFIER_TEST + noseargs])
    }

    # Run all of the specified tests
    for ste in suites:
        if actions.get(ste) is not None:
            print("%s:" % ste.capitalize())
            process = actions[ste][0](*actions[ste][1])
            process.wait()
            print("\n")

    cleanup()


if __name__ == "__main__":
    # Register the sigint handler
    signal.signal(signal.SIGINT, sigint_handler)

    parser = argparse.ArgumentParser(
        description="Runs OrderAPI test suites")

    parser.add_argument("suite", metavar="suite", type=str, choices=VALID_SUITES + ["all"],
        help="The test suite to be run")
    parser.add_argument("noseargs", default="", nargs=argparse.REMAINDER,
        help="Any args to pass to nosetests")

    args = parser.parse_args()
    suites = VALID_SUITES if args.suite == "all" else [args.suite]

    run_suites(suites, args.noseargs)

    # Make sure that the output files have been closed
    out.close()
    err.close()
