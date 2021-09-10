"""
A central manager that storing configs, provide logging mechanism etc...
This is a base manager, which means that it should not import any module
to avoid cyclic dependencies. To add any capabilities to the manager,
create a new file to inherit the manager. The base manager is using
borg pattern, so class inheritance will also guarantee singleton
properties for all instances.
"""
import collections
import datetime
import linecache
import logging
import os
import sys
import tracemalloc
from textwrap import dedent


class Message:
    def __init__(self, fmt, *args):
        self.fmt = fmt
        self.args = args

    def __str__(self):
        try:
            return self.fmt.format(*self.args)
        except Exception:
            return self.fmt


class BaseManager:
    """
    Enable custom logging signature to differentiate the context, where the first arg is
    the operation name.
    E.g. To log a stuff about ssa,
    >>> manager = BaseManager()
    >>> manager.logger.info("ssa", "perform an operation related to ssa")
    """

    _core = {}
    _VERBOSITY_LEVEL = {0: logging.ERROR, 1: logging.INFO, 2: logging.DEBUG}
    _LOG_METHOD_REPR = ("info", "warning", "error", "critical", "exception", "debug")

    def __init__(self, config=None):
        self.__dict__ = BaseManager._core
        self._fresh_init(config)

    def initialize(self, config=None):
        """initialize the logging level and clear all the state"""
        self._fresh_init(config)
        sys.setrecursionlimit(1500)
        if hasattr(config, "verbose"):
            logging.basicConfig(
                level=self._VERBOSITY_LEVEL.get(config.verbose) or logging.WARNING,
                format="(%(levelname)s) - %(message)s",
            )

        if config.display_mem_usage:
            tracemalloc.start()
            for log_method_repr in self._LOG_METHOD_REPR:
                getattr(self.logger, log_method_repr).display_mem = config.display_mem_usage

    def _fresh_init(self, config=None):
        # To indicate the manager has been initialized.
        # This wouldn't be needed in the typical borg pattern but
        # in this case there is inheritance and different
        # initializing points.
        if not self.__dict__ or not hasattr(self, "_manager_status") or not self._manager_status:
            self._manager_status = True
            self.config = config
            self.builtins_ast_cls = {}
            self.builtins_tree = None
            self.logger = FlowMsgAdapter(logging.getLogger("PYSCA"), {})
            for log_method_repr in self._LOG_METHOD_REPR:
                log_method = getattr(self.logger, log_method_repr)
                setattr(self.logger, log_method_repr, CustomLogger(log_method))
            self.logger.debug("INITIALIZE", "First initialization of manager object")
            # cache for inferring to save time.
            self.infer_cache = {}
            self.infer_count = 0
            self.skipped_infer_count = 0
            self.skipped_same_operand_count = 0
            self.skipped_same_operand_nested_count = 0
            self.skipped_z3_operand = 0

    def get_infer_statistics(self):
        return dedent(
            """ \
                Total number of infer: {},
                skipped infer: {},
                skipped operand: {}
                skipped operand nested: {}
                skipped z3 expr: {}
            """
        ).format(
            self.infer_count,
            self.skipped_infer_count,
            self.skipped_same_operand_count,
            self.skipped_same_operand_nested_count,
            self.skipped_z3_operand,
        )

    def uninitialize(self):
        self.clear_infer_cache()

    def clear_infer_cache(self):
        self.infer_cache = {}

    def reset(self):
        BaseManager.core = {}
        self._fresh_init()
        tracemalloc.stop()
        for log_method_repr in self._LOG_METHOD_REPR:
            getattr(self.logger, log_method_repr).display_mem = False


class FlowMsgAdapter(logging.LoggerAdapter):
    def log(self, level, flow, msg, *args, **kwargs):
        if self.isEnabledFor(level):
            msg, kwargs = self.process(msg, kwargs)
            msg = ("[{}] " if flow else "{}") + msg
            self.logger._log(level, Message(msg, flow, *args), (), **kwargs)


def display_top(statistics_diff, limit=3):
    print("Top %s lines" % limit)
    for index, stat in enumerate(statistics_diff[:limit], 1):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        print("#%s: %s:%s: %.1f Mb" % (index, filename, frame.lineno, stat.size / 1024 / 1024))
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print("    %s" % line)

    other = statistics_diff[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("%s other: %.1f Mb" % (len(other), size / 1024 / 1024))
    total = sum(stat.size for stat in statistics_diff)
    print("Total allocated size: %.1f Mb" % (total / 1024 / 1024))


class CustomLogger:
    """Custom logger that allow logging time taken
    >>> c = CustomLogger(logging.info)
    >>> c("COV", "Running cov")
    [COV] Running cov...
    >>> with c("COV", "Running cov..."):
    ...     list(range(10000))
    [COV] Running cov...
    [COV] Running cov took 00:00:01.231
    """

    def __init__(self, ori_log_method, display_mem=False):
        self.ori_log_method = ori_log_method
        self.initial_time = None
        self.final_time = None
        self.msg = ""
        self.stacked_msg = collections.deque()
        self.mem_statistics = collections.deque()
        self.display_mem = display_mem
        self.display_mem_individual = False

    def __call__(self, operation="", msg="", *args, display_mem=False, **kwargs):
        self.display_mem_individual = display_mem
        msg = dedent(msg)
        if not operation:
            self.msg = msg
            self.ori_log_method(msg, *args, **kwargs)
            return self
        self.msg = msg
        self.ori_log_method(operation, msg, *args, **kwargs)
        return self

    def __enter__(self):
        if self.display_mem or self.display_mem_individual:
            self.mem_statistics.append(tracemalloc.take_snapshot())
        self.initial_time = datetime.datetime.now()
        self.stacked_msg.append(self.msg)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.display_mem or self.display_mem_individual:
            self.display_mem_individual = False
            snap_shot = tracemalloc.take_snapshot()
            statistics = snap_shot.compare_to(self.mem_statistics.pop(), "lineno")
            display_top(statistics)
        self.final_time = datetime.datetime.now()
        duration = self.final_time - self.initial_time
        msg = self.stacked_msg.pop()
        self.ori_log_method("", msg + " took {}", str(duration))
