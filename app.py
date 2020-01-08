import os

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    make_response,
    redirect,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_api import status
from flask_cors import CORS
from flask_session import Session
from pm4py.objects.log.importer.xes import factory as xes_importer
from skelevision import TraceLog, LogSkeleton
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "./uploads"
CACHE_FOLDER = "./cache"
ALLOWED_EXTENSIONS = {"xes", "gz"}
SESSION_FILE_DIR = CACHE_FOLDER
SESSION_FILE_THRESHOLD = 3

app = Flask(__name__)

app.config.from_object(__name__)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_FILE_SIZE"] = 1024 ** 3

app.config["SESSION_FILE_DIR"] = SESSION_FILE_DIR
app.config["SESSION_FILE_THRESHOLD"] = SESSION_FILE_THRESHOLD
app.config["SECRET_KEY"] = os.urandom(64)
app.config["SESSION_TYPE"] = "filesystem"

Session(app)

app.config["CORS_HEADERS"] = "Content-Type"
CORS(app, supports_credentials=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def process(dataset):
    tl = (TraceLog.from_xes(dataset))
    tl_aug = tl.augment()
    session["dataset"] = tl_aug


def valid(request):
    data = request.get_json(force=True)

    # Missing parameters
    if "requiredActivities" not in data or "forbiddenActivities" not in data:
        return False

    reqA = set(data["requiredActivities"])
    forbA = set(data["forbiddenActivities"])

    # All filter activities are present in the original dataset
    for a in reqA.union(forbA):
        if a not in session["dataset"].labels:
            return False

    # The two filter set are disjoint
    if len(reqA.intersection(forbA)) > 0:
        return False

    return True


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        content = {"No file part": "Plase upload a new file."}
        return jsonify(content), status.HTTP_400_BAD_REQUEST

    f = request.files["file"]

    if f.filename == "":
        content = {"No file selected for uploading": "Plase upload a new file."}
        return jsonify(content), status.HTTP_400_BAD_REQUEST

    if not allowed_file(f.filename):
        content = {"Allowed file types are xes and gz": "Plase try again."}
        return jsonify(content), status.HTTP_400_BAD_REQUEST

    try:
        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"], secure_filename(f.filename)
        )
        f.save(filepath)
    except Exception as e:
        content = {
            "Unexpected exception occured: {}".format(e): "Please try again later."
        }
        return jsonify(content), status.HTTP_500_INTERNAL_SERVER_ERROR

    try:
        process(filepath)
    except Exception as e:
        content = {
            "Unexpected exception occured: {}".format(e): "Please try again later."
        }
        return jsonify(content), status.HTTP_500_INTERNAL_SERVER_ERROR

    content = {"Uploading the dataset was succesful.": "Succesful."}
    return jsonify(content), status.HTTP_200_OK


@app.route("/labels", methods=["GET"])
def labels():
    if not session.get("dataset"):
        abort(404)

    tl = session["dataset"]

    labels = list(tl.labels)
    labels = {"labels": labels}

    return jsonify(labels), status.HTTP_200_OK


@app.route("/mine", methods=["POST"])
def mine():

    if not session.get("dataset"):
        abort(404)

    if not valid(request):
        content = {"Invalid request": "Please check your request and try again."}
        return jsonify(content), status.HTTP_400_BAD_REQUEST

    tracelog = session["dataset"]

    data = request.get_json(force=True)

    reqA = set(data["requiredActivities"])
    forbA = set(data["forbiddenActivities"])

    results = LogSkeleton.mine(tracelog, reqA, forbA)

    response = {
        "relationships": dict(),
        "statistics": {
            "node": results['statistics']['node'],
        }
    }

    for k, v in results["relationships"].items():
        response["relationships"][k] = [list(pair) for pair in v]

    return jsonify(response)


@app.errorhandler(404)
def not_found(error):
    return make_response(
        jsonify({"error": "Dataset not found. Please upload a dataset first"}), 404
    )


if __name__ == "__main__":
    app.run(debug=True)
