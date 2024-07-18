# -*- coding: utf-8 -*-
import re

from bs4.element import Tag, NavigableString
from bs4 import BeautifulSoup

from Acquisition import aq_inner

from plone import api
from plone.app.layout.navigation.root import getNavigationRootObject
from ulearn5.core.content.community import ICommunity


def getCommunityNameFromObj(self, value):
    portal_state = self.context.unrestrictedTraverse('@@plone_portal_state')
    root = getNavigationRootObject(self.context, portal_state.portal())
    physical_path = value.getPhysicalPath()
    relative = physical_path[len(root.getPhysicalPath()):]
    for i in range(len(relative)):
        now = relative[:i + 1]
        obj = aq_inner(root.unrestrictedTraverse(now))
        if (ICommunity.providedBy(obj)):
            return obj.title
    return ''


def replaceImagePathByURL(msg):
    srcs = re.findall('src="([^"]+)"', msg)

    # Transformamos imagenes internas
    uids = re.findall(r"resolveuid/(.*?)/@@images", msg)
    for i in range(len(uids)):
        thumb_url = api.content.get(UID=uids[i]).absolute_url() + '/thumbnail-image'
        plone_url = srcs[i]
        msg = re.sub(plone_url, thumb_url, msg)

    # Transformamos imagenes contra la propia web
    images = re.findall(r"/@@images/.*?\"", msg)
    for i in range(len(images)):
        msg = re.sub(images[i], '/thumbnail-image"', msg)

    return msg


ATTRS_TO_REMOVE = [
    'lang', 'language', 'onmouseover', 'onmouseout', 'script', 'style', 'font',
    'dir', 'face', 'size', 'color', 'style', 'class', 'width', 'height', 'hspace',
    'border', 'valign', 'align', 'background', 'bgcolor', 'text', 'link', 'vlink',
    'alink', 'cellpadding', 'cellspacing']

TAGS_TO_REMOVE = [
    "aside", "audio", "bdo", "big", "canvas", "col", "colgroup",
    "command", "datalist", "dd", "del", "details", "dfn", "dialog", "dl",
    "dt", "footer", "head", "header", "hgroup", "ins", "kbd", "keygen",
    "map", "mark", "meter", "nav", "output", "progress", "rp", "rt",
    "ruby", "samp", "sub", "sup", "var", "video", "script"]

# These are empty elements, but they are relevant for the visualization of the html
TAGS_TO_KEEP = ["br", "iframe", "img", "input"]


def HTMLParser(html):
    soup = BeautifulSoup(html, "html.parser")

    """ Remove specific tags """
    for tag_name in TAGS_TO_REMOVE:
        tags = soup.find_all(tag_name)
        for TAG in tags:
            TAG.decompose()

    """ Remove useless attrs """
    for tag in soup.find_all():
        for attr in list(tag.attrs):
            if attr in ATTRS_TO_REMOVE:
                del tag[attr]

    """ Remove empty tags. Separated from the other loop for readability """
    for tag in soup.find_all():
        remove_empty_tags(tag)

    try:
        return soup.prettify()
    except:
        return None


def remove_empty_tags(el):
    if el.can_be_empty_element:
        return

    if (not el.contents or is_whitespace_content(el.contents)) and el.name not in TAGS_TO_KEEP:
        if el.parent:
            parent = el.parent
            el.decompose()
            remove_empty_tags(parent)
            return

        el.decompose()
        return

    for child in el.children:
        if isinstance(child, Tag):
            remove_empty_tags(child)


def is_whitespace_content(content):
    return all(isinstance(item, NavigableString) and not item.strip() for item in content)
