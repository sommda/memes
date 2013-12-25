#!flask/bin/python
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from flask import Flask, jsonify, abort, request, make_response, redirect, url_for, send_file
from werkzeug import secure_filename
import io
import os
import hashlib

from PIL import Image, ImageEnhance, ImageDraw, ImageFont


ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif', 'bmp'])

application = Flask(__name__)
application.debug=True
application.config['UPLOAD_FOLDER'] = '/Users/sommda/python/memes_service/files'

conn = S3Connection('AKIAIR6KVOWNHSWCGGHQ', '3TCc+54FSTcT85pNpwEMQhUJ5gZrF4wYnP1KKnLE')
bucket = conn.get_bucket('meme-images-us-west-2', validate = False)

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

def top_text_pos(imagesize,textsize,margin):
    xcoord = imagesize[0]/2-textsize[0]/2
    ycoord = margin[1]
    return (xcoord,ycoord)
    
def bottom_text_pos(imagesize,textsize,margin):
    xcoord = imagesize[0]/2-textsize[0]/2
    ycoord = imagesize[1]-textsize[1]-margin[1]-20
    return (xcoord,ycoord)

def make_meme(image, toptext, bottomtext, textsize, textface="fonts/Impact.ttf", color="white"):
    font = ImageFont.truetype(textface, textsize)
    margin = (10,10)

    out_image = image.convert("RGBA")
    textlayer = Image.new("RGBA", out_image.size, (0,0,0,0))
    textdraw = ImageDraw.Draw(textlayer)

    if toptext:
        toptextsize = textdraw.textsize(toptext, font=font)
        toppos = top_text_pos(out_image.size, toptextsize, margin)
        textdraw.text(toppos, toptext, font=font, fill=color)

    if bottomtext:
        bottomtextsize = textdraw.textsize(bottomtext, font=font)
        bottompos = bottom_text_pos(out_image.size, bottomtextsize, margin)
        textdraw.text(bottompos, bottomtext, font=font, fill=color)

    return Image.composite(textlayer, out_image, textlayer)

@application.route('/api/v1.0/images/<string:image_hash>/info', methods = ['GET'])
def image_info(image_hash):
    key = bucket.get_key(image_hash)
    if key:
        buffer = io.BytesIO()
        key.get_contents_to_file(buffer)
        buffer.seek(0)
        im = Image.open(buffer)
        (width, height) = im.size
        return jsonify( { 'width': width, 'height': height } )

@application.route('/api/v1.0/images/<string:image_hash>/render', methods = ['GET'])
def render_image(image_hash):
    toptext = request.args.get("toptext")
    bottomtext = request.args.get("bottomtext")
    textsize = int(request.args.get("textsize", "60"))
    key = bucket.get_key(image_hash)
    if key:
        in_buffer = io.BytesIO()
        key.get_contents_to_file(in_buffer)
        in_buffer.seek(0)
        im = Image.open(in_buffer)
        im = make_meme(im, toptext, bottomtext, textsize)
        out_buffer = io.BytesIO()
        im.save(out_buffer, 'png')
        out_buffer.seek(0)
        return send_file(out_buffer, mimetype='image/png')
    else:
        abort(404)

@application.route('/api/v1.0/images', methods = ['POST'])
def create_image():
    uploaded_file = request.files['file']
    if uploaded_file and allowed_file(uploaded_file.filename):
        hash = hash_file_contents(uploaded_file)
        key = bucket.get_key(hash)
        if key:
            return jsonify( { 'hash': hash, 'message': 'Image already uploaded' } )
        else:
            key = bucket.new_key(hash)
            key.set_contents_from_file(uploaded_file, rewind = True)
            key.set_metadata('filename', uploaded_file.filename)
            return jsonify( { 'hash': hash, 'message': 'Image created',
                              'filename': uploaded_file.filename } )
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
