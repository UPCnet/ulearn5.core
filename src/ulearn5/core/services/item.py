# -*- coding: utf-8 -*-
import logging
from base64 import b64encode

import requests
from plone import api
from plone.app.uuid.utils import uuidToURL
from plone.restapi.services import Service
from ulearn5.core.services import (UnknownEndpoint, check_methods,
                                   check_required_params, check_roles)

from ulearn5.core.services.utils import urlBelongsToCommunity
from ulearn5.core.html_parser import HTMLParser, replaceImagePathByURL

logger = logging.getLogger(__name__)


class Item(Service):
    """
    - Endpoint: @api/item
    - Method: GET
        Required params:
            - url (str) URL of the item to retrieve.

    - Subpaths allowed: NO
    """

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request
        self.url = kwargs.get('url', None)

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if subpath:
            return UnknownEndpoint(f'Unknown sub-endpoint: {"/".join(subpath)}')

        return self.reply()

    @check_roles(roles=['Member', 'Manager', 'Api'])
    @check_required_params(params=['url'])
    @check_methods(methods=['GET'])
    def reply(self):
        """ Expanded bitly links """
        request_url = self.url
        expanded = self.get_expanded_url(request_url)
        portal = api.portal.get()
        portal_url = portal.absolute_url()
        results = []

        if portal_url in expanded:
            item_path = self.get_item_path(expanded, portal_url)
            item = self.is_item_still_there(item_path)

            if item:
                result = self.process_item(item, expanded)
                results.append(result)
        else:
            results.append(self.process_external_url(expanded))

        return results

    def get_expanded_url(self, request_url):
        session = requests.Session()
        resp = session.head(request_url, allow_redirects=True)
        expanded = resp.url.split('came_from=')[1].replace(
            '%3A', ':') if 'came_from' in resp.url else resp.url
        if 'resolveuid' in expanded:
            expanded = uuidToURL(expanded.split('/')[-1])

        return expanded

    def get_item_path(self, expanded, portal_url):
        item_id = expanded.split(portal_url)[1][1:]
        mountpoint_id = self.context.getPhysicalPath()[1]
        if mountpoint_id == self.context.id:
            item_path = '/'.join(api.portal.get().getPhysicalPath()) + '/' + item_id
        else:
            item_path = '/' + mountpoint_id + '/' + api.portal.get().id + '/' + item_id
        if item_path[-5:] == '/view':
            item_path = item_path.replace('/view', '')

        return item_path

    def is_item_still_there(self, item_path):
        try:
            # Check if value deleted / moved --> NOT FOUND!
            item = api.content.find(path=item_path, depth=0)[0].getObject()
            return item
        except:
            return False

    def process_item(self, item, expanded):
        """ Process the item based on its portal type """
        text = image = image_caption = raw_image = raw_file = content_type = ''
        type_when_follow_url = item.portal_type
        external_url = False
        belong = urlBelongsToCommunity(self.url, expanded)

        if item.portal_type == 'News Item':
            text, image, image_caption, raw_image = self.process_news_item(item)
        elif item.portal_type == 'Image':
            image, raw_image, content_type = self.process_image(item)
        elif item.portal_type == 'Document':
            text = self.process_document(item)
        elif item.portal_type == 'Link':
            text, type_when_follow_url, external_url = self.process_link(item)
        elif item.portal_type == 'Event':
            text = self.process_event(item)
        elif item.portal_type in ['File', 'ulearn.video']:
            raw_file, content_type = self.process_file(item)
        elif item.portal_type == 'ExternalContent':
            expanded = f"{item.absolute_url()}/@@download/{item.filename}"
            external_url = True

        return {
            'absolute_url': expanded,
            'content_type': content_type,
            'description': item.Description(),
            'external_url': external_url,
            'id': item.id,
            'image': image,
            'image_caption': image_caption,
            'is_community_belonged': belong,
            'portal_type': item.portal_type,
            'raw_file': raw_file,
            'raw_image': raw_image,
            'title': item.Title(),
            'text': text,
            'type_when_follow_url': type_when_follow_url,
            'uid': item.UID(),
        }

    def process_news_item(self, item):
        text = replaceImagePathByURL(item.text.raw) if item.text else None
        text = HTMLParser(text) if text else None
        image = item.image.filename if item.image else None
        image_caption = item.image_caption
        raw_image = (
            b64encode(item.image.data).decode('utf-8')
            if item.image and item.image.data
            else None
        )
        return text, image, image_caption, raw_image

    def process_image(self, item):
        image = item.image.filename
        raw_image = (
            b64encode(item.image.data).decode('utf-8')
            if item.image and item.image.data
            else None
        )
        content_type = item.image.contentType
        return image, raw_image, content_type

    def process_document(self, item):
        text = replaceImagePathByURL(item.text.raw) if item.text else None
        text = HTMLParser(text) if text else None
        return text

    def process_link(self, item):
        if 'resolveuid' in item.remoteUrl:
            uid = item.remoteUrl.split('/')[-1]
            next_obj = api.content.get(UID=uid)
            text = next_obj.absolute_url()
            type_when_follow_url = next_obj.Type()
            external_url = False
        else:
            text = item.remoteUrl
            type_when_follow_url = item.portal_type
            external_url = True
        return text, type_when_follow_url, external_url

    def process_event(self, item):
        text = replaceImagePathByURL(item.text.raw) if item.text else None
        text = HTMLParser(text) if text else None
        return text

    def process_file(self, item):
        raw_file = (
            b64encode(item.file.data).decode('utf-8')
            if item.file and item.file.data
            else None
        )
        content_type = item.file.contentType
        return raw_file, content_type

    def process_external_url(self, expanded):
        return {
            'absolute_url': expanded,
            'content_type': '',
            'description': '',
            'external_url': True,
            'id': '',
            'image': '',
            'image_caption': '',
            'is_community_belonged': False,
            'portal_type': '',
            'raw_file': '',
            'raw_image': '',
            'title': '',
            'text': '',
            'uid': '',
        }
