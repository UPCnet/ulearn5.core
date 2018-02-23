# -*- coding: utf-8 -*-
from five import grok

from Products.CMFPlone.interfaces import IPloneSiteRoot
from plone import api
from plone.app.contenttypes.behaviors.richtext import IRichText
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobImage

from ulearn5.core.api import ApiResponse
from ulearn5.core.api import REST
from ulearn5.core.api import api_resource
from ulearn5.core.api.root import APIRoot

from datetime import datetime

import requests


class News(REST):
    """
        /api/news
    """

    placeholder_type = 'new'
    placeholder_id = 'newid'

    grok.adapts(APIRoot, IPloneSiteRoot)
    grok.require('base.authenticated')


class New(REST):
    """
        /api/news/{newid}
    """
    grok.adapts(News, IPloneSiteRoot)
    grok.require('base.authenticated')

    def __init__(self, context, request):
        super(New, self).__init__(context, request)

    @api_resource(required=['newid', 'title', 'description', 'body', 'start'])
    def POST(self):
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

    def create_new(self, newid, title, desc, body, imgData, imgName, date_start, date_end):
        date_start = date_start.split('/')
        time_start = date_start[3].split(':')

        portal_url = api.portal.get()
        news_url = portal_url['news']
        pc = api.portal.get_tool('portal_catalog')
        brains = pc.unrestrictedSearchResults(portal_type='News Item', id=newid)
        if not brains:
            if imgName != '':
                new_new = createContentInContainer(news_url,
                                                   'News Item',
                                                   title=newid,
                                                   image=NamedBlobImage(data=imgData,
                                                                        filename=imgName,
                                                                        contentType='image/jpeg'),
                                                   description=desc,
                                                   timezone="Europe/Madrid",
                                                   checkConstraints=False)
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
            resp = ApiResponse.from_string('News Item {} created'.format(newid), code=201)
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
            resp = ApiResponse.from_string('News Item {} updated'.format(newid), code=200)

        return resp
