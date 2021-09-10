import json
import pathlib
import sys

import configargparse

from klara import cli
from klara.klara_z3 import cov_manager, inference_extension
from klara.scripts.cover_gen_ins import line_fix_solver, solver
from klara.scripts.cover_gen_ins.config import ConfigNamespace

MANAGER = cov_manager.CovManager()


def _add_require_group(parser):
    parser.add_argument(
        "file_name",
        nargs="*",
        help="specify the filename or directory. For directory, will auto determine file based on extension",
    )
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--cover-return",
        action="store_true",
        help="Return coverage. Cover all possible return value. Will require more run time. " "Enabled by default.",
    )
    group.add_argument("--cover-lines", type=int, nargs="*", help="specify the line numbers to cover")
    group.add_argument("--cover-all", action="store_true", help="Line covearge. Cover all the lines")


def _add_optional_group(parser):
    parser.add_argument("--entry-class", type=str, help="The class to analyze", default="")
    parser.add_argument("--entry-func", type=str, help="The top function to analyze in `--entry-class`", default="Top")
    parser.add_argument(
        "-o",
        type=configargparse.FileType("w"),
        help="output json file containing analysis result. If not specified, result will dump in stdout",
        default=None,
        dest="output_file",
    )
    parser.add_argument(
        "--output-statistics",
        type=configargparse.FileType("w"),
        help="dump conditions statistics gathered and used to solve z3 in json",
        default=None,
        dest="output_statistics",
    )


def _add_z3_options(parser):
    parser.add_argument(
        "--z3-parallel", action="store_true", default=False, help="solving conditions with z3 using multi threading"
    )
    parser.add_argument(
        "--z3-parallel-max-threads", type=int, default=None, help="max threads used in z3 parallel solving."
    )
    parser.add_argument(
        "--mss-algorithm",
        choices=["z3", "legacy"],
        default="marco",
        help="Use legacy mss algorithm using z3 optimization. Default is marco, which perform the best.",
    )


def parse_args(args, namespace=None):
    cur_path = pathlib.Path(__file__)
    fcf_path = cur_path.parent / "default_config.ini"
    parser = configargparse.ArgParser(
        default_config_files=[str(fcf_path)],
        description="Analyse and auto suggesting test suite.",
        add_config_file_help=False,
        add_env_var_help=False,
    )
    cli.add_general_option(parser.add_argument_group("General option"))
    _add_require_group(parser)
    _add_optional_group(parser)
    _add_z3_options(parser.add_argument_group("Z3", description="Z3-SMT solver related options"))
    cli.add_analysis_related_group(parser.add_argument_group("Analysis related option"))
    parser.parse_args(args, namespace=namespace)


def run(args):
    cli.print_info(args)
    for fn in args.file_name:
        file_path = pathlib.Path(fn)
        text = file_path.read_text()
        file_path_text = file_path.resolve().as_uri()
        MANAGER.logger.info("COV", "analyzing file: {}\n", file_path_text)
        output_stream = args.output_file or sys.stdout
        if not any((args.cover_return, args.cover_lines, args.cover_all)):
            MANAGER.logger.info("COV", "No coverage strategy is selected. Using cover_return by default")
            result = solver.solve(text, args)
        else:
            if args.cover_return:
                result = solver.solve(text, args)
            elif args.cover_lines or args.cover_all:
                result = line_fix_solver.solve(text, args)
            else:
                MANAGER.logger.warning("COV", "No coverage strategy is selected!")
                return
        json.dump(result, output_stream, indent=4)
        print("Needed {} amount of instances".format(len(result)))
    MANAGER.logger.info("COV", MANAGER.get_infer_statistics())


def main():
    c = ConfigNamespace()
    parse_args(sys.argv[1:], namespace=c)
    MANAGER.initialize(c)
    inference_extension.enable()
    run(c)


if __name__ == "__main__":
    main()
