import json
import os

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


class CovAnalysisHtmlReport(report.InferHtmlReport):
    def __init__(self, file_path, file_src, tree, token_cls=Tokens):
        super(CovAnalysisHtmlReport, self).__init__(
            file_path, file_src, tree, token_cls, os.path.join(os.path.dirname(__file__), "pyfile_cov.html")
        )
        self.warning_lines = {}

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
