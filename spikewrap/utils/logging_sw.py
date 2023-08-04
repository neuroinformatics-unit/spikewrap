from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal, Union


class HandleLogging:  # TODO: better explain when this is on / off
    """
    Handle logging for SpikeWrap. The aim of spike wrap logging is
    to agnostically log everything printed by stdout and stderr
    to a log file. Because we do not have control over logging
    in SpikeInterface, we can re-pipe all stdout and stderr
    messages to loggers with the appropriate output streams.

    Both stdout and stderr are always piped to a logger that
    outputs to file (`self.logger_file`). Additionally,
    stdout is re-piped back to stdout with another logger (`self.logger_stdout`)
    while stderr is piped back to stderr (`self.logger_stderr`).

    This ensures that all stdout and stderr messages are logged to file
    without interfering with the normal message printing.
    """

    def __init__(self):
        self.bkup_stdout = None
        self.bkup_stderr = None
        self.logger_file = None
        self.logger_stdout = None
        self.logger_stderr = None
        self.this_instance_is_logging = False

    def start_logging(self, log_filepath: Union[Path, str]):
        """
        Here the three loggers that pipe to file, stdout and
        stderr are defined. Then, sys.stdout is overridden to
        pipe to the file logger and the stdout logger. sys.stderr
        is overridden to pipe to the file logger and the stderr logger.

        stdout and stderr and stored so they can be re-set in
        `stop_logging()`.

        Parameters
        ----------
        log_filepath : Path
            Path the output logs will be saved to.
        """
        if not self.are_already_logging():
            self.this_instance_is_logging = True

            if not Path(log_filepath).parent.is_dir():
                Path(log_filepath).parent.mkdir(parents=True, exist_ok=True)

            if isinstance(log_filepath, Path):
                log_filepath = log_filepath.as_posix()

            # File logger
            self.logger_file = logging.getLogger("spikewrap_file")

            self.logger_file.addHandler(logging.FileHandler(log_filepath, "a"))

            # Stdout logger
            self.logger_stdout = logging.getLogger("spikewrap_stdout")
            stdout_handler = logging.StreamHandler(sys.stdout)
            self.logger_stdout.addHandler(stdout_handler)

            # Stderr Logger
            self.logger_stderr = logging.getLogger("spikewrap_stderr")
            stderr_handler = logging.StreamHandler(sys.stderr)
            self.logger_stderr.addHandler(stderr_handler)

            # Override system stdout / stderr
            self.bkup_stdout = sys.stdout
            self.bkup_stderr = sys.stderr

            sys.stdout = StreamToLogger(  # type: ignore
                self.logger_file, self.logger_stdout, logging.ERROR
            )
            sys.stderr = StreamToLogger(  # type: ignore
                self.logger_file, self.logger_stderr, logging.ERROR
            )

    def stop_logging(self):
        """
        Stop the existing loggers by removing their stream (i.e. output
        handlers). Set system stdout and stderr to their original classes
        so the logger receives no information.

        Note that the removal of the log handlers is critial as this is what is
        used to check that we are not already logging, which is important
        to ensure we do not log multiple times when functions call eachother.
        For example `run_full_pipeline` and `run_sorting` can both log, but
        we do not want `run_sorting` to start logging if it is called from
        `run_full_pipeline`.
        """
        if self.this_instance_is_logging:
            for logger in [self.logger_file, self.logger_stdout, self.logger_stderr]:
                handlers = logger.handlers[:]
                for handler in handlers:
                    logger.removeHandler(handler)
                    handler.close()

            sys.stdout = self.bkup_stdout
            sys.stderr = self.bkup_stderr

    def are_already_logging(self):
        """ """
        loggers = [
            logging.getLogger("spikewrap_file"),
            logging.getLogger("spikewrap_stdout"),
            logging.getLogger("spikewrap_stderr"),
        ]

        active_loggers = [logger.hasHandlers() for logger in loggers]

        all_on = all(active_loggers)
        all_off = not any(active_loggers)

        assert (
            all_on or all_off
        ), "Some loggers are switched on while others are off. This should not happen."

        if all_on:
            return True
        return False


class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """

    def __init__(self, logger_file, logger_std, level):
        self.logger_file = logger_file
        self.logger_std = logger_std
        self.level = level
        self.linebuf = ""

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger_file.log(self.level, line.rstrip())
            self.logger_std.log(self.level, line.rstrip())

    def flush(self):
        pass


def get_started_logger(
    log_filepath: Path,
    run_name: Literal["full_pipeline", "preprocess", "sorting", "postprocess"],
) -> HandleLogging:
    """
    Convenience function
    """
    format_datetime = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_name = f"{format_datetime}_{run_name}.log"

    logs = HandleLogging()
    logs.start_logging(log_filepath / log_name)
    return logs
