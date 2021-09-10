# import protocols and enable builtins bootstrapping
# enable monkey patching of inference
from . import inference, nodes, protocols
from .manager import AstManager

MANAGER = AstManager()
__all__ = ["protocols", "AstManager", "MANAGER", "nodes", "inference"]
