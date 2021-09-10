#!python
import argparse
import ast
import astor
import pathlib2
import sys


class FStringConverter(ast.NodeTransformer):
    def visit_JoinedStr(self, node):
        log(f"converting {astor.to_source(node)}")
        main_str = ""
        formatted_args = []
        for b in node.values:
            if isinstance(b, ast.Str):
                main_str += b.s
            elif isinstance(b, ast.FormattedValue):
                formatted_args.append(b.value)
                main_str += "{}"
        return ast.Call(
            args=formatted_args,
            func=ast.Attribute(ctx=ast.Load(), attr="format", value=ast.Str(s=main_str)),
            keywords=[],
        )


def _add_require_group(parser):
    parser.add_argument("file_name", type=str, help="specify the filename")


def _add_optional_group(parser):
    parser.add_argument("-v", "--verbose", help="specify the verbosity", action="store_true")


def parse_args(args, namespace=None):
    parser = argparse.ArgumentParser(description="Optional app description")
    _add_optional_group(parser)
    _add_require_group(parser)
    return parser, parser.parse_args(args, namespace=namespace)


class ConfigNamespace:
    pass


c = ConfigNamespace()


def log(msg):
    if c.verbose is True:
        print(msg)


if __name__ == "__main__":
    parser, args = parse_args(sys.argv[1:], namespace=c)
    file_folder = c.file_name
    for f in pathlib2.Path(file_folder).glob("**/*.py"):
        log(f"converting file{f}")
        s = ast.fix_missing_locations(FStringConverter().visit(ast.parse(f.read_text())))
        converted_str = astor.to_source(s)
        f.write_text(converted_str)
