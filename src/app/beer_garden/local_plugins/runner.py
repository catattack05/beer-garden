# -*- coding: utf-8 -*-
from io import TextIOBase

import logging
import os
import signal
import subprocess
from pathlib import Path
from threading import Thread
from typing import Dict, Sequence

log_levels = [n for n in getattr(logging, "_nameToLevel").keys()]


def read_stream(process: subprocess.Popen, stream: TextIOBase, logger: logging.Logger):
    """Helper function thread target to read a subprocess IO stream

    This will read line by line from STDOUT or STDERR and log each line at INFO level.
    Loggers passed to this function should have handlers configured to log at that level
    (or propagate to a logger than can), otherwise this function is pointless.
    """
    stream_reader = iter(stream.readline, "")

    # Sometimes the iter can finish before the process is really done
    while process.poll() is None:
        for raw_line in stream_reader:
            logger.info(raw_line.rstrip())


class StreamReader:
    """Context manager responsible for managing stream reading threads"""

    def __init__(self, runner):
        self.runner = runner
        self.process = runner.process
        self.process_cwd = runner.process_cwd
        self.capture_streams = runner.capture_streams

        self.stdout_thread = None
        self.stderr_thread = None

    def __enter__(self):
        if not self.capture_streams:
            return

        format_str = "%(asctime)s %(name)s: %(message)s"

        stdout_handler = logging.FileHandler(self.process_cwd / "plugin.stdout")
        stdout_handler.setFormatter(logging.Formatter(fmt=format_str))

        stderr_handler = logging.FileHandler(self.process_cwd / "plugin.stderr")
        stderr_handler.setFormatter(logging.Formatter(fmt=format_str))

        stdout_logger = logging.getLogger(f"{self.runner.runner_id}.stdout")
        stdout_logger.addHandler(stdout_handler)
        stdout_logger.propagate = False
        stdout_logger.setLevel("DEBUG")

        stderr_logger = logging.getLogger(f"{self.runner.runner_id}.stderr")
        stderr_logger.addHandler(stderr_handler)
        stderr_logger.propagate = False
        stderr_logger.setLevel("DEBUG")

        self.stdout_thread = Thread(
            target=read_stream,
            args=(self.process, self.process.stdout, stdout_logger),
            name=f"{self.runner} STDOUT Reader",
        )
        self.stderr_thread = Thread(
            target=read_stream,
            args=(self.process, self.process.stderr, stderr_logger),
            name=f"{self.runner} STDERR Reader",
        )

        self.stdout_thread.start()
        self.stderr_thread.start()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.stdout_thread and self.stdout_thread.is_alive():
            self.stdout_thread.join()
        if self.stderr_thread and self.stderr_thread.is_alive():
            self.stderr_thread.join()


class ProcessRunner(Thread):
    """Thread that runs a Plugin process

    A runner will take care of creating and starting a process that will run the plugin
    entry point.

    Logging here is a little interesting. We expect that plugins will be created as the
    first order of business in the plugin's ``main()``. Part of the Plugin initialize
    is asking beer-garden for a logging configuration, so anything after that point will
    be handled according to the returned configuration.

    However, there are two potential problems: the plugin may have logging calls before
    initializing the Plugin (even though it's not recommended), and the Plugin may fail
    to register at all for whatever reason.

    This can be problematic depending on the way the Beer-garden application is run.
    When running as a systemd service it's difficult to find the output for individual
    plugin processes, which can make troubleshooting frustrating.

    To make things less annoying the beer.conf file supports a CAPTURE_STREAMS flag. If
    this is set to True the STDOUT and STDERR for the plugin process will be captured
    and logged to files plugin.out and plugin.err, respectively. These files will be
    located in the same directory as the plugin.

    The log statements will have the runner ID as part of the logger name. This is to
    distinguish between output generated by the different processes that are created
    when more than once instance of a plugin is run. Unfortunately, the instance name
    itself can't be used here because it's not guaranteed to be accurate.

    """

    def __init__(
        self,
        runner_id: str,
        process_args: Sequence[str],
        process_cwd: Path,
        process_env: dict,
        capture_streams: bool,
    ):
        self.process = None
        self.restart = False
        self.stopped = False
        self.dead = False

        self.runner_id = runner_id
        self.instance_id = ""

        self.process_args = process_args
        self.process_cwd = process_cwd
        self.process_env = process_env
        self.runner_name = process_cwd.name
        self.capture_streams = capture_streams

        self.logger = logging.getLogger(f"{__name__}.{self}")

        Thread.__init__(self, name=self.runner_name)

    def __str__(self):
        return f"{self.runner_name}.{self.runner_id}"

    def state(self) -> Dict:
        """Pickleable representation"""

        return {
            "runner_name": self.runner_name,
            "runner_id": self.runner_id,
            "instance_id": self.instance_id,
            "restart": self.restart,
            "stopped": self.stopped,
            "dead": self.dead,
        }

    def associate(self, instance=None):
        """Associate this runner with a specific instance ID"""
        self.instance_id = instance.id

    def terminate(self):
        """Kill the underlying plugin process with SIGTERM"""
        if self.process and self.process.poll() is None:
            self.logger.debug("About to send SIGINT")
            os.kill(self.process.pid(), signal.SIGINT)

    def kill(self):
        """Kill the underlying plugin process with SIGKILL"""
        if self.process and self.process.poll() is None:
            self.logger.warning("About to send SIGKILL")
            self.process.kill()

    def run(self):
        """Runs the plugin process

        Run the plugin using the entry point specified with the generated environment in
        its own subprocess.
        """
        self.logger.debug(f"Starting process with args {self.process_args}")

        try:
            self.process = subprocess.Popen(
                args=self.process_args,
                env=self.process_env,
                cwd=str(self.process_cwd.resolve()),
                restore_signals=False,
                close_fds=True,
                text=True,
                stdout=subprocess.PIPE if self.capture_streams else None,
                stderr=subprocess.PIPE if self.capture_streams else None,
            )

            with StreamReader(self):
                self.process.wait()

            if not self.instance_id:
                self.logger.warning(
                    f"Plugin {self} terminated before successfully initializing."
                )

            self.logger.debug("Plugin is officially stopped")

        except Exception as ex:
            self.logger.exception(f"Plugin {self} died: {ex}")
