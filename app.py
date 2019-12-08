import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, jsonify, flash
from werkzeug.utils import secure_filename
from pm4py.objects.log.importer.xes import factory as xes_importer
from flask_session import Session
from flask_cors import CORS
from flask_api import status
from skelevision import TraceLog

UPLOAD_FOLDER = 'uploads'
CACHE_FOLDER = 'cache'
ALLOWED_EXTENSIONS = {'xes','jpg'}
app = Flask(__name__)
app.config.from_object(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_FILE_SIZE'] = 1024 ** 3
app.config['SECRET_KEY'] = os.urandom(64)
app.config['SESSION_TYPE'] = 'filesystem'
SESSION_FILE_DIR = CACHE_FOLDER
SESSION_FILE_THRESHOLD = 10
app.config['CORS_HEADERS'] = 'Content-Type'
CORS(app, supports_credentials=True)

Session(app)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
		   
def process(dataset):
    tracelog = dict()
    log = xes_importer.apply(dataset)
    for case in log:
        a = tuple([event["concept:name"] for event in case])

        if a not in tracelog:
            tracelog[a] = 0
        tracelog[a] += 1
    session["dataset"] = TraceLog(tracelog)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

@app.route('/upload', methods = ['GET','POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            content = {'No file part': 'Plase upload a new file.'}
            return jsonify(content), status.HTTP_400_BAD_REQUEST
        f = request.files['file']
        if f.filename == "":
            content = {'No file selected for uploading': 'Plase upload a new file.'}
            return jsonify(content), status.HTTP_400_BAD_REQUEST

        if f and allowed_file(f.filename):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename))
            f.save(filepath)
            process(filepath)
            s_tracelog = [{"key": k, "value": v} for k, v in session['dataset'].items()]
            return jsonify(s_tracelog), status.HTTP_200_OK

        else:
            content = {'Allowed file types are txt, pdf, png, jpg, jpeg, gif': 'Plase try again.'}
            return jsonify(content), status.HTTP_404_NOT_FOUND
    
    return render_template('upload.html')
   
        
if __name__ == '__main__':
    app.run()