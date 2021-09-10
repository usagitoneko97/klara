import datetime
import os
import re
import shutil
from types import SimpleNamespace

from klara.core import manager
from . import phystokens, templite

MANAGER = manager.AstManager()

STATIC_PATH = os.path.join(os.path.dirname(__file__), "htmlfiles")
HTML_SOURCE = os.path.join(os.path.dirname(__file__), "htmlfiles/pyfile.html")


class Tokens:
    __slots__ = ("cls", "name", "scol", "id", "lineno")

    def __init__(self, cls, name, scol, id, lineno):
        self.cls = cls
        self.name = name
        self.lineno = lineno
        self.scol = scol
        self.id = id


class HtmlReporter:
    """provide the basic functionality of displaying python file to html."""

    STATIC_FILES = [
        "style.css",
        "jquery.min.js",
        "jquery.ba-throttle-debounce.min.js",
        "jquery.hotkeys.js",
        "jquery.isonscreen.js",
        "jquery.tablesorter.min.js",
        "coverage_html.js",
        "keybd_closed.png",
        "keybd_open.png",
        "bootstrap",
        "down.png",
        "up.png",
        "popper.min.js",
    ]

    def __init__(self, analysis_file_path, pysrc, tree, token_cls=Tokens, html_source_path=""):
        self.analysis_file_path = analysis_file_path
        self.pysrc = pysrc
        self.tree = tree
        self.token_cls = token_cls
        self.template_globals = {
            # Functions available in the templates.
            "escape": escape,
            "pair": pair,
            "len": len,
            # Constants for this report.
            "__url__": "",
            "__version__": "",
            "title": "sca",
            "time_stamp": format_local_datetime(datetime.datetime.now()),
            "extra_css": None,
            "has_arcs": False,
            "show_contexts": False,
            # Constants for all reports.
            # These css classes determine which lines are highlighted by default.
            "category": {
                "exc": "exc show_exc",
                "mis": "mis show_mis",
                "par": "par run show_par",
                "run": "run",
            },
        }
        with open(html_source_path or HTML_SOURCE, "r") as f:
            self.source_tmpl = templite.Templite(f.read(), self.template_globals)
        self._token_counter = 0
        self.lineno_cache = {}

    def generate_static_html(self, html_dir):
        """Generate static html at directory.
        By default, it's just generating the python source. Since there is no information,
        derived is responsible to place information, in one of the process_* method.
        """
        html_path = os.path.join(html_dir, os.path.basename(self.analysis_file_path) + ".html")
        html_source = self.html_file()
        if os.path.exists(html_dir):
            shutil.rmtree(html_dir)
        os.mkdir(html_dir)
        self.make_local_static_report_files(html_dir)
        write_html(html_path, html_source)

    def make_local_static_report_files(self, html_dir):
        """Make local instances of static files for HTML report."""
        # The files we provide must always be copied.
        for static in self.STATIC_FILES:
            static_file_name = data_filename(static)
            if os.path.isdir(static_file_name):
                copy_meth = shutil.copytree
            else:
                copy_meth = shutil.copyfile
            copy_meth(static_file_name, os.path.join(html_dir, static))

    def _make_token_id(self):
        self._token_counter += 1
        return "i" + str(self._token_counter)

    def tokenize_source(self):
        for lineno, tokens in enumerate(phystokens.source_token_lines(self.pysrc), start=1):
            converted_tokens = []
            for token in tokens:
                token_id = self._make_token_id()
                converted_tokens.append(self.token_cls(*token, token_id, lineno))
            self.lineno_cache[lineno] = converted_tokens
            yield lineno, converted_tokens

    def process_line(self, lineno, tokens):
        """process each line of tokens.
        Derived class can implement other types of processing. E.g. handling the category
        """
        category = "run"
        short_annotations = ""
        long_annotations = []
        return SimpleNamespace(
            tokens=tuple(tokens),
            number=lineno,
            category=category,
            short_annotations=short_annotations,
            long_annotations=long_annotations,
        )

    def process_tokens(self, ldata):
        htmls = []
        for token in ldata.tokens:
            if token.cls == "ws":
                htmls.append(escape(token.name))
            else:
                tok_html = escape(token.name) or "&nbsp;"
                htmls.append(
                    u'<span class="{}" id={} lineno={} col={} >{}</span>'.format(
                        token.cls, token.id, token.lineno, token.scol, tok_html
                    )
                )
        ldata.html = "".join(htmls)

    def process_annotations(self, ldata):
        if ldata.short_annotations:
            # 202F is NARROW NO-BREAK SPACE.
            # 219B is RIGHTWARDS ARROW WITH STROKE.
            ldata.annotate = ldata.short_annotations
        else:
            ldata.annotate = None

        if ldata.long_annotations:
            longs = ldata.long_annotations
            ldata.annotate_long = "\n".join(longs)
        else:
            ldata.annotate_long = None

    def process_class(self, ldata):
        css_classes = []
        if ldata.category:
            css_classes.append(self.template_globals["category"][ldata.category])
        ldata.css_class = " ".join(css_classes) or "pln"

    def get_analysis_to_report(self):
        lines = []
        for lineno, tokens in self.tokenize_source():
            lines.append(self.process_line(lineno, tokens))
        file_data = SimpleNamespace(
            relative_filename=self.analysis_file_path,
            lines=lines,
        )
        return file_data

    def html_file(self):
        file_data = self.get_analysis_to_report()
        for ldata in file_data.lines:
            # Build the HTML for the line.
            self.process_tokens(ldata)
            self.process_annotations(ldata)
            self.process_class(ldata)

        html = self.source_tmpl.render(file_data.__dict__)
        return html


def escape(t):
    """HTML-escape the text in `t`.

    This is only suitable for HTML text, not attributes.

    """
    # Convert HTML special chars into HTML entities.
    return t.replace("&", "&amp;").replace("<", "&lt;")


def pair(ratio):
    """Format a pair of numbers so JavaScript can read them in an attribute."""
    return "%s %s" % ratio


def format_local_datetime(dt):
    """Return a string with local timezone representing the date.
    If python version is lower than 3.6, the time zone is not included.
    """
    try:
        return dt.astimezone().strftime("%Y-%m-%d %H:%M %z")
    except (TypeError, ValueError):
        # Datetime.astimezone in Python 3.5 can not handle naive datetime
        return dt.strftime("%Y-%m-%d %H:%M")


def write_html(fname, html):
    """Write `html` to `fname`, properly encoded."""
    html = re.sub(r"(\A\s+)|(\s+$)", "", html, flags=re.MULTILINE) + "\n"
    with open(fname, "wb") as fout:
        fout.write(html.encode("ascii", "xmlcharrefreplace"))


def data_filename(fname):
    """Return the path to a data file of ours.

    The file is searched for on `STATIC_PATH`, and the first place it's found,
    is returned.

    Each directory in `STATIC_PATH` is searched as-is, and also, if `pkgdir`
    is provided, at that sub-directory.

    """
    static_filename = os.path.join(STATIC_PATH, fname)
    if os.path.exists(static_filename):
        return static_filename
    else:
        raise ValueError("Couldn't find static file %r from %r, tried: %r" % (fname, os.getcwd(), STATIC_PATH))
