import textwrap
import ast

OPERATOR_VARIABLE = 0
LEFT_OPERATOR_CONSTANT = 1
RIGHT_OPERATOR_CONSTANT = 2


ms = textwrap.dedent

operator_dict = {'Add': '+', 'Sub': '-', 'Mult': '*', 'Div': '/', 'BitOr': '|', 'BitXor': '^', 'BitAnd': '&',
                 'Lt': '<', 'Gt': '>', 'FloorDiv': '//', 'Mod': '%', 'Pow': '^', 'LShift': '<<', 'RShift': '>>',
                 'Eq': '==', 'NotEq': '!=', 'LtE': '<=', 'GtE': '>=', 'Is': 'is', 'IsNot': 'is not', 'In': 'in',
                 'NotIn': 'not in'}

def is_num(s):
    if isinstance(s, int) or isinstance(s, float):
        return True
    return False


def get_var_or_num(value):
    if isinstance(value, ast.Name):
        return value.id
    else:
        return value.n


def value_list_get_op_type(val_list):
    return val_list[1]

def value_list_get_var(val_list):
    return val_list[0]