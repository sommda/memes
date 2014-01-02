#!flask/bin/python
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from flask import Flask, jsonify, abort, request, make_response, redirect, url_for, send_file
from flask import render_template
from werkzeug import secure_filename
import io
import os
import hashlib
import uuid
import datetime
import string
from Crypto.Random.random import sample, getrandbits

from PIL import Image, ImageEnhance, ImageDraw, ImageFont

from boto.dynamodb2.table import Table

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif', 'bmp'])

application = Flask(__name__)
application.debug=True
application.config['UPLOAD_FOLDER'] = '/Users/sommda/python/memes_service/files'

conn = S3Connection()
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
def root():
    return render_template('memegen.html')

@application.route('/api/v1.0/users', methods = ['GET','POST'])
def handle_users():
    if request.method == 'GET':
        return get_users()
    elif request.method == 'POST':
        return create_user()

def generate_salt(length):
    return ''.join(sample(list(string.ascii_lowercase), length))

def create_user():
    if not request.form.get('user-id'):
        return jsonify( { 'message': 'user-id is required' } ), 400
    if not request.form.get('password'):
        return jsonify( { 'message': 'password is required' } ), 400
    users = Table('Users')
    user_id = request.form.get('user-id')
    password = request.form.get('password')
    kwargs = { 'user-id': user_id }
    if users.get_item(**kwargs):
        return jsonify( { 'message': 'user-id ' + user_id + 'is already in use' } ), 400
    salt = generate_salt(12)
    user = {
        'user-id': user_id,
        'create-time': datetime.datetime.now().isoformat(),
        'password-hash': hashlib.sha256(salt + password).hexdigest(),
        'password-salt': salt
    }
    users.put_item(data = user)
    return jsonify( { 'user-id': user_id,
                      'create-time': user['create-time'] } ), 201

def get_users():
    users = Table('Users')
    for user in users.scan():
        result.append( { 'user-id': user['user-id'],
                         'create-time': user['create-time']
                       } )
    return jsonify( { 'users': result } )

def generate_session_id():
    randint = getrandbits(128)
    return str(uuid.UUID(int = randint))

@application.route('/api/v1.0/login', methods = ['POST'])
def login():
    users = Table('Users')

    # Check that the user exists
    user_id = request.form.get('user-id')
    kwargs = { 'user-id': user_id }
    user = users.get_item(**kwargs)
    if not user:
        return jsonify( { 'message': 'unknown user-id/password combination' } ), 400

    # Check that the password matches
    password = request.form.get('password')
    password_hash = hashlib.sha256(user['password-salt'] + password).hexdigest()
    if password_hash != user['password-hash']:
#        return jsonify( { 'message': 'unknown user-id/password combination' } ), 400
        return jsonify( { 'message': 'cannot login with ' + user_id + '/' + password } ), 400

    # Create a new session
    sessions = Table('Sessions')
    session = {
        'session-id': generate_session_id(),
        'create-time': datetime.datetime.now().isoformat(),
        'user-id': user_id
    }
    sessions.put_item(data = session)
    return jsonify( { 'session': session } ), 201    


@application.route('/api/v1.0/memes/<string:meme_id>', methods = ['GET'])
def get_meme(meme_id):
    memes = Table('Memes')
    meme = memes.get_item(id=meme_id)
    return jsonify( { 'meme-id': meme['meme-id'],
                      'user-id': meme['user-id'],
                      'top-text': meme['top-text'],
                      'bottom-text': meme['bottom-text'],
                      'create-time': meme['create-time'],
                      'image-hash': meme['image-hash']
                      } )

@application.route('/api/v1.0/memes/<string:meme_id>/render', methods = ['GET'])
def render_meme(meme_id):
    memes = Table('Memes')
    kwargs = { 'meme-id': meme_id }
    meme = memes.get_item(**kwargs)
    if not meme:
        abort(404)
    meme_image_hash = meme['image-hash']
    if not meme_image_hash:
        abort(404)
    return render_meme_image(meme_image_hash, meme['top-text'],
                             meme['bottom-text'],
                             30)

@application.route('/api/v1.0/memes/<string:meme_id>/votes', methods = ['POST'])
def vote_meme(meme_id):
    session_id = request.cookies.get('session-id')
    if not session_id:
        return jsonify( { 'message': 'must be logged in' } ), 400
    sessions = Table('Sessions')
    kwargs = { 'session-id': session_id }
    session = sessions.get_item(**kwargs)
    if not session:
        return jsonify( { 'message': 'invalid session' } ), 400
    user_id = session['user-id']

    memes = Table('Memes')
    kwargs = { 'meme-id': meme_id }
    meme = memes.get_item(**kwargs)
    if not meme:
        abort(404)
    vote = request.form.get('vote')
    if not vote:
        vote = 1
    return jsonify( { 'user_id': user_id,
                      'meme_id': meme_id,
                      'vote': vote
                      } )

@application.route('/api/v1.0/memes', methods = ['GET','POST'])
def handle_memes():
    if request.method == 'GET':
        return get_memes()
    elif request.method == 'POST':
        return create_meme()

def get_memes():
    result = []
    memes = Table('Memes')
    for meme in memes.scan():
        result.append( { 'image-hash': meme['image-hash'],
                         'top-text': meme['top-text'],
                         'bottom-text': meme['bottom-text'],
                         'create-time': meme['create-time'],
                         'meme-id': str(meme['meme-id']),
                         'user-id': str(meme['user-id'])
                       } )
    return jsonify( { 'memes': result } )

def create_meme():
    session_id = request.cookies.get('session-id')
    if not session_id:
        return jsonify( { 'message': 'must be logged in' } ), 400
    sessions = Table('Sessions')
    kwargs = { 'session-id': session_id }
    session = sessions.get_item(**kwargs)
    if not session:
        return jsonify( { 'message': 'invalid session' } ), 400
    user_id = session['user-id']

    if not request.form.get('image-hash'):
        return jsonify( { 'message': 'image-hash is required' } ), 400
    memes = Table('Memes')
    meme = {
        'meme-id': str(uuid.uuid4()),
        'user-id': user_id,
        'image-hash': request.form.get('image-hash'),
        'top-text': request.form.get('top-text'),
        'bottom-text': request.form.get('bottom-text'),
        'create-time': datetime.datetime.now().isoformat()
    }
    memes.put_item(data = meme)
    return jsonify( { 'meme': meme } ), 201

def top_text_pos(imagesize,textsize,margin):
    xcoord = imagesize[0]/2-textsize[0]/2
    ycoord = margin[1]
    return (xcoord,ycoord)
    
def bottom_text_pos(imagesize,textsize,margin):
    xcoord = imagesize[0]/2-textsize[0]/2
    ycoord = imagesize[1]-textsize[1]-margin[1]
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

def render_meme_image(image_hash, toptext, bottomtext, textsize):
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

@application.route('/api/v1.0/images/<string:image_hash>/render', methods = ['GET'])
def render_image(image_hash):
    toptext = request.args.get("toptext")
    bottomtext = request.args.get("bottomtext")
    textsize = int(request.args.get("textsize", "60"))
    return render_meme_image(image_hash, toptext, bottomtext, textsize)

@application.route('/api/v1.0/images', methods = ['GET', 'POST'])
def handle_images():
    if request.method == 'GET':
        return get_images();
    elif request.method == 'POST':
        return create_image();

def get_images():
    results = []
    for key in bucket.list():
        results.append( { "hash": key.name,
                          "url": "/api/v1.0/images/" + key.name + "/render" } )
    return jsonify( { "images": results } )

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
