import textwrap
import ast

OPERATOR_VARIABLE = 0
LEFT_OPERATOR_CONSTANT = 1
RIGHT_OPERATOR_CONSTANT = 2


ms = textwrap.dedent


def is_num(s):
    if isinstance(s, int) or isinstance(s, float):
        return True
    return False


def get_var_or_num(value):
    if isinstance(value, ast.Name):
        return value.id
    else:
        return value.n