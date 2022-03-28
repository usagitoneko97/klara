import ast

_ast3 = _ast2 = None


def get_parser_module():
    return _ast3 or ast


def parse(string, py2=False):
    parse_mod = (_ast2 if py2 else _ast3) or ast
    tree = parse_mod.parse(string)
    return tree
