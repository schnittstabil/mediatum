"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import re
import sys
from functools import partial
import logging
import time
from warnings import warn
import humanize
from mediatumtal import tal

from core import Node, db
from core.database.postgres.node import children_rel
import core.config as config
from core.translation import lang, t
from core.styles import getContentStyles
from core.transition.postgres import check_type_arg_with_schema
from export.exportutils import runTALSnippet, default_context
from schema.schema import getMetadataType, VIEW_DATA_ONLY, VIEW_HIDE_EMPTY, SchemaMixin, Metafield, Metadatatype, Mask
from web.services.cache import date2string as cache_date2string
from utils.utils import highlight
from core.transition.globals import request
from core.node import get_node_from_request_cache

logg = logging.getLogger(__name__)


# for TAL templates from mask cache
context = default_context.copy()
### XXX: does this work without hostname? Can we remove this?
context['host'] = "http://" + config.get("host.name", "")


def get_maskcache_report(maskcache_accesscount):
    maskcache_msg = '| cache initialized %s\r\n|\r\n' % cache_date2string(time.time(), '%04d-%02d-%02d-%02d-%02d-%02d')
    s = maskcache_msg + "| %d lookup keys in cache, total access count: %d\r\n|\r\n"
    total_access_count = 0
    for k, v in sorted(maskcache_accesscount.items()):
        s += u"| {} : {}\r\n".format(k.ljust(60, '.'),
                                     unicode(v).rjust(8, '.'))
        total_access_count += v
    return s % (len(maskcache_accesscount), total_access_count)


def flush_maskcache(req=None):
    from core import users
    global maskcache, maskcache_accesscount, maskcache_msg
    logg.info("going to flush maskcache, content is: \r\n%s", get_maskcache_report())
    maskcache = {}
    maskcache_accesscount = {}
    if req:
        user = users.getUserFromRequest(req)
        logg.info("flush of masks cache triggered by user %s with request on '%s'", user.login_name, req.path)

        sys.stdout.flush()
    maskcache_msg = '| cache last flushed %s\r\n|\r\n' % cache_date2string(time.time(), '%04d-%02d-%02d-%02d-%02d-%02d')


def make_lookup_key(node, language=None, labels=True):
    languages = config.languages
    if language is None:
        language = languages[0]
    flaglabels = 'nolabels'
    if labels:
        flaglabels = 'uselabels'

    if language in languages:
        return "%s/%s_%s_%s" % (node.type, node.schema, language, flaglabels)
    else:
        return "%s/%s_%s_%s" % (node.type, node.schema, languages[0], flaglabels)


def get_maskcache_entry(lookup_key, maskcache, maskcache_accesscount):
    try:
        res = maskcache[lookup_key]
        maskcache_accesscount[lookup_key] += 1
    except:
        res = None
    return res


get_mask = partial(get_node_from_request_cache, Mask)
get_metafield = partial(get_node_from_request_cache, Metafield)


