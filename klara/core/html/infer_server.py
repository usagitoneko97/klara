import pathlib
from flask import Flask, jsonify, request, send_from_directory

from klara.core import manager

session = {}

MANAGER = manager.AstManager()
app = Flask(__name__)


@app.route("/", methods=["GET"])
def base_infer_html():
    return session["html_reporter"].html_file()


def warn():
    return "error"


@app.route("/infer", methods=["GET"])
def infer_node():
    lineno = request.args.get("lineno", None)
    if not lineno:
        return warn()
    col = request.args.get("col", None)
    if not col:
        return warn()

    response = session["html_reporter"].infer(int(lineno), int(col), session["context"])
    MANAGER.logger.info("HTML", "getting response of: {}", response)
    return jsonify(response)


def run(port, html_reporter, context):
    session["html_reporter"] = html_reporter
    session["context"] = context
    app.run(port=port)


@app.route("/<path:filename>")
def download_file(filename):
    return send_from_directory(
        pathlib.Path(__file__).parent.parent.parent / "html/htmlfiles/", filename, as_attachment=True
    )
