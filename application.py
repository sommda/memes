#!flask/bin/python
from flask import Flask, jsonify, abort, request, make_response, redirect, url_for
from werkzeug import secure_filename
import os
import hashlib

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

application = Flask(__name__)
application.debug=True
application.config['UPLOAD_FOLDER'] = '/Users/sommda/python/memes_service/files'

tasks = [
    {
        'id': 1,
        'title': u'Buy groceries',
        'description': u'Milk, Cheese, Pizza, Fruit, Tylenol',
        'done': False
    },
    {
        'id': 2,
        'title': u'Learn Python',
        'description': u'Need to find a good Python tutorial on the web',
        'done': False
    }
]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def hash_file_contents(file, block_size=2**14):
    hash = hashlib.sha1()
    while True:
        data = file.read(block_size)
        if not data:
            break;
        hash.update(data)
    return hash.hexdigest()

@application.route('/')
def hello_world():
    return "Hello world!"

@application.route('/todo/api/v1.0/tasks', methods = ['GET'])
def get_tasks():
    return jsonify( { 'tasks': tasks } )

@application.route('/todo/api/v1.0/tasks/<int:task_id>', methods = ['GET'])
def get_task(task_id):
    task = filter(lambda t: t['id'] == task_id, tasks)
    if len(task) == 0:
        abort(404)
    return jsonify( { 'task': task[0] } )

@application.route('/todo/api/v1.0/tasks', methods = ['POST'])
def create_task():
    if not request.json or not 'title' in request.json:
        abort(400)
    task = {
        'id': tasks[-1]['id'] + 1,
        'title': request.json['title'],
        'description': request.json.get('description', ""),
        'done': False
    }
    tasks.append(task)
    return jsonify( { 'task': task } ), 201

@application.route('/api/v1.0/images', methods = ['POST'])
def create_image():
    uploaded_file = request.files['file']
    if uploaded_file and allowed_file(uploaded_file.filename):
        hash = hash_file_contents(uploaded_file)
        uploaded_file.save(os.path.join(application.config['UPLOAD_FOLDER'], hash))
        return jsonify( { 'hash': hash, 'filename': uploaded_file.filename } )
    else:
        abort(400)

@application.route('/todo/api/v1.0/tasks/<int:task_id>', methods = ['PUT'])
def update_task(task_id):
    task = filter(lambda t: t['id'] == task_id, tasks)
    if len(task) == 0:
        abort(404)
    if not request.json:
        abort(400)
    if 'title' in request.json and type(request.json['title']) != unicode:
        abort(400)
    if 'description' in request.json and type(request.json['description']) is not unicode:
        abort(400)
    if 'done' in request.json and type(request.json['done']) is not bool:
        abort(400)
    task[0]['title'] = request.json.get('title', task[0]['title'])
    task[0]['description'] = request.json.get('description', task[0]['description'])
    task[0]['done'] = request.json.get('done', task[0]['done'])
    return jsonify( { 'task': task[0] } )

@application.route('/todo/api/v1.0/tasks/<int:task_id>', methods = ['DELETE'])
def delete_task(task_id):
    task = filter(lambda t: t['id'] == task_id, tasks)
    if len(task) == 0:
        abort(404)
    tasks.remove(task[0])
    return jsonify( { 'result': True } )

@application.route('/upload', methods = ['GET'])
def upload_page():
    return '''
    <!doctype html>
    <title>Upload new file</title>
    <h1>Upload new file</h1>
    <form action="/api/v1.0/images" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''

@application.errorhandler(404)
def not_found(error):
    return make_response(jsonify( { 'error': 'Not found' } ), 404)

if __name__ == '__main__':
    application.run(host='0.0.0.0', debug = True)
