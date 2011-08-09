from bson import json_util
from flask import Flask, request, render_template, json, redirect, url_for, abort
from pymongo.errors import OperationFailure
from pymongo.connection import Connection

conn = Connection()

def tojson(v):
    return json.dumps(v, ensure_ascii=False, indent='  ', default=json_util.default)

def fromjson(v):
    return json.loads(v, object_hook=json_util.object_hook)

def getdb_or_404(db_name):
    if db_name not in conn.database_names():
        abort(404)
    return conn[db_name]

def getcoll_or_404(db_name, coll_name):
    db = getdb_or_404(db_name)
    if coll_name not in db.collection_names():
        abort(404)
    return db[coll_name]

app = Flask(__name__)
app.jinja_env.filters['tojson'] = tojson

@app.route('/')
def index():
    dbs = conn.database_names()
    return render_template('index.html', dbs=dbs)

@app.route('/<db_name>')
def database(db_name):
    db = getdb_or_404(db_name)
    colls = [n for n in db.collection_names() if not n.startswith('system.')]
    return render_template('db.html', db_name=db_name, colls=colls)

@app.route('/<db_name>/<coll_name>')
def collection(db_name, coll_name):
    coll = getcoll_or_404(db_name, coll_name)
    objects = coll.find()
    return render_template('collection.html', objects=objects, db_name=db_name, coll_name=coll_name)

@app.route('/<db_name>/<coll_name>/add', methods=['GET', 'POST'])
def add(db_name, coll_name):
    coll = getcoll_or_404(db_name, coll_name)
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
                coll.insert(new_object, safe=True)
            except OperationFailure as e:
                error = u'Insert error: ' + unicode(e)
            else:
                return redirect(url_for('.collection', db_name=db_name, coll_name=coll_name))
    else:
        value = u''

    return render_template('edit.html', value=value, error=error, db_name=db_name, coll_name=coll_name)

@app.route('/<db_name>/<coll_name>/edit/<id>', methods=['GET', 'POST'])
def edit(db_name, coll_name, id):
    coll = getcoll_or_404(db_name, coll_name)

    id = fromjson(id)
    row = coll.find_one({'_id': id})
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
                coll.update({'_id': id}, new_object, safe=True)
            except OperationFailure as e:
                error = u'Update error: ' + unicode(e)
            else:
                return redirect(url_for('.collection', db_name=db_name, coll_name=coll_name))
    else:
        value = tojson(row)

    return render_template('edit.html', value=value, error=error, db_name=db_name, coll_name=coll_name, id=id)

@app.route('/<db_name>/<coll_name>/delete/<id>', methods=['GET', 'POST'])
def delete(db_name, coll_name, id):
    coll = getcoll_or_404(db_name, coll_name)
    id = fromjson(id)
    row = coll.find_one({'_id': id})
    if row is None:
        abort(404)

    if request.method == 'POST':
        if 'delete' in request.form:
            coll.remove({'_id': id})
        return redirect(url_for('.collection', db_name=db_name, coll_name=coll_name))

    return render_template('delete.html', value=tojson(row), db_name=db_name, coll_name=coll_name, id=id)

app.run(debug=True)
