import os

from flask import Flask, flash, redirect, request, session, url_for, jsonify
from flask_session import Session
from werkzeug.utils import secure_filename

from pm4py.objects.log.importer.xes import factory as xes_import_factory

UPLOAD_FOLDER = './static'
CACHE_FOLDER = './cache'
ALLOWED_EXTENSIONS = {'xes', 'gz'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1024 ** 3
SESSION_TYPE = 'filesystem'
SESSION_FILE_DIR = CACHE_FOLDER
SESSION_FILE_THRESHOLD = 10
app.config.from_object(__name__)
Session(app)

def process(dataset):
    tracelog = dict()
    log = xes_import_factory.apply(dataset, variant="nonstandard")
    for case in log:
        a = tuple([event["concept:name"] for event in case])

        if a not in tracelog:
            tracelog[a] = 0
        tracelog[a] += 1

    session["dataset"] = tracelog

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            process(filepath)
            return filepath
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

@app.route('/eval', methods=['GET', 'POST'])
def eval():
    s_tracelog = [{"key": k, "value": v} for k, v in session['dataset'].items()]
    return jsonify(s_tracelog)

if __name__ == "__main_":
    app.run(debug=True)  # run app in debug mode on port 5000
