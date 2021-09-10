"""
A central command line option to use for all tools
"""

import pprint
import sys
from textwrap import dedent

import configargparse

from .core import manager
from .version import __version__

MANAGER = manager.AstManager()


def add_general_option(parser):
    parser.add_argument("--version", help="Print program version and exit", action="version", version=__version__)
    parser.add_argument("-c", "--config-file", is_config_file=True, help="config file path")
    parser.add_argument(
        "--display-mem-usage", help="display detailed memory usage on every operation.", action="store_true"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help=dedent(
            """\
            specify the verbosity level
            0 - print the full traceback
            1 - print the memory usage and time lapse
    """
        ),
        action="count",
        default=0,
    )
    parser.add_argument(
        "--statistics",
        type=configargparse.FileType("w"),
        help="Dump the inference and other statistics to the file specified.",
    )


def add_analysis_related_group(parser):
    parser.add_argument(
        "-py",
        "--python-version",
        help="specify the python version of the analyse code",
        choices=[2, 3],
        type=int,
        dest="py_version",
        default=3,
    )

    parser.add_argument(
        "--no-analyze-procedure",
        help="recursively analyze all procedure even without calling",
        dest="no_analyze_procedure",
        default=False,
        action="store_true",
    )

    parser.add_argument(
        "--type-inference",
        help="infer the type based on type annotation. Support binop and comparison.",
        dest="type_inference",
        action="store_true",
    )

    parser.add_argument(
        "--limit-inference",
        help="specify the maximum inference recursion value. Default is unlimited",
        dest="max_inference_value",
        metavar="<NUMBER>",
        type=int,
    )

    parser.add_argument(
        "--infer-extension",
        help="specify the external custom inference module to load.",
        dest="infer_extension_files",
        nargs="*",
        type=configargparse.FileType("r"),
        default=[],
        metavar="<EXTENSION PY FILE>",
    )

    parser.add_argument(
        "--typeshed-select",
        help="""
            specify which python builtin module to enable type inference, default to ALL.
            Use --typeshed-select ALL to select all typeshed modules.
        """.strip(),
        dest="typeshed_select",
        nargs="*",
        type=str,
        default=[],
        metavar="<PYTHON MODULE>",
    )

    parser.add_argument(
        "--stubs",
        help="""
            specify additional stub file for better type inference. Stub file follow pep-484 format, \
            and must have ".pyi" extension and named based on the module to stub. \
            E.g. math.pyi is type stubs for math module.
        """.strip(),
        dest="stubs",
        nargs="*",
        type=configargparse.FileType("r"),
        default=[],
        metavar="<.pyi STUBS>",
    )

    parser.add_argument(
        "--enable-infer-sequence",
        help="infer all possible values in sequence e.g. list, set, this will increase inference time.",
        action="store_true",
    )

    parser.add_argument("--html-server", help="enable html server for graphical inference support", action="store_true")
    parser.add_argument("--html-server-port", help="port for html server", type=int, default=5000)


def print_info(args, output_stream=sys.stdout):
    pp = pprint.PrettyPrinter(indent=4, stream=output_stream)
    output_stream.write("loaded extension: {}\n\n".format(MANAGER.loaded_extension))
    output_stream.write("using configuration value: \n{}\n\n".format(pp.pformat(vars(args))))
