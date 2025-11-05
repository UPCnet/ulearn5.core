# -*- coding: utf-8 -*-
import logging

from plone import api
from plone.restapi.services import Service
from ulearn5.core.services import check_methods, check_roles
from ulearn5.core.services.new import New
from ulearn5.core.services.utils import show_news_in_app

from ulearn5.core.html_parser import (HTMLParser, getCommunityNameFromObj,
                                      replaceImagePathByURL)

logger = logging.getLogger(__name__)

NEWS_PER_PAGE = 10

class News(Service):
    """
    - Endpoint: @api/news
    - Method: GET
        Optional params:
            - page: (str) The page number to retrieve.
            - path: (str) Community name
            - external_or_internal: ['zoom_in', 'zoom_out']

        Get all News by "X-Oauth-Username"

    - Subpaths allowed: YES
    """

    PATH_DICT = {}

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request
        self.page = kwargs.get('page', None)
        self.path = kwargs.get('path', None)
        self.external_or_internal = kwargs.get('external_or_internal', None)

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if not subpath:
            return self.reply()

        next_segment = subpath[0]
        handler_class = self.PATH_DICT.get(next_segment)

        if handler_class:
            handler = handler_class(self.context, self.request)
            return handler.handle_subpath(subpath[1:])

        # No subpath is considered wrong, as a New will be
        # updated if it's found, and created otherwise
        # This means any string in its path will be the New id
        kwargs = {'new_id': next_segment}
        new_handler = New(self.context, self.request, **kwargs)
        return new_handler.handle_subpath(subpath[1:])

    @check_roles(roles=['Member', 'Manager', 'Api'])
    @check_methods(methods=['GET'])
    def reply(self):
        results = []
        pagination_page = self.request.form.get('page', None)
        total_news = 0

        if show_news_in_app():
            news, total_news = self.find_news()
            news, more_items = self.paginate_news(news, total_news, pagination_page)

            for item in news:
                results.append(self.process_news_item(item))
        else:
            return {"message": "Show in App is not enabled on this site", "code": 404}

        info = {
            'items': results,
            'more_items': more_items,
            'total_news': total_news
        }
        return info


    def find_news(self):
        query = self.build_query()
        news = api.content.find(**query)
        return news, len(news)

    def build_query(self):
        portal = api.portal.get()
        query = {
            'portal_type': 'News Item',
            'review_state': ['intranet', 'published'],
            'sort_order': 'descending',
            'sort_on': 'effective',
            'is_inapp': 'True',
        }
        path = self.request.form.pop('path', None)
        if path:
            query['path'] = '/'.join(portal.getPhysicalPath()) + '/' + path
        query.update(self.request.form)
        return query

    def paginate_news(self, news, total_news, pagination_page):
        more_items = False

        if pagination_page:
            pagination_page = int(pagination_page)
            if pagination_page == 0:
                pagination_page = 1
            start = NEWS_PER_PAGE * (pagination_page - 1)
            end = NEWS_PER_PAGE * pagination_page
            news = news[start:end]
            if end < total_news:
                more_items = True
        else:
            news = news[:NEWS_PER_PAGE]
            if NEWS_PER_PAGE < total_news:
                more_items = True

        return news, more_items

    def process_news_item(self, item):
        value = item.getObject()
        date = self.process_date(value)
        text = self.process_text(value)
        filename, contentType, raw_image = self.process_image(value)
        community_name = getCommunityNameFromObj(self.context, value)

        return {
            'title': value.title,
            'id': value.id,
            'description': value.description,
            'path': item.getURL(),
            'url_site': api.portal.get().absolute_url(),
            'absolute_url': value.absolute_url_path(),
            'text': text,
            'filename': filename,
            'caption': value.image_caption,
            'is_inapp': getattr(item, 'is_inapp', None),
            'is_outoflist': getattr(item, 'is_outoflist', None),
            'is_flash': getattr(item, 'is_flash', None),
            'is_important': getattr(item, 'is_important', None),
            'effective_date': date,
            'creators': value.creators,
            'raw_image': raw_image,
            'content_type': contentType,
            'community': community_name
        }

    def process_date(self, item):
        if getattr(item, 'effective_date', None):
            return item.effective_date.strftime("%d/%m/%Y")

        return item.creation_date.strftime("%d/%m/%Y")

    def process_text(self, item):
        if getattr(item, 'text', None):
            text = replaceImagePathByURL(item.text.output)
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