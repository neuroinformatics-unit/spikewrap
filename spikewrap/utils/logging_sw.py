from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Literal, Union

from spikewrap.utils import utils


class HandleLogging:
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

    Note that within spikewrap, the main entry methods `run_full_pipeline`,
    `run_sorting` and `run_postprocessing` are exposed. We want to
    log when these are run, but as `run_full_pipeline` calls the other two
    methods, we do not want to duplicate logging. Here, logging only starts
    if the named loggers do not have handlers. This is important because
    the `logs` instantiation of this class at the level of the `run_sorting`
    or `run_postprocessing` sub-functions will not be doing anything.
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
        """
        Check that we are logging by checking if any of the named
        loggers have handlers. As these handlers are removed
        when logging is stopped in this class, this is a valid check.

        Returns

        all_on : bool
            `True` if the loggers are on and `False` if the loggers are off.
            A check is performed to ensure all loggers are either off or on,
            ensuring this is not `False` by some unexpected intermediate
            state where some loggers but not all are on.
        """
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

        return all_on


class StreamToLogger(object):
    """
    A stream object that redirects writes to two logger
    instances, one to file and another back to stdout and stderr.
    The expected use of this class is to override stdout / stderr
    to print it to file and feed it back to stdout / stderr.
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
    run_name: Literal["full_pipeline", "sorting", "postprocess", "preprocessing"],
) -> HandleLogging:
    """
    Convenience function that creates logger name and stars a
    HandleLogging() instance. Note that this may be called
    even when the logging does not log, see HandleLogging()
    docs for details.
    """
    format_datetime = utils.get_formatted_datetime()
    log_name = f"{format_datetime}_{run_name}.log"

    logs = HandleLogging()
    logs.start_logging(log_filepath / log_name)

    return logs
