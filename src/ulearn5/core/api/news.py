# -*- coding: utf-8 -*-
import requests

from datetime import datetime
from five import grok
from lxml import html

from Products.CMFPlone.interfaces import IPloneSiteRoot
from plone import api
from plone.app.contenttypes.behaviors.richtext import IRichText
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobImage

from ulearn5.core.api import ApiResponse
from ulearn5.core.api import ObjectNotFound
from ulearn5.core.api import REST
from ulearn5.core.api import api_resource
from ulearn5.core.api.root import APIRoot
from ulearn5.core.formatting import formatMessageEntities
from ulearn5.core.html_parser import getCommunityNameFromObj
from ulearn5.core.html_parser import HTMLParser
from ulearn5.core.html_parser import replaceImagePathByURL


class News(REST):
    """
        /api/news
        and
        /api/news/NEW_ID

        Get all News by "X-Oauth-Username"
        :param page
        :param path: community_name
        :param external_or_internal: ['zoom_in', 'zoom_out']
    """

    placeholder_type = 'new'
    placeholder_id = 'newid'

    grok.adapts(APIRoot, IPloneSiteRoot)
    grok.require('base.authenticated')

    @api_resource(required=[])
    def GET(self):
        portal = api.portal.get()
        show_news_in_app = api.portal.get_registry_record(
            name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.show_news_in_app')
        results = []
        news_per_page = 10  # Default items per page
        pagination_page = self.params.pop('page', None)
        more_items = False
        total_news = 0
        if show_news_in_app:
            query = {
                'portal_type': 'News Item',
                'review_state': ['intranet', 'published'],
                'sort_order': 'descending',
                'sort_on': 'effective',
                'is_inapp': 'True',
            }
            for k in self.params.keys():
                if k == 'path':
                    query[k] = ('/').join(portal.getPhysicalPath()
                                          ) + '/' + self.params.pop(k, None)
                else:
                    query[k] = self.params.pop(k, None)
            news = api.content.find(**query)
            total_news = len(news)
            print(query)
            print(total_news)
            if pagination_page:
                # Si page = 0, devolvemos la ?page=1 (que es lo mismo)
                if pagination_page == '0':
                    pagination_page = 1
                start = int(news_per_page) * (int(pagination_page) - 1)
                end = int(news_per_page) * int(pagination_page)
                # Devolvemos paginando
                news = news[start:end]
                if end < total_news:
                    more_items = True
            else:
                # No paginammos, solo devolvemos 10 primeras => ?page=1
                news = news[0:news_per_page]
                if news_per_page < total_news:
                    more_items = True

            for item in news:
                value = item.getObject()
                if value.effective_date:
                    date = value.effective_date.strftime("%d/%m/%Y")
                else:
                    date = value.creation_date.strftime("%d/%m/%Y")
                if value.text:
                    text = replaceImagePathByURL(value.text.output)
                    text = HTMLParser(text)
                else:
                    text = None

                is_inapp = None
                is_outoflist = None
                is_flash = None
                is_important = None
                filename = None
                contentType = None
                raw_image = None

                if getattr(item, 'is_inapp', None):
                    is_inapp = item.is_inapp
                if getattr(item, 'is_outoflist', None):
                    is_outoflist = item.is_outoflist
                if getattr(item, 'is_flash', None):
                    is_flash = item.is_flash
                if getattr(item, 'is_important', None):
                    is_important = item.is_important
                if getattr(value, 'image', None):
                    filename = value.image.filename
                    contentType = value.image.contentType
                    raw_image = value.absolute_url() + '/thumbnail-image'

                communityName = getCommunityNameFromObj(self, value)

                new = dict(title=value.title,
                           id=value.id,
                           description=value.description,
                           path=item.getURL(),
                           url_site=portal.absolute_url(),
                           absolute_url=value.absolute_url_path(),
                           text=text,
                           filename=filename,
                           caption=value.image_caption,
                           is_inapp=is_inapp,
                           is_outoflist=is_outoflist,
                           is_flash=is_flash,
                           is_important=is_important,
                           effective_date=date,
                           creators=value.creators,
                           raw_image=raw_image,
                           content_type=contentType,
                           community=communityName
                           )
                results.append(new)
        values = dict(items=results,
                      more_items=more_items,
                      total_news=total_news)
        return ApiResponse(values)


class New(REST):
    grok.adapts(News, IPloneSiteRoot)
    grok.require('base.authenticated')

    def __init__(self, context, request):
        super(New, self).__init__(context, request)

    @api_resource(required=['newid', 'title', 'description', 'body', 'start'])
    def POST(self):
        """
            /api/news/{newid}
        """
        imgName = ''
        imgData = ''
        newid = self.params.pop('newid')
        title = self.params.pop('title')
        desc = self.params.pop('description')
        body = self.params.pop('body')
        date_start = self.params.pop('start')
        date_end = self.params.pop('end', None)
        img = self.params.pop('imgUrl', None)
        if img:
            imgName = (img.split('/')[-1]).decode('utf-8')
            imgData = requests.get(img).content

        result = self.create_new(newid,
                                 title,
                                 desc,
                                 body,
                                 imgData,
                                 imgName,
                                 date_start,
                                 date_end)

        return result

    @api_resource(required=['newid'])
    def GET(self):
        """
            /api/news/{newid}?absolute_url={absolute_url}
        """
        show_news_in_app = api.portal.get_registry_record(
            name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.show_news_in_app')
        if show_news_in_app:
            newid = self.params['newid']
            mountpoint_id = self.context.getPhysicalPath()[1]
            if 'absolute_url' in self.params:
                absolute_url = self.params['absolute_url']
                if mountpoint_id == self.context.id:
                    default_path = '/'.join(absolute_url.split('/')[:-1])
                else:
                    default_path = '/' + mountpoint_id + '/' + api.portal.get().id + '/'.join(absolute_url.split('/')
                                                                                              [:-1])
            else:
                if mountpoint_id == self.context.id:
                    default_path = '/'.join(api.portal.get().getPhysicalPath()
                                            ) + '/news'
                else:
                    default_path = '/' + mountpoint_id + '/' + api.portal.get().id + '/news'
            item = api.content.find(portal_type="News Item",
                                    path=default_path, id=newid)
            if item:
                newitem = item[0]
                value = newitem.getObject()
                if value.effective_date:
                    date = value.effective_date.strftime("%d/%m/%Y")
                else:
                    date = value.creation_date.strftime("%d/%m/%Y")
                if value.text:
                    text = formatMessageEntities(html.tostring(
                        html.fromstring(value.text.output)))
                    if text is not None:
                        text = replaceImagePathByURL(text)
                        text = HTMLParser(text)
                    else:
                        text = None
                else:
                    text = ''

                is_inapp = None
                is_outoflist = None
                is_flash = None
                is_important = None
                filename = None
                contentType = None
                raw_image = None

                if getattr(newitem, 'is_inapp', None):
                    is_inapp = newitem.is_inapp
                if getattr(newitem, 'is_outoflist', None):
                    is_outoflist = newitem.is_outoflist
                if getattr(newitem, 'is_flash', None):
                    is_flash = newitem.is_flash
                if getattr(newitem, 'is_important', None):
                    is_important = newitem.is_important
                if getattr(value, 'image', None):
                    filename = value.image.filename
                    contentType = value.image.contentType
                    raw_image = value.absolute_url() + '/thumbnail-image'

                communityName = getCommunityNameFromObj(self, value)
                portal = api.portal.get()
                new = dict(title=value.title,
                           id=value.id,
                           description=value.description,
                           path=value.absolute_url(),
                           url_site=portal.absolute_url(),
                           absolute_url=value.absolute_url_path(),
                           text=text,
                           filename=filename,
                           caption=value.image_caption,
                           is_inapp=is_inapp,
                           is_outoflist=is_outoflist,
                           is_flash=is_flash,
                           is_important=is_important,
                           effective_date=date,
                           creators=value.creators,
                           content_type=contentType,
                           raw_image=raw_image,
                           community=communityName
                           )
            else:
                raise ObjectNotFound('News Item not found')
            return ApiResponse(new)
        else:
            return ApiResponse.from_string(
                'Show in App not enabled on this site', code=404)

    def create_new(
            self, newid, title, desc, body, imgData, imgName, date_start, date_end):
        date_start = date_start.split('/')
        time_start = date_start[3].split(':')

        portal_url = api.portal.get()
        news_url = portal_url['news']
        pc = api.portal.get_tool('portal_catalog')
        brains = pc.unrestrictedSearchResults(portal_type='News Item', id=newid)
        if not brains:
            if imgName != '':
                new_new = createContentInContainer(
                    news_url, 'News Item', title=newid,
                    image=NamedBlobImage(
                        data=imgData, filename=imgName, contentType='image/jpeg'),
                    description=desc, timezone="Europe/Madrid", checkConstraints=False)
            else:
                new_new = createContentInContainer(news_url,
                                                   'News Item',
                                                   title=newid,
                                                   description=desc,
                                                   timezone="Europe/Madrid",
                                                   checkConstraints=False)
            new_new.title = title
            new_new.setEffectiveDate(datetime(int(date_start[2]),
                                              int(date_start[1]),
                                              int(date_start[0]),
                                              int(time_start[0]),
                                              int(time_start[1])
                                              )
                                     )
            if date_end:
                date_end = date_end.split('/')
                time_end = date_end[3].split(':')
                new_new.setExpirationDate(datetime(int(date_end[2]),
                                                   int(date_end[1]),
                                                   int(date_end[0]),
                                                   int(time_end[0]),
                                                   int(time_end[1])
                                                   )
                                          )
            new_new.text = IRichText['text'].fromUnicode(body)
            new_new.reindexObject()
            resp = ApiResponse.from_string(
                'News Item {} created'.format(newid), code=201)
        else:
            new = brains[0].getObject()
            new.title = title
            new.description = desc
            new.setEffectiveDate(datetime(int(date_start[2]),
                                          int(date_start[1]),
                                          int(date_start[0]),
                                          int(time_start[0]),
                                          int(time_start[1])
                                          )
                                 )
            if date_end:
                new.setExpirationDate(datetime(int(date_end[2]),
                                               int(date_end[1]),
                                               int(date_end[0]),
                                               int(time_end[0]),
                                               int(time_end[1])
                                               )
                                      )
            if imgName != '':
                new.image = NamedBlobImage(data=imgData,
                                           filename=imgName,
                                           contentType='image/jpeg')
            new.text = IRichText['text'].fromUnicode(body)
            new.reindexObject()
            resp = ApiResponse.from_string(
                'News Item {} updated'.format(newid), code=200)

        return resp
