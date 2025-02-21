# -*- coding: utf-8 -*-
import logging
from datetime import datetime

import requests
from lxml import html
from plone import api
from plone.app.contenttypes.behaviors.richtext import IRichText
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobImage
from plone.restapi.services import Service
from ulearn5.core.services import (MethodNotAllowed, ObjectNotFound,
                                   UnknownEndpoint, check_methods,
                                   check_required_params)
from ulearn5.core.services.utils import lookup_new, show_news_in_app

# from ulearn5.core.formatting import formatMessageEntities
# from ulearn5.core.html_parser import (HTMLParser, getCommunityNameFromObj,
#                                       replaceImagePathByURL)

logger = logging.getLogger(__name__)


class New(Service):
    """
    - Endpoint: @api/news/{newid}
    - Method: GET
        Optional params:
            - absolute_url (str): Path
    - Method: POST
        Required params:
            - title (str)
            - description (str)
            - body (str)
            - start (str)
        Optional params:
            - end (str)
            - imgUrl

    - Subpaths allowed: NO
    """

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request
        self.news_item_id = kwargs.get('news_item_id', None)

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if subpath:
            return UnknownEndpoint(f'Unknown sub-endpoint: {"/".join(subpath)}')

        return self.reply()

    @check_methods(methods=['GET', 'POST'])
    def reply(self):
        method = self.request.get('method')
        if method == 'GET':
            return self.reply_get()
        elif method == 'POST':
            return self.reply_post()

        raise MethodNotAllowed(f"Unknown method: {method}")

    def reply_get(self):
        if show_news_in_app:
            default_path = self.get_default_path()

            news_item = lookup_new({
                'portal_type': 'News Item',
                'path': default_path,
                'id': self.news_item_id
            })

            if not news_item:
                raise ObjectNotFound(f'News Item with ID {self.news_item_id} not found')

            news_item_info = self.process_news_item(news_item)
            return {"data": news_item_info, "code": 200}

        else:
            return {"message": "Show in App is not enabled on this site", "code": 404}

    def get_default_path(self):
        mountpoint_id = self.context.getPhysicalPath()[1]
        portal = api.portal.get()
        portal_id = portal.id
        physical_path = '/'.join(portal.getPhysicalPath())

        if 'absolute_url' in self.request.form:
            absolute_url = self.request.form['absolute_url']
            base_path = '/'.join(absolute_url.split('/')[:-1])
        else:
            base_path = f'{physical_path}/news'

        if mountpoint_id != self.context.id:
            base_path = f'/{mountpoint_id}/{portal_id}/{base_path.lstrip("/")}'

        return base_path

    def process_news_item(self, news_item):
        date = self.process_date(news_item)
        text = self.process_text(news_item)
        filename, contentType, raw_image = self.process_image(news_item)
        community_name = getCommunityNameFromObj(self.context, news_item)

        return {
            'title': news_item.title,
            'id': news_item.id,
            'description': news_item.description,
            'path': news_item.getURL(),
            'url_site': api.portal.get().absolute_url(),
            'absolute_url': news_item.absolute_url_path(),
            'text': text,
            'filename': filename,
            'caption': news_item.image_caption,
            'is_inapp': getattr(news_item, 'is_inapp', None),
            'is_outoflist': getattr(news_item, 'is_outoflist', None),
            'is_flash': getattr(news_item, 'is_flash', None),
            'is_important': getattr(news_item, 'is_important', None),
            'effective_date': date,
            'creators': news_item.creators,
            'raw_image': raw_image,
            'content_type': contentType,
            'community': community_name
        }

    def process_date(self, value):
        if getattr(value, 'effective_date', None):
            return value.effective_date.strftime("%d/%m/%Y")

        return value.creation_date.strftime("%d/%m/%Y")

    def process_text(self, item):
        if getattr(item, 'text', None):
            text = formatMessageEntities(
                html.tostring(
                    html.fromstring(item.text.output)
                )
            )
            if text:
                text = replaceImagePathByURL(text)
                return HTMLParser(text)

        return None

    def process_image(self, item):
        filename = None
        contentType = None
        raw_image = None

        if getattr(item, 'image', None):
            filename = item.image.filename
            contentType = item.image.contentType
            raw_image = item.absolute_url() + '/thumbnail-image'

        return filename, contentType, raw_image

    @check_required_params(params=['title', 'description', 'body', 'start'])
    def reply_post(self):
        image = self.get_image_data()
        news_item = lookup_new({'id': self.news_item_id})
        if news_item:
            result = self.update_news_item(news_item, image)
            res = f'News Item {result.id} updated'
            code = 200
        else:
            result = self.create_news_item(image)
            res = f'News Item {result.id} created'
            code = 201
        return {"message": res, "code": code}

    def get_image_data(self):
        image = self.request.form.get('imgUrl', None)
        if image:
            image_name = (image.split('/')[1])
            try:
                response = requests.get(image_name)
                return {'image_name': image_name, 'image_data': response.content}
            except Exception:
                raise ObjectNotFound(f'Image data {image_name} not found')

        return None

    def update_news_item(self, news_item, image=None):
        self.set_news_item_attributes(news_item)

        if image:
            blob = NamedBlobImage(
                data=image['image_data'],
                filename=image['image_name'],
                contentType='image/jpeg'
            )
            setattr(news_item, 'image', blob)

        news_item.reindexObject()
        return news_item

    def set_news_item_attributes(self, news_item):
        setattr(news_item, 'title', self.request.form.get('title'))
        setattr(news_item, 'description', self.request.form.get('desc'))
        setattr(news_item, 'text', IRichText['text'].fromUnicode(
            self.request.form.get('body')))
        self.set_date(news_item, self.request.form.get('start'), 'setEffectiveDate')
        if self.request.form.get('end', None):
            self.set_date(news_item, self.request.form.get('end'), 'setExpirationDate')

    def set_date(self, news_item, date_raw, method):
        """
        Set effectiveDate or expirationDate.
        date_raw should be in 'dd/mm/yyyy/HH:MM' format
        """
        try:
            datetime_object = datetime.strptime(date_raw, "%d/%m/%Y/%H:%M")
        except ValueError as e:
            raise ValueError(
                f"Invalid date format: {date_raw}. Expected 'dd/mm/yyyy/HH:MM'") from e
        caller = getattr(news_item, method)
        caller(datetime_object)

    def create_news_item(self, image=None):
        news_item_params = self.build_create_params(image)
        new_news_item = createContentInContainer(**news_item_params)

        self.set_news_item_attributes(new_news_item)

        new_news_item.reindexObject()
        return new_news_item

    def build_create_params(self, image):
        portal = api.portal.get()
        news_url = portal.get('news')

        news_item_params = {
            'container': news_url,
            'portal_type': 'News Item',
            'title': self.news_item_id,
            'description': self.request.form.get('description'),
            'timezone': 'Europe/Madrid',
            'checkConstraints': False
        }

        if image:
            news_item_params['image'] = NamedBlobImage(
                data=image['image_data'],
                filename=image['image_name'],
                contentType='image/jpeg'
            )

        return news_item_params
