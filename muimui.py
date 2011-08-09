from bson import json_util
from flask import Flask, request, render_template, json, redirect, url_for, abort
from pymongo.errors import OperationFailure
from pymongo.connection import Connection


URI = None
DATABASE = 'sandbox'

conn = Connection(URI)
db = conn[DATABASE]

def tojson(v):
    return json.dumps(v, ensure_ascii=False, indent='  ', default=json_util.default)

def fromjson(v):
    return json.loads(v, object_hook=json_util.object_hook)

app = Flask(__name__)
app.jinja_env.filters['tojson'] = tojson

@app.route('/')
def index():
    collections = [c for c in db.collection_names() if not c.startswith('system.')]
    return render_template('index.html', collections=collections)

@app.route('/<name>')
def collection(name):
    return render_template('collection.html', objects=db[name].find(), collection=name)

@app.route('/<name>/add', methods=['GET', 'POST'])
def add(name):
    error = None

    if request.method == 'POST' and 'value' in request.form:
        value = request.form['value']
        try:
            new_object = fromjson(value)
            if not isinstance(new_object, dict):
                raise ValueError(u'Value should be JSON dictionary')
        except Exception as e:
            error = u'Invalid JSON: ' + unicode(e)
        else:
            try:
                db[name].insert(new_object, safe=True)
            except OperationFailure as e:
                error = u'Insert error: ' + unicode(e)
            else:
                return redirect(url_for('.collection', name=name))
    else:
        value = u''

    return render_template('edit.html', value=value, error=error, collection=name)

@app.route('/<name>/edit/<id>', methods=['GET', 'POST'])
def edit(name, id):
    id = fromjson(id)
    row = db[name].find_one({'_id': id})
    if row is None:
        abort(404)

    error = None

    if request.method == 'POST' and 'value' in request.form:
        value = request.form['value']
        try:
            new_object = fromjson(value)
            if not isinstance(new_object, dict):
                raise ValueError(u'Value should be JSON dictionary')
        except Exception as e:
            error = u'Invalid JSON: ' + unicode(e)
        else:
            try:
                db[name].update({'_id': id}, new_object, safe=True)
            except OperationFailure as e:
                error = u'Update error: ' + unicode(e)
            else:
                return redirect(url_for('.collection', name=name))
    else:
        value = tojson(row)

    return render_template('edit.html', value=value, error=error, collection=name)

@app.route('/<name>/delete/<id>', methods=['GET', 'POST'])
def delete(name, id):
    id = fromjson(id)
    row = db[name].find_one({'_id': id})
    if row is None:
        abort(404)

    if request.method == 'POST':
        if 'delete' in request.form:
            db[name].remove({'_id': id})
        return redirect(url_for('.collection', name=name))

    return render_template('delete.html', value=tojson(row), collection=name)

app.run(debug=True)
