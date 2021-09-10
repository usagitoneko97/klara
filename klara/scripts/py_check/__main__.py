import pathlib
import sys
import time

import configargparse

from klara import cli
from klara.core import cfg, manager, utilities
from . import fcf_solver, loop_solver
from .config import ConfigNamespace

MANAGER = manager.AstManager()
CHECKER_SELECT = {"fcf": fcf_solver, "loop": loop_solver}


def _add_require_group(parser):
    parser.add_argument(
        "file_name",
        nargs="*",
        help="specify the filename or directory. For directory, will auto determine file based on extension",
    )
    parser.add_argument(
        "--checks",
        type=str,
        nargs="*",
        help="specify the check to carry out. ALL for all the check. By default all checks will be carried out",
        choices=["fcf", "loop", "ALL"],
        default="fcf",
    )


def _add_result_printing_group(parser):
    parser.add_argument(
        "-hv", "--hide-value", help="hide the actual value printed out", dest="hide_value", action="store_true"
    )

    parser.add_argument("-e", "--eq-neq", help="target only equal and not equal operator", action="store_true")


def _add_html_group(parser):
    parser.add_argument("--html-dir", help="specify the html directory to generate static html files.")


def parse_args(args, namespace=None):
    cur_path = pathlib.Path(__file__)
    fcf_path = cur_path.parent / "default_config.ini"
    parser = configargparse.ArgParser(
        description="Find float comparison expression in python file.",
        default_config_files=[str(fcf_path)],
        add_config_file_help=False,
        add_env_var_help=False,
    )
    _add_require_group(parser)
    _add_html_group(parser)
    cli.add_general_option(parser.add_argument_group("General option"))
    cli.add_analysis_related_group(parser.add_argument_group("Analysis related option"))
    result_printing_group = parser.add_argument_group("Fcf related options")
    _add_result_printing_group(result_printing_group)
    parser.parse_args(args, namespace=namespace)


def print_time(func):
    def _(*args, **kwargs):
        initial = time.perf_counter()
        result = func(*args, **kwargs)
        print("elapsed time: {} seconds".format(time.perf_counter() - initial))
        return result

    return _


def get_checker(args):
    if not args.checks or (len(args.checks) > 0 and args.checks[0] == "ALL"):
        return [fcf_solver, loop_solver]
    sel = []
    for check in args.checks:
        if check not in CHECKER_SELECT:
            MANAGER.logger.error(
                "CLI",
                "The check specify: {} not in a list of available checker: {}.",
                check,
                list(CHECKER_SELECT.keys()),
            )
            raise ValueError(
                "The check specify: {} not in a list of available checker: {}".format(
                    check, list(CHECKER_SELECT.keys())
                )
            )
        sel.append(CHECKER_SELECT[check])
    return sel


def run(args, output_stream=sys.stdout, error_stream=sys.stderr):
    MANAGER.config = args
    if args.verbose >= 1:
        cli.print_info(args, output_stream=output_stream)
    result = ""
    for fn in args.file_name:
        file_path = pathlib.Path(fn)
        text = file_path.read_text().expandtabs(8)
        file_path_text = file_path.resolve().as_uri()
        MANAGER.logger.info("FCF", "analyzing file: {}\n", file_path_text)
        with utilities.temp_config(MANAGER, args):
            MANAGER.reload_protocol()
            as_tree = MANAGER.build_tree(text)
            MANAGER.apply_transform(as_tree)
            cfg_ir = cfg.Cfg(as_tree)
            cfg_ir.apply_transform()
            cfg_ir.convert_to_ssa()
            for checker_mod in get_checker(args):
                result += checker_mod.solve(cfg_ir, as_tree, text, file_path_text, args)
    MANAGER.logger.info("COV", MANAGER.get_infer_statistics())
    if result:
        error_stream.write(result)
        sys.exit(1)


def main():
    c = ConfigNamespace()
    parse_args(sys.argv[1:], namespace=c)
    MANAGER.initialize(c)
    run(c)


if __name__ == "__main__":
    main()
