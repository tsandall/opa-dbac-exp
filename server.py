#!/usr/bin/env bash

import sqlite3
import base64
import json

import flask
from flask_bootstrap import Bootstrap

import opa

app = flask.Flask(__name__, static_url_path='/static')
Bootstrap(app)


@app.route("/api/posts", methods=["GET"])
def api_list_posts():
    return flask.jsonify(list_posts())


def list_posts():
    decision = opa.query(
        input={
            'method': 'GET',
            'path': ['posts'],
            'subject': make_subject(),
        },
        unknowns=['posts'])
    if not decision.allow:
        return []
    sql = ''
    if isinstance(decision.sql, opa.SQLWherePredicate):
        sql = ' WHERE ' + decision.sql.sql()
        opa.pp_sql(decision.sql)
        print sql
    result = query_db('SELECT * FROM posts' + sql)
    return result


@app.route('/')
def index():
    kwargs = {
        'username': flask.request.cookies.get('user', ''),
        'posts': list_posts(),
    }
    if kwargs['username'] in USERS:
        kwargs['user'] = USERS[kwargs['username']]
    return flask.render_template('index.html', **kwargs)


@app.route('/login', methods=['POST'])
def login():
    user = flask.request.values.get('username')
    response = app.make_response(flask.redirect(flask.request.referrer))
    response.set_cookie('user', user)
    if user in USERS:
        for c in COOKIES:
            if c in USERS[user]:
                response.set_cookie(c, base64.b64encode(
                    json.dumps(USERS[user][c])))
    return response


@app.route('/logout', methods=['GET'])
def logout():
    response = app.make_response(flask.redirect(flask.request.referrer))
    response.set_cookie('user', '', expires=0)
    for c in COOKIES:
        response.set_cookie(c, '', expires=0)
    return response


def make_subject():
    subject = {}
    user = flask.request.cookies.get('user', '')
    if user:
        subject['user'] = user
    for c in COOKIES:
        v = flask.request.cookies.get(c, '')
        if v:
            subject[c] = json.loads(base64.b64decode(v))
    return subject


def get_db():
    db = getattr(flask.g, '_database', None)
    if db is None:
        db = flask.g._database = sqlite3.connect('test.db')
    db.row_factory = make_dicts
    return db


@app.teardown_appcontext
def close_connection(e):
    db = getattr(flask.g, '_database', None)
    if db is not None:
        db.close()


def init_schema():
    db = get_db()
    c = db.cursor()
    c.execute('DROP TABLE IF EXISTS posts')
    c.execute(POSTS_TABLE)
    db.commit()


def pump_db():
    db = get_db()
    c = db.cursor()
    for post in POSTS:
        keys = '(' + ','.join(POST_KEYS) + ')'
        values = '(' + ','.join(['?'] * len(POST_KEYS)) + ')'
        stmt = 'INSERT INTO posts {} VALUES {}'.format(keys, values)
        c.execute(stmt, [str(post[k]) for k in POST_KEYS])
    db.commit()


def init_db():
    with app.app_context():
        init_schema()
        pump_db()


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))


POSTS_TABLE = """CREATE TABLE posts (
    name TEXT PRIMARY KEY
    , author TEXT
    , content TEXT
    , department TEXT
)"""

POST_KEYS = [
    'name',
    'author',
    'content',
    'department',
]

POSTS = [
    {
        'name': 'Personalization Updated to v2.1',
        'author': 'bob',
        'department': 'dev',
        'content': 'Leverage agile frameworks to provide a robust synopsis for high level overviews. Iterative approaches to corporate strategy foster collaborative thinking to further the overall value proposition. Organically grow the holistic world view of disruptive innovation via workplace diversity and empowerment.',
    },
    {
        'name': 'Critical Vulnerability in Y2K patch (CVE-2018-DEADBEEF)',
        'author': 'bob',
        'department': 'sec',
        'content': 'Bring to the table win-win survival strategies to ensure proactive domination. At the end of the day, going forward, a new normal that has evolved from generation X is on the runway heading towards a streamlined cloud solution. User generated content in real-time will have multiple touchpoints for offshoring.',
    },
    {
        'name': 'Blockchain Service Mesh deployed',
        'author': 'alice',
        'department': 'dev',
        'content': 'Capitalize on low hanging fruit to identify a ballpark value added activity to beta test. Override the digital divide with additional clickthroughs from DevOps. Nanotechnology immersion along the information highway will close the loop on focusing solely on the bottom line.'
    },
    {
        'name': 'Quantum Gigaflux encountering errors',
        'author': 'alice',
        'department': 'dev',
        'content': 'Collaboratively administrate turnkey channels whereas virtual e-tailers. Objectively seize scalable metrics whereas proactive e-services. Seamlessly empower fully researched growth strategies and interoperable internal or "organic" sources.',
    },
    {
        'name': 'Missing printer',
        'author': 'charlie',
        'department': 'company',
        'content': 'Objectively innovate empowered manufactured products whereas parallel platforms. Holisticly predominate extensible testing procedures for reliable supply chains. Dramatically engage top-line web services vis-a-vis cutting-edge deliverables.',
    },
    {
        'name': 'Scary results from internal pay gap study',
        'author': 'charlie',
        'department': 'hr',
        'content': 'Podcasting operational change management inside of workflows to establish a framework. Taking seamless key performance indicators offline to maximise the long tail. Keeping your eye on the ball while performing a deep dive on the start-up mentality to derive convergence on cross-platform integration.',
    },
    {
        'name': 'Loud keyboards considered harmful',
        'author': 'charlie',
        'department': 'company',
        'content': 'Proactively envisioned multimedia based expertise and cross-media growth strategies. Seamlessly visualize quality intellectual capital without superior collaboration and idea-sharing. Holistically pontificate installed base portals after maintainable products.',
    }
]

COOKIES = [
    'departments',
]

USERS = {
    "bob": {
        "departments": ["sec", "dev"],
    },
    "alice": {
        "departments": ["dev"],
    },
    "charlie": {
        "departments": ["hr"],
    }
}

if __name__ == '__main__':
    init_db()
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True)
