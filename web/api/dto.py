from contenttypes import Data
from core.webconfig import node_url

import core.config as config


host_schema = 'https' if config.getboolean('host.ssl', True) else 'http'
host_name = config.get('host.name', '')
host_port = config.getint('host.port', '443' if config.getboolean('host.ssl', True) else '80')

if host_name:
    if (host_schema == 'https' and host_port == 443) or (host_schema == 'http' and host_port == 80):
        base_url = '{schema}://{name}'.format(schema=host_schema, name=host_name)
    else:
        base_url = '{schema}://{name}:{port}'.format(schema=host_schema, name=host_name, port=host_port)
else:
    base_url = ''


def url(endpoint, *args, **kwargs):
    return '{base_url}{endpoint}'.format(base_url=base_url, endpoint=endpoint).format(*args, **kwargs)


def sanitize_meta_field_value_list(value_list):
    # TODO find the service which provides this functionality:
    return [v.lstrip('*').strip() for v in value_list]


def assemble_meta_field_dto(meta_field):
    return {
        'id': meta_field.id,
        'name': meta_field.name,
        'valueList': sanitize_meta_field_value_list(meta_field.getValueList()),
        '_links': {
            'self': {
                'href': url('/api/metafields/{id}', id=meta_field.id)
            }
        }
    }


def assemble_node_dto(node, fulltext=False):
    dto = {
        'id': node.id,
        'name': node.name,
        'type': node.type,
        'schema': node.schema,
        'attrs': node.attrs,
        '_links': {
            'related': [],
            'self': {
                'href': url('/api/nodes/{id}', id=node.id),
            },
            'up': [
                {
                    'href': url('/api/nodes/{id}', id=parent.id),
                }
                for parent in node.parents
            ],
        }
    }

    if fulltext:
        dto['fulltext'] = node.fulltext

    if isinstance(node, Data):
        dto['_links']['related'].append({
            'name': node.schema,
            'type': 'text/html',
            'title': node.getLabel(),
            'href': url(node_url(node.id)),
        })

    if node.files:
        for file in node.files:
            file_dto = {
                'name': file.filetype,
                'type': file.mimetype,
                'title': file.base_name,
                'href': url('/api/nodes/{node_id}/files/{file_id}', node_id=node.id, file_id=file.id),
            }
            dto['_links']['related'].append(file_dto)

    return dto
