import json
from flask import Flask, session, jsonify
from flask_session import Session
from pm4py.objects.log.importer.xes import factory as xes_import_factory

from rq import Queue
from rq.job import Job
from worker import conn

app = Flask(__name__)  # create the Flask app
SESSION_TYPE = "redis"
app.config.from_object(__name__)
Session(app)


q = Queue(connection=conn)


def process(dataset):
    tracelog = dict()
    log = xes_import_factory.apply(dataset, variant="nonstandard")
    for case in log:
        a = tuple([event["concept:name"] for event in case])

        if a not in tracelog:
            tracelog[a] = 0
        tracelog[a] += 1

    session["data"] = tracelog


@app.route("/")
def index():
    return "Hello"


@app.route("/browse/<dataset>", methods=["GET"])
def process_dataset(dataset):
    # job = q.enqueue_call(func=process, args=(dataset,), result_ttl=5000)
    # print(job.get_id())
    # return job.get_id()
    tracelog = dict()
    log = xes_import_factory.apply(dataset, variant="nonstandard")
    for case in log:
        a = tuple([event["activity"] for event in case])

        if a not in tracelog:
            tracelog[a] = 0
        tracelog[a] += 1

    session["data"] = tracelog
    # Serialize
    s_tracelog = [{"key": k, "value": v} for k, v in tracelog.items()]
    return jsonify(s_tracelog)


@app.route("/visualize/<job_key>")
def visualize_dataset(job_key):
    job = Job.fetch(job_key, connection=conn)

    if job.is_finished:
        return str(job.result), 200
    else:
        return "Nay!", 202


if __name__ == "__main_":
    app.run(debug=True)  # run app in debug mode on port 5000

