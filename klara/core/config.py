"""provide config for analysis related or inference"""


class Config:
    type_inference = True
    max_inference_value = None
    py_version = 3
    analyze_procedure = False
    typeshed_select = []
    stubs = []
    verbose = 0
    display_mem_usage = False
    infer_extension_files = []
    no_analyze_procedure = False
    html_server = False
    html_server_port = 5000
    enable_infer_sequence = False
    statistics = None

    def __init__(
        self,
        eq_neq=False,
        type_inference=True,
        max_inference_value=None,
        py_version=3,
        typeshed_select=None,
        stubs=None,
    ):
        self.eq_neq = eq_neq
        self.type_inference = type_inference
        self.max_inference_value = max_inference_value
        self.py_version = py_version
        self.typeshed_select = typeshed_select or []
        self.stubs = stubs or []

    def is_type_inference(self):
        if hasattr(self, "type_inference"):
            return self.type_inference
        return False

    def is_analyze_procedure(self):
        if hasattr(self, "no_analyze_procedure"):
            return self.no_analyze_procedure
        return False
