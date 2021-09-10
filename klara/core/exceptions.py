from textwrap import dedent


class CustomException(Exception):
    def __init__(self, msg="", override_msg=""):
        self.msg = msg if override_msg == "" else override_msg
        self.msg = dedent(self.msg)
        super(CustomException, self).__init__(self.msg)


class OperationIncompatible(CustomException):
    """Throw when the operation is not compatible. E.g. calling subscript to a name node"""

    def __init__(self, operation=None, target=None, override_msg=""):
        self.msg = "Operation :{} failed for target: {}".format(operation, target)
        super(OperationIncompatible, self).__init__(self.msg, override_msg)


class RenameError(CustomException):
    def __init__(self, node, scope):
        self.node = node
        self.scope = scope
        self.msg = 'Unable to rename variable: "{}" in scope: {}'.format(node, scope)
        super(RenameError, self).__init__(self.msg)


class VariableNotExistStackError(CustomException):
    def __init__(self, var):
        self.var = var
        self.msg = "variable :{} does not exist".format(var)
        super(VariableNotExistStackError, self).__init__(self.msg)


class StructureError(CustomException):
    def __init__(self, node=None, parent_node=None, expected_parent_node=None, override_msg=""):
        self.node = node
        self.parent_node = parent_node
        self.expected_parent_node = expected_parent_node
        self.msg = """\
Invalid structure. {} is children of {}. {} should be children of {}
            """.format(
            node, parent_node, node, expected_parent_node
        )
        super(StructureError, self).__init__(self.msg, override_msg)


class UnannotatedError(CustomException):
    def __init__(self, variable):
        self.msg = """variable {} is unannotated""".format(variable)
        super(UnannotatedError, self).__init__(self.msg)


class InstanceNotExistError(CustomException):
    """This is thrown when trying to access the attribute of a non instance variable.
    e.g.
    x = 1
    y = x.y     # ----> thrown
    x.z = 1     # ----> thrown in renaming
    """

    def __init__(self, instance):
        self.msg = "{} is not an instance".format(instance)
        super(InstanceNotExistError, self).__init__(self.msg)


class NotInLocalsError(CustomException):
    """Variable does not exist in a locals scope"""

    def __init__(self, var, scope):
        self.var = var
        self.scope = scope
        self.msg = "{} does not exist in scope: {}".format(var, scope)
        super(NotInLocalsError, self).__init__(self.msg)


class UnimplementedError(CustomException):
    """thrown when certain node/features/method is unimplemented"""

    def __init__(self, obj, override_msg=""):
        self.object = obj
        self.msg = "{} is unimplemented".format(obj)
        super(UnimplementedError, self).__init__(self.msg, override_msg)


class DunderUnimplemented(UnimplementedError):
    def __init__(self, method_name, target_cls):
        self.method_name = method_name
        self.target_cls = target_cls
        self.msg = ""
        if target_cls:
            self.msg = "{} is unimplemented in scope {}".format(method_name, target_cls)
        super(DunderUnimplemented, self).__init__(method_name, self.msg)


class InferenceTransformError(CustomException):
    pass


class InconsistentMroError(CustomException):
    pass


class DuplicateBasesError(CustomException):
    pass


class ContainerExtractError(CustomException):
    pass
