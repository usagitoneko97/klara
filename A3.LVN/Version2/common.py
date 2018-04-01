OPERATOR_VARIABLE = 0
LEFT_OPERATOR_CONSTANT = 1
RIGHT_OPERATOR_CONSTANT = 2


def is_num(s):
    if isinstance(s, int) or isinstance(s, float):
        return True
    return False