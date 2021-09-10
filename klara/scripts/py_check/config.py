from klara.core import config


class ConfigNamespace(config.Config):
    command = ""
    file_name = []
    eq_neq = False
    hide_value = False
    checks = []
    html_dir = ""

    def is_eq_neq(self):
        if hasattr(self, "eq_neq"):
            return self.eq_neq
        return False

    def is_hiding_value(self):
        if hasattr(self, "hide_value"):
            return self.hide_value
        return False

    def get_operator_involved(self):
        if self.is_eq_neq():
            return "==", "!="
        return ">", "<", ">=", "<=", "==", "!=", "in", "not in"