class Data(Node):

    """Abstract base class for all node classes which can be viewed / fetched by frontend / api users.
    Methods in this class are concerned with viewing / representing the contents of the data node.

    In other words: Node classes which don't inherit from this class are seen as internal 'system types'.
    """

    content_children = children_rel("Content")

    @classmethod
    def get_all_datatypes(cls):
        """Returns all known subclasses of cls except `Collections` and `Home`"""
        return cls.get_all_subclasses(filter_classnames=("collections", "home"))

    @classmethod
    def getTypeAlias(cls):
        """Returns an identifier for this content type, always lower case.
        By default, the class name in lowercase is used.
        """
        return cls.__name__.lower()

    @classmethod
    def get_original_filetype(cls):
        """Returns the File.filetype value for associated files that represent the "original" file
        """
        return "original"

    @classmethod
    def get_upload_filetype(cls):
        """Returns the File.filetype value that will be used by the editor for uploaded files.
        """
        return cls.__name__.lower()

    @classmethod
    def isContainer(cls):
        warn("use isinstance(node, Container) or issubclass(nodecls, Container)", DeprecationWarning)
        return 0

    @classmethod
    def get_default_edit_menu_tabs(cls):
        return "menuglobals()"

    @classmethod
    def get_default_edit_tab(cls):
        """Returns the editor tag that should be displayed when visiting a node.
        Defaults to the preview view
        """
        return "view"

    @property
    def has_upload_file(self):
        """Is True when the node has a file with type `self.get_upload_filetype`.
        """
        # XXX: should be scalar(), but we don't really try to avoid duplicates atm
        return self.files.filter_by(filetype=self.get_upload_filetype()).first() is not None

    def show_node_big(self, req, template="", macro=""):
        if template == "":
            styles = getContentStyles("bigview", contenttype=self.type)
            if len(styles) >= 1:
                template = styles[0].getTemplate()

        return req.getTAL(template, self._prepareData(req), macro)

    def show_node_image(self, language=None):
        return tal.getTAL(
            "contenttypes/data.html", {'children': self.getChildren().sort_by_orderpos(), 'node': self}, macro="show_node_image")


    def show_node_text(self, words=None, language=None, separator="", labels=0):
        return self.show_node_text_deep(words=words, language=language, separator=separator, labels=labels)


    def show_node_text_deep(self, words=None, language=None, separator="", labels=0):


        def render_mask_template(node, mask, field_descriptors, words=None, separator="", skip_empty_fields=True):
            
            res = []
             
            for node_attribute, fd in field_descriptors:
                metafield_type = fd['metafield_type']
                maskitem_type = fd['maskitem_type']
                metafield_id = fd["metafield_id"]
                metafield = get_metafield(metafield_id)
                
                if metafield is None:
                    raise ValueError("metafield with ID {} not found!".format(metafield_id))
                
                metatype = fd["metatype"]
                
                if metafield_type in ['date', 'url', 'hlist']:
                    value = node.get_special(node_attribute)
                    try:
                        value = metatype.getFormatedValue(metafield, node, language=language, mask=mask)[1]
                    except:
                        value = metatype.getFormatedValue(metafield, node, language=language)[1]

                elif metafield_type in ['field']:
                    if maskitem_type in ['hgroup', 'vgroup']:
                        _sep = ''
                        if maskitem_type == 'hgroup':
                            fd['unit'] = ''  # unit will be taken from definition of the hgroup
                            use_label = False
                        else:
                            use_label = True
                        value = getMetadataType(maskitem_type).getViewHTML(
                                                                         fd['field'],  # field
                                                                         [node],  # nodes
                                                                         0,  # flags
                                                                         language=language,
                                                                         mask=mask, use_label=use_label)
                else:
                    value = node.get_special(node_attribute)

                    if hasattr(metatype, "language_snipper"):
                        if (metafield.get("type") == "text" and metafield.get("valuelist") == "multilingual") \
                            or \
                           (metafield.get("type") in ['memo', 'htmlmemo'] and metafield.get("multilang") == '1'):
                            value = metatype.language_snipper(value, language)

                    if value.find('&lt;') >= 0:
                        # replace variables
                        for var in re.findall(r'&lt;(.+?)&gt;', value):
                            if var == "att:id":
                                value = value.replace("&lt;" + var + "&gt;", unicode(node.id))
                            elif var.startswith("att:"):
                                val = node.get_special(var[4:])
                                if val == "":
                                    val = "____"

                                value = value.replace("&lt;" + var + "&gt;", val)
                        value = value.replace("&lt;", "<").replace("&gt;", ">")

                    if value.find('<') >= 0:
                        # replace variables
                        for var in re.findall(r'\<(.+?)\>', value):
                            if var == "att:id":
                                value = value.replace("<" + var + ">", unicode(node.id))
                            elif var.startswith("att:"):
                                val = node.get_special(var[4:])
                                if val == "":
                                    val = "____"

                                value = value.replace("&lt;" + var + "&gt;", val)
                        value = value.replace("&lt;", "<").replace("&gt;", ">")

                    if value.find('tal:') >= 0:
                        context['node'] = node
                        value = runTALSnippet(value, context)

                    # don't escape before running TAL
                    if (not value) and fd['default']:
                        default = fd['default']
                        if fd['default_has_tal']:
                            context['node'] = node
                            value = runTALSnippet(default, context)
                        else:
                            value = default


                if skip_empty_fields and not value:
                    continue

                if fd["unit"]:
                    value = value + " " + fd["unit"]
                if fd["format"]:
                    value = fd["format"].replace("<value>", value)
                if words:
                    value = highlight(value, words, '<font class="hilite">', "</font>")
                res.append(fd["template"] % value)
                
            return separator.join(res)

        if not separator:
            separator = "<br/>"

        lookup_key = make_lookup_key(self, language, labels)

        # if the lookup_key is already in the cache dict: render the cached mask_template
        # else: build the mask_template


        if not 'maskcache' in request.app_cache:
            request.app_cache['maskcache'] = {}
            request.app_cache['maskcache_accesscount'] = {}

        if lookup_key in request.app_cache['maskcache']:
            mask_id, field_descriptors = request.app_cache['maskcache'][lookup_key]
            mask = get_mask(mask_id)
            
            if mask is None:
                raise ValueError("mask for cached ID {} not found".format(mask_id))

            res = render_mask_template(self, mask_id, field_descriptors, words=words, separator=separator)
            request.app_cache['maskcache_accesscount'][lookup_key] = request.app_cache['maskcache_accesscount'].get(lookup_key, 0) + 1
            #print '--------->', self

        else:
            mask = self.metadatatype.get_mask(u"nodesmall")
            for m in self.metadatatype.filter_masks(u"shortview", language=language):
                mask = m

            if mask:
                fields = mask.getMaskFields(first_level_only=True)
                ordered_fields = sorted([(f.orderpos, f) for f in fields])
                field_descriptors = []
                
                for _, maskitem in ordered_fields:
                    fd = {}  # field descriptor
                    fd['maskitem_id'] = maskitem.id
                    fd['maskitem_type'] = maskitem.get('type')
                    fd['format'] = maskitem.getFormat()
                    fd['unit'] = maskitem.getUnit()
                    fd['label'] = maskitem.getLabel()

                    metafield = maskitem.getField()
                    default = maskitem.getDefault()
                    fd['default'] = default
                    fd['default_has_tal'] = (default.find('tal:') >= 0)

                    metafield_type = metafield.get('type')
                    
                    fd['metafield_type'] = metafield_type
                    fd['metafield_id'] = metafield.id

                    t = getMetadataType(metafield_type)
                    fd['metatype'] = t

                    def getNodeAttributeName(maskitem):
                        metafields = maskitem.children.filter_by(type=u"metafield").all()
                        if len(metafields) != 1:
                            # this can only happen in case of vgroup or hgroup
                            logg.error("maskitem %s has zero or multiple metafield child(s)", maskitem.id)
                            return maskitem.name
                        return metafields[0].name

                    node_attribute = getNodeAttributeName(maskitem)
                    fd['node_attribute'] = node_attribute

                    def build_field_template(field_descriptor):
                        if labels:
                            template = "<b>" + field_descriptor['label'] + ":</b> %s"
                        else:
                            if field_descriptor['node_attribute'].startswith("author"):
                                template = '<span class="author">%s</span>'
                            elif field_descriptor['node_attribute'].startswith("subject"):
                                template = '<b>%s</b>'
                            else:
                                template = "%s"
                        return template

                    template = build_field_template(fd)

                    fd['template'] = template
                    long_field_descriptor = (node_attribute, fd)
                    field_descriptors.append(long_field_descriptor)

                request.app_cache['maskcache'][lookup_key] = (mask.id, field_descriptors)
                request.app_cache['maskcache_accesscount'][lookup_key] = 0
                res = render_mask_template(self, mask, field_descriptors, words=words, separator=separator)

            else:
                res = '&lt;smallview mask not defined&gt;'

        return res

    def get_name(self):
        return self.name

    def getTechnAttributes(self):
        return {}

    def has_object(self):
        return False

    def getFullView(self, language):
        """Gets the fullview mask for the given `language`.
        If no matching language mask is found, return a mask without language specification or None.
        :rtype: Mask
        """

        lang_mask = self.metadatatype.filter_masks(masktype=u"fullview", language=language).first()

        if lang_mask is not None:
            return lang_mask
        else:
            return self.metadatatype.filter_masks(masktype=u"fullview").first()

    @classmethod
    def get_sys_filetypes(cls):
        return []

    def getLabel(self, lang=None):
        return self.name


