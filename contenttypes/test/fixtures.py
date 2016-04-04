# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from functools import partial
import os
from pytest import fixture
import pytest
from core import File
from contenttypes.test.factories import VideoFactory, ImageFactory
from schema.test.factories import MetadatatypeFactory
from contenttypes.test import TEST_IMAGE_PATHS, TEST_VIDEO_PATH
from core.config import resolve_datadir_path


@fixture
def patch_get_iptc_tags(monkeypatch):
    import lib.iptc.IPTC
    monkeypatch.setattr(lib.iptc.IPTC, "get_iptc_values", lambda *a, **k: {})


def _image_fixture_proto(mime_subtype, session):
    img_path = TEST_IMAGE_PATHS[mime_subtype]
    img_fullpath = resolve_datadir_path(img_path)
    if not os.path.exists(img_fullpath):
        pytest.skip(u"test image not found at " + img_fullpath)

    image = ImageFactory()
    MetadatatypeFactory(name=u"test")
    mimetype = u"image/" + mime_subtype
    image.files.append(File(path=img_path, filetype=u"original", mimetype=mimetype))
    image._test_mimetype = mimetype
    return image


def make_image_fixture(mime_subtype):
    return fixture(partial(_image_fixture_proto, mime_subtype))


image_tiff = make_image_fixture("tiff")
image_jpeg = make_image_fixture("jpeg")
image_png = make_image_fixture("png")
image_svg = make_image_fixture("svg+xml")
image_gif = make_image_fixture("gif")


@fixture(params=["tiff", "jpeg", "png", "svg+xml", "gif"])
def image(request, session):
    return _image_fixture_proto(request.param, session)


@fixture
def video(session):
    video = VideoFactory()
    MetadatatypeFactory(name=u"test")
    video.files.append(File(path=TEST_VIDEO_PATH, filetype=u"video", mimetype=u"video/mp4"))
    return video
