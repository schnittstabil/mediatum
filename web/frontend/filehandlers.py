# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from functools import partial
import logging
import os
import glob

from sqlalchemy.orm.exc import NoResultFound
from core import db
from core import Node, File
import core.config as config
import core.athana as athana
from core.archive import get_archive_for_node
from contenttypes import Container
from contenttypes import Content
from contenttypes.data import Data
from schema.schema import existMetaField
from web.frontend.filehelpers import sendZipFile, splitpath, build_transferzip, node_id_from_req_path
from utils import userinput
import utils.utils
from utils.utils import getMimeType
import tempfile


logg = logging.getLogger(__name__)
q = db.query


def _send_thumbnail(thumb_type, req):
    try:
        nid = node_id_from_req_path(req)
    except ValueError:
        return 400

    if not Node.req_has_access_to_node_id(nid, u"read"):
        return 404

    # XXX: better to use scalar(), but we must ensure that we have no dupes first
    for f in q(File).filter_by(nid=nid, filetype=thumb_type):
        if os.path.isfile(f.abspath):
            return req.sendFile(f.abspath, f.mimetype)

    try:
        ntype, schema = q(Content.type, Content.schema).filter_by(id=nid).one()
    except NoResultFound:
        return 404

    for p in athana.getFileStorePaths("/img/"):
        for test in ["default_thumb_%s_%s.*" % (ntype, schema),
                     "default_thumb_%s.*" % schema,
                     "default_thumb_%s.*" % ntype]:
            fps = glob.glob(os.path.join(p, test))
            if fps:
                thumb_mimetype, thumb_type = utils.utils.getMimeType(fps[0])
                return req.sendFile(fps[0], thumb_mimetype, force=1)

    return req.sendFile(config.basedir + "/web/img/questionmark.png", "image/png", force=1)


send_thumbnail = partial(_send_thumbnail, u"thumb")
send_thumbnail2 = partial(_send_thumbnail, u"presentation")


def _send_file_with_type(filetype, mimetype, req):
    try:
        nid = node_id_from_req_path(req)
    except ValueError:
        return 400

    node = q(Content).get(nid)
    if node is None or not node.has_data_access():
        return 404

    file_query = node.files.filter_by(filetype=filetype)
    if mimetype:
        file_query.filter_by(mimetype=mimetype)

    fileobj = file_query.scalar()
    if fileobj is not None:
        return req.sendFile(fileobj.abspath, fileobj.mimetype)

    return 404


send_doc = partial(_send_file_with_type, u"document", None)
send_jpeg = partial(_send_file_with_type, u"image", u"image/jpeg")


def send_original_file(req):
    try:
        nid = node_id_from_req_path(req)
    except ValueError:
        return 400

    node = q(Content).get(nid)
    if node is None or not node.has_data_access():
        return 404

    original_filetype = node.get_original_filetype()
    original_file = node.files.filter_by(filetype=original_filetype).scalar()
    if original_file is not None:
        return req.sendFile(original_file.abspath, original_file.mimetype)

    return 404


def send_file(req):
    parts = splitpath(req.path)
    if len(parts) != 2:
        return 400

    nidstr, filename = parts
    if nidstr.endswith("_transfer.zip"):
        nidstr = nidstr[:-13]

    nid = userinput.string_to_int(nidstr)
    node = q(Data).get(nid)

    if (node is None
            or isinstance(node, Container) and not node.has_read_access()
            or isinstance(node, Content) and not node.has_data_access()):
        return 404

    def _send_attachment(filepath, mimetype):
        file_ext = os.path.splitext(filepath)[1]
        if existMetaField(node.schema, u'nodename'):
            display_file_name = u'{}{}'.format(os.path.splitext(os.path.basename(node.name))[0], file_ext)
        else:
            display_file_name = filename

        req.reply_headers["Content-Disposition"] = u'attachment; filename="{}"'.format(display_file_name).encode('utf8')
        return req.sendFile(filepath, mimetype)

    if filename is None:
        # build zip-file and return it
        with tempfile.NamedTemporaryFile() as tmpfile:
            files_written = build_transferzip(tmpfile, node)
            if files_written == 0:
                return 404
            return req.sendFile(tmpfile.name, "application/zip")

    # try full filename
    for f in node.files:
        if f.base_name == filename:
            return _send_attachment(f.abspath, f.mimetype)

    archive = get_archive_for_node(node)
    if archive:
        filepath = archive.get_local_filepath(node)
        mimetype, _ = getMimeType(filepath)
        return _send_attachment(filepath, mimetype)

    else:
        # try only extension
        file_ext = os.path.splitext(filename)[1]
        for f in node.files:
            if os.path.splitext(f.base_name)[1] == file_ext and f.filetype in ['doc', 'document', 'original', 'mp3']:
                logg.warn("serving file %s for node %s only by matched extension", f.path, node.id)
                return _send_attachment(f.abspath, f.mimetype)

    return 404


def send_attachment(req):
    try:
        nid = node_id_from_req_path(req)
    except ValueError:
        return 400

    node = q(Data).get(nid)
    if (node is None
            or isinstance(node, Container) and not node.has_read_access()
            or isinstance(node, Content) and not node.has_data_access()):
        return 404

    attachment_file = node.files.filter_by(filetype=u"attachment").first()
    if attachment_file is not None:
        # filename is attachment.zip
        sendZipFile(req, file.abspath)


def send_attfile(req):
    """send single attachment file to user"""
    parts = req.path[9:].split('/')

    if len(parts) < 2:
        return 400

    nid = userinput.string_to_int(parts[0])

    if nid is None:
        return 400

    node = q(Data).get(nid)

    # XXX: why do we want to send attachments from containers?
    if (node is None
            or isinstance(node, Container) and not node.has_read_access()
            or isinstance(node, Content) and not node.has_data_access()):
        return 404

    paths = ["/".join(parts[1:]), "/".join(parts[1:-1])]
    fileobjs = [fo for fo in node.files if fo.path in paths]

    if not fileobjs:
        return 404

    fileobj = fileobjs[0]

    if (fileobj.size > 16 * 1048576):
        req.reply_headers["Content-Disposition"] = u'attachment; filename="{}"'.format(fileobj.base_name).encode('utf8')

    return req.sendFile(fileobj.abspath, fileobj.mimetype)


def fetch_archived(req):
    try:
        nid = node_id_from_req_path(req)
    except ValueError:
        return 400

    node = q(Content).get(nid)

    archive = get_archive_for_node(node)
    if archive:
        archive.fetch_file_from_archive(node)
        req.write('done')
    else:
        msg = "archive for node not found"
        req.setStatus(404)
        req.write(msg)
        logg.warn(msg)

    db.session.commit()


def send_from_webroot(req):
    filename = config.basedir + "/web/root" + req.path
    if os.path.isfile(filename):
        return req.sendFile(filename, getMimeType(filename)[0])
    else:
        return 404
