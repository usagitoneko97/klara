import pathlib
import sys

import astor
import configargparse

from klara import cli
from klara.klara_z3 import cov_manager
from . import config, solver

MANAGER = cov_manager.CovManager()


def _add_required_group(parser):
    parser.add_argument("input_test_file", help="specify input python file for analyzing.")
    parser.add_argument("-o", "--output-file", help="output pytest file to test input file")


def parse_args(args, namespace=None):
    cur_path = pathlib.Path(__file__)
    fcf_path = cur_path.parent / "default_config.ini"
    parser = configargparse.ArgParser(
        default_config_files=[str(fcf_path)],
        description="Analyse and auto suggesting test suite.",
        add_config_file_help=False,
        add_env_var_help=False,
    )
    _add_required_group(parser)
    cli.add_general_option(parser.add_argument_group("General option"))
    cli.add_analysis_related_group(parser.add_argument_group("Analysis related option"))
    parser.parse_args(args, namespace=namespace)


def run(input_str: str, input_file_name: str):
    tree = MANAGER.build_tree(ast_str=input_str)
    cfg = MANAGER.build_cfg(tree)
    cs = solver.ContractSolver(cfg, tree, input_file_name)
    MANAGER.logger.info("CONTRACT", "Running algorithm on file: {}", input_file_name)
    module = cs.solve()
    return astor.to_source(module.to_ast())


def main():
    c = config.ContractConfig()
    parse_args(sys.argv[1:], namespace=c)
    MANAGER.initialize(c)
    cli.print_info(c)
    input_file = pathlib.Path(c.input_test_file)
    if input_file.exists():
        output_test = run(input_file.read_text(), input_file.stem)
        output_file = c.get_output_file()
        MANAGER.logger.info("CONTRACT", "Converting inferred test case to ast and write to file: {}", output_file)
        with open(output_file, "w") as f:
            f.write(output_test)
    else:
        MANAGER.logger.error("CONTRACT" "input file: {} doesn't exist", c.input_test_file)


if __name__ == "__main__":
    main()
