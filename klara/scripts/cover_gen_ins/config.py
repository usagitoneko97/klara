from klara.core.config import Config


class ConfigNamespace(Config):
    """Config for cov analysis"""

    file_name: list = []
    # disable inferring cache. Usually used in test.
    force_infer = False
    # the class to analyze
    entry_class: str = ""
    # entry function of the specified class of `entry_class`
    entry_func: str = "Top"
    # the output file object for storing json result
    output_file = None
    z3_parallel = False
    z3_parallel_max_threads = None
    # file that contain dump of conditions gathered and used to solve z3
    output_statistics = None
    mss_algorithm = "z3"
    cover_lines = []
    cover_all = False
    cover_return = False
