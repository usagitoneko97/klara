import json
from types import SimpleNamespace

from klara.core.html import report
from klara.core.manager import AstManager
from klara.html.report import escape

MANAGER = AstManager()


class Tokens:
    __slots__ = ("cls", "name", "scol", "id", "infer_path", "lineno")

    def __init__(self, cls, name, scol, id, lineno):
        self.cls = cls
        self.name = name
        self.lineno = lineno
        self.scol = scol
        self.id = id
        self.infer_path = []


class PyCheckHtmlReport(report.InferHtmlReport):
    def __init__(self, file_path, file_src, tree, token_cls=Tokens, float_warnings=None):
        super(PyCheckHtmlReport, self).__init__(file_path, file_src, tree, token_cls)
        self.warning_lines = {}
        self.float_warnings = float_warnings
        self.init_warning_lines()

    def init_warning_lines(self):
        if self.float_warnings:
            for trace, items_in_trace in self.float_warnings.items():
                for lineno in sorted(items_in_trace.warning):
                    self.warning_lines.setdefault(lineno, []).extend(items_in_trace.warning[lineno])

    def process_line(self, lineno, tokens):
        warning_cols = []
        short_annotations = ""
        long_annotations = []
        category = "run"
        if lineno in self.warning_lines:
            for warning in self.warning_lines[lineno]:
                infer_path_result = self.process_infer_path(warning.infer_path)
                short_annotations = "float"
                warning_cols.append(
                    (warning.col_offset, warning.col_offset + len(warning.value_repr) - 1, infer_path_result)
                )
                if warning.value != "Unknown value":
                    long_annotations.append("{} has value: {}".format(warning.value_repr, warning.value))
                else:
                    long_annotations.append("{} has value type float".format(warning.value_repr))
                category = "mis"
        for scol, endcol, path_result in warning_cols:
            for token in tokens:
                if scol <= token.scol <= endcol and token.cls != "ws":
                    token.cls += " float_warning"
                    token.infer_path.append(path_result)
        return SimpleNamespace(
            tokens=tuple(tokens),
            number=lineno,
            category=category,
            short_annotations=short_annotations,
            long_annotations=long_annotations,
        )

    def get_analysis_to_report(self):
        lines = []
        for lineno, tokens in self.tokenize_source():
            lines.append(self.process_line(lineno, tokens))
        file_data = SimpleNamespace(
            relative_filename=self.analysis_file_path,
            lines=lines,
            infer_server="checked" if hasattr(MANAGER.config, "html_server") and MANAGER.config.html_server else "",
        )
        return file_data

    def process_tokens(self, ldata):
        htmls = []
        for token in ldata.tokens:
            if token.cls == "ws":
                htmls.append(escape(token.name))
            else:
                tok_html = escape(token.name) or "&nbsp;"
                htmls.append(
                    u"<span class=\"{}\" id={} lineno={} col={} infer_paths='{}'>{}</span>".format(
                        token.cls, token.id, token.lineno, token.scol, json.dumps(token.infer_path), tok_html
                    )
                )
        ldata.html = "".join(htmls)
