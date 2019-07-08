# -*- coding: utf-8 -*-
import os
import logging
import time

from flask import g, Flask, render_template, request, send_file, jsonify

from contenttypes import Container, Collections
from core import db, User, Node
from core.auth import authenticate_user_credentials
from core.search import SearchQueryException
import core.config as config
from schema.schema import Metafield, Metadatatype
from web.api.auth import HTTPBasicAuth
from web.api.dto import assemble_meta_field_dto, assemble_node_dto


logg = logging.getLogger(__name__)
api_debug = config.getboolean('api.debug', False)

q = db.query
auth = HTTPBasicAuth()
app = Flask('mediaTUM api', template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))

if api_debug:
    app.debug = True
    from werkzeug.debug import DebuggedApplication
    app.wsgi_app = DebuggedApplication(app.wsgi_app, True)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/spec.yaml')
def spec():
    return render_template('spec.yaml'), 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/metafields')
@auth.login_required
def meta_fields():
    name = request.args.get('name')
    if name:
        fields = q(Metafield).filter(Metafield.name.ilike('%{}%'.format(name)))
    else:
        fields = q(Metafield).all()

    return jsonify([assemble_meta_field_dto(f) for f in fields])


@app.route('/metafields/<int:id>')
@auth.login_required
def meta_fields_get(id):
    meta_field = q(Metafield).get(id)

    if not meta_field:
        return jsonify({'error': 'Metafield(id={id}) not found.'.format(id=id)}), 404

    return jsonify(assemble_meta_field_dto(meta_field))


@app.route('/nodes')
@app.route('/nodes/<int:id>')
@auth.login_required
def containers_get(id=None):
    node = q(Collections).first() if id is None else q(Node).get(id)
    fulltext = request.args.get('fulltext', 'false') == 'true'

    if not node:
        return jsonify({'error': 'Node(id={id}) not found.'.format(id=id)}), 404

    if not node.has_read_access(user=g.user):
        return jsonify({'error': 'User(login_name={login_name}) is not authorized to read this Node(id={node_id}).'.format(login_name=g.user.login_name, node_id=node.id)}), 401

    return jsonify(assemble_node_dto(node, fulltext=fulltext)), 200


@app.route('/nodes/allchildren')
@app.route('/nodes/<int:id>/allchildren')
@auth.login_required
def node_allchildren(id=None):
    node = q(Collections).first() if id is None else q(Node).get(id)

    if not node:
        return jsonify({'error': 'Node(id={id}) not found.'.format(id=id)}), 404

    if not node.has_read_access(user=g.user):
        return jsonify({'error': 'User(login_name={login_name}) is not authorized to read this Node(id={node_id}).'.format(login_name=g.user.login_name, node_id=node.id)}), 401

    query = request.args.get('query')
    type = request.args.get('type')
    fulltext = request.args.get('fulltext', 'false') == 'true'
    include_self = request.args.get('self', 'false') == 'true'

    try:
        limit = int(request.args.get('limit', 1000))
    except ValueError:
        # athana does not like 422, use 400 instead:
        return jsonify({'error': 'request.args.limit is not an integer'}), 400

    if query:
        try:
            children = node.search(query)
        except SearchQueryException as e:
            return jsonify({'error': 'request.args.query is not valid: {message}'.format(message=e.message)}), 400
    else:
        children = node.all_children

    if type:
        children = children.filter((Node.type + '/' + Node.schema).op('~')(type))

    if limit > 0:
        children = children.limit(limit - 1 if include_self else limit)

    dtos = ([assemble_node_dto(node, fulltext=fulltext)] if include_self else []) + [
        assemble_node_dto(child, fulltext=fulltext)
        for child in children
        if child.has_read_access(user=g.user)
    ]
    return jsonify(dtos), 201


@app.route('/nodes/<int:node_id>/files/<int:file_id>')
@auth.login_required
def files_get(node_id, file_id):
    node = q(Node).get(node_id)
    if not node:
        return jsonify({'error': 'Node(id={id}) not found.'.format(id=node_id)}), 404

    if not node.has_data_access(user=g.user):
        return jsonify({'error': 'User(login_name={login_name}) is not authorized to access this Node(id={node_id}).'.format(login_name=g.user.login_name, node_id=node.id)}), 401

    file = node.files.filter_by(id=file_id).first()
    if not file:
        return jsonify({'error': 'File(id={file_id}) not found.'.format(file_id=file_id)}), 404

    return send_file(file.abspath, file.mimetype)


@app.route('/containers/<int:id>', methods=['POST'])
@auth.login_required
def containers_post(id):
    container = q(Container).get(id)
    if not container:
        return jsonify({'error': 'Container(id={id}) not found.'.format(id=id)}), 404

    if not container.has_write_access(user=g.user):
        return jsonify({'error': 'User(login_name={login_name}) is not authorized to write to this Container(id={id}).'.format(login_name=g.user.login_name, id=container.id)}), 401

    if not isinstance(request.json, dict):
        # athana does not like 422, use 400 instead:
        return jsonify({'error': 'request.data is not a JSON object.', 'request': {'data': request.data}}), 400

    attrs = request.json.get('attrs')
    type = request.json.get('type')
    schema = request.json.get('schema')

    if not isinstance(attrs, dict):
        # athana does not like 422, use 400 instead:
        return jsonify({'error': 'request.json.attrs attribute is not a JSON object.', 'request': {'json': request.json}}), 400

    if not q(Metadatatype).filter_by(name=type).first():
        # athana does not like 422, use 400 instead:
        return jsonify({'error': 'Type \'{type}\' not found.'.format(type=type)}), 400

    if not q(Metadatatype).filter_by(name=schema).first():
        # athana does not like 422, use 400 instead:
        return jsonify({'error': 'Schema \'{schema}\' not found.'.format(schema=schema)}), 400

    node = Node(name=u'', type=type, schema=schema)
    for key, value in attrs.items():
        node.set(key, value)
    node.set('creator', g.user.login_name)
    node.set('creationtime', ustr(time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time()))))

    container.children.append(node)
    db.session.commit()

    return jsonify(assemble_node_dto(node, fulltext=True)), 201
