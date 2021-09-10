import ast

_ast3 = _ast2 = None

try:
    import typed_ast.ast3 as _ast3
    import typed_ast.ast27 as _ast2
    from typed_ast import conversions
except ImportError:
    pass


def get_parser_module():
    return _ast3 or ast


def parse(string, py2=False):
    parse_mod = (_ast2 if py2 else _ast3) or ast
    tree = parse_mod.parse(string)
    if py2:
        tree = conversions.py2to3(tree)
    return tree