def _get_node_metadata_html(node, req):
    """Renders HTML data for displaying metadata using the the fullview mask.
    :rtype: unicode
    """
    mask = node.getFullView(lang(req))
    if mask is not None:
        return mask.getViewHTML([node], VIEW_HIDE_EMPTY, lang(req))  # hide empty elements
    else:
        return t(req, "no_metadata_to_display")


def child_node_url(child_id, **kwargs):
    """XXX: this shouldn't be here, child display should not be a responsibility of content types!"""
    from core.webconfig import node_url
    from core.transition import request
    params = {k: v for k, v in request.args.items()}
    if "show_id" in params:
        params["show_id"] = child_id
    else:
        params["id"] = child_id

    params.update(kwargs)
    return node_url(**params)


def prepare_node_data(node, req):
    """Prepare data needed for displaying this object.
    :returns: representation dictionary
    :rtype: dict
    """

    if node.get('deleted') == 'true':
        # If this object is marked as deleted version, render the active version instead.
        active_version = node.getActiveVersion()
        data = prepare_node_data(active_version, req)
        data["deleted"] = True
        return data

    data = {}
    data["deleted"] = False
    data["metadata"] = _get_node_metadata_html(node, req)
    data['node'] = node
    data['children'] = node.children.filter_read_access().all()
    # XXX: this is a hack, remove child display from contenttypes!
    data['child_node_url'] = child_node_url
    data['path'] = req.params.get("path", "")
    return data


class Content(Data, SchemaMixin):

    """(Abstract) base class for all content node types.
    """


@check_type_arg_with_schema
class Other(Content):

    def _prepareData(self, req):
        obj = prepare_node_data(self, req)
        if obj["deleted"]:
            # no more processing needed if this object version has been deleted
            # rendering has been delegated to current version
            return obj

        obj["naturalsize"] = humanize.filesize.naturalsize
        return obj
