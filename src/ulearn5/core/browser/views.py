# -*- coding: utf-8 -*-
from five import grok
from zope import schema
from itertools import chain
from z3c.form import button
from zope.interface import Interface
from zope.component.hooks import getSite
from zope.component import getMultiAdapter
from zope.component import queryUtility
from zope.component import getUtility

from plone import api
from plone.directives import form
from plone.registry.interfaces import IRegistry

from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces import IPloneSiteRoot
from Products.statusmessages.interfaces import IStatusMessage

from ulearn5.core import _
from ulearn5.core.controlpanel import IUlearnControlPanelSettings
from ulearn5.core.interfaces import IUlearn5CoreLayer

from datetime import datetime

from souper.soup import get_soup
from souper.soup import Record
from repoze.catalog.query import Eq
from cStringIO import StringIO
from PIL import ImageOps
from mrs5.max.utilities import IMAXClient
import os
import PIL

import logging

logger = logging.getLogger(__name__)

import json
import requests


class AjaxUserSearch(grok.View):
    grok.context(Interface)
    grok.name('ulearn.ajaxusersearch')
    grok.require('base.authenticated')
    grok.layer(IUlearn5CoreLayer)

    def render(self):
        self.request.response.setHeader('Content-type', 'application/json')
        query = self.request.form.get('q', '')
        results = dict(more=False, results=[])
        registry = queryUtility(IRegistry)
        settings = registry.forInterface(IUlearnControlPanelSettings)

        if query:
            portal = getSite()
            hunter = getMultiAdapter((portal, self.request), name='pas_search')
            fulluserinfo = hunter.merge(chain(*[hunter.searchUsers(**{field: query}) for field in ['fullname', 'name']]), 'userid')
            values = [dict(id=userinfo.get('login'), text=u'{} ({})'.format(userinfo.get('title'), userinfo.get('login'))) for userinfo in fulluserinfo]

            if settings.nonvisibles:
                if query in settings.nonvisibles:
                    # Fa falta?
                    pass

            results['results'] = values
            return json.dumps(results)
        else:
            return json.dumps({'error': 'No query found'})


class addUserSearch(grok.View):
    grok.context(Interface)
    grok.name('add_user_search')
    grok.require('base.authenticated')
    grok.layer(IUlearn5CoreLayer)

    def render(self):
        portal = getSite()
        current_user = api.user.get_current()
        userid = current_user.id
        search_items_string = self.request.form['items']
        search_items = search_items_string.split(',')
        soup_searches = get_soup('user_news_searches', portal)
        exist = [r for r in soup_searches.query(Eq('id', userid))]
        if not exist:
            record = Record()
            record.attrs['id'] = userid
            record.attrs['searches'] = [search_items]
            record_id = soup_searches.add(record)
            acl_record = soup_searches.get(record_id)
        else:
            acl_record = exist[0]
            in_list = False
            total_searches = acl_record.attrs['searches']
            if acl_record.attrs['searches']:
                for search in acl_record.attrs['searches']:
                    for i, item in enumerate(search_items):
                        if item not in search:
                            break
                        if i == len(search_items) - 1:
                            if len(search_items) < len(search):
                                break
                            else:
                                in_list = True
            if not in_list:
                total_searches.append(search_items)
                acl_record.attrs['searches'] = total_searches
            else:
                acl_record.attrs['searches'] = total_searches

        soup_searches.reindex(records=[acl_record])


class removeUserSearch(grok.View):
    grok.context(Interface)
    grok.name('remove_user_search')
    grok.require('base.authenticated')
    grok.layer(IUlearn5CoreLayer)

    def render(self):
        portal = getSite()
        current_user = api.user.get_current()
        userid = current_user.id
        search_items = self.request.form['items']
        search_items = search_items.split(',')
        in_list = False
        soup_searches = get_soup('user_news_searches', portal)
        exist = [r for r in soup_searches.query(Eq('id', userid))]
        if exist:
            acl_record = exist[0]
            total_searches = acl_record.attrs['searches']
            for search in exist[0].attrs['searches']:
                for i, item in enumerate(search_items):
                    if item not in search:
                        break
                    if i == len(search_items) - 1:
                        if len(search_items) < len(search):
                            break
                        else:
                            in_list = True
                    if in_list:
                        total_searches.remove(search_items)
                        acl_record.attrs['searches'] = total_searches
                        soup_searches.reindex(records=[acl_record])


class isSearchInSearchers(grok.View):
    grok.context(Interface)
    grok.name('search_in_searchers')
    grok.require('base.authenticated')
    grok.layer(IUlearn5CoreLayer)

    def render(self):
        portal = getSite()
        current_user = api.user.get_current()
        userid = current_user.id
        search_items = self.request.form['items']
        search_items = search_items.split(',')
        soup_searches = get_soup('user_news_searches', portal)
        exist = [r for r in soup_searches.query(Eq('id', userid))]
        if exist:
            if exist[0].attrs['searches']:
                for search in exist[0].attrs['searches']:
                    for i, item in enumerate(search_items):
                        if item not in search:
                            break
                        if i == len(search_items) - 1:
                            if len(search_items) < len(search):
                                break
                            else:
                                return True
                return False
        return False


class getUserSearchers(grok.View):
    grok.context(Interface)
    grok.name('get_user_searchers')
    grok.require('base.authenticated')
    grok.layer(IUlearn5CoreLayer)

    def render(self):
        portal = getSite()
        current_user = api.user.get_current()
        userid = current_user.id
        soup_searches = get_soup('user_news_searches', portal)
        exist = [r for r in soup_searches.query(Eq('id', userid))]

        res = []
        if exist:
            values = exist[0].attrs['searches']
            if values:
                for val in values:
                    res.append(' '.join(val))
        return res


class MigrateAvatars(grok.View):
    """ Migrate avatar images from disk to web (migration on sunday 27/11/2017) """
    grok.name('migrate_avatars')
    grok.context(Interface)
    grok.require('base.member')
    grok.layer(IUlearn5CoreLayer)

    def render(self):
        path = '/var/plone/import-images/'
        for filename in os.listdir(path):
            portrait = open(path + filename, 'rb')
            scaled, mimetype = self.convertSquareImage(portrait)
            scaled.seek(0)
            safe_id = filename

            # Upload to MAX server using restricted user credentials
            maxclient, settings = getUtility(IMAXClient)()
            maxclient.setActor(settings.max_restricted_username)
            maxclient.setToken(settings.max_restricted_token)
            migratedMessage = ''
            try:
                maxclient.people[safe_id].avatar.post(upload_file=scaled)
                logger.info('OK! Avatar image changed for user: ' + filename)
            except Exception as exc:
                logger.error(exc.message)
                logger.info('ERROR! Error processing Avatar image for user: ' + filename)

        migrating = maxclient.url
        migratedMessage = str(migrating) + 'END!'
        return migratedMessage

    def convertSquareImage(self, image_file):
        CONVERT_SIZE = (250, 250)
        image = PIL.Image.open(image_file)
        format = image.format
        mimetype = 'image/%s' % format.lower()

        # Old way
        # if image.size[0] > 250 or image.size[1] > 250:
        #     image.thumbnail((250, 9800), PIL.Image.ANTIALIAS)
        #     image = image.transform((250, 250), PILImage.EXTENT, (0, 0, 250, 250), PILImage.BICUBIC)

        result = ImageOps.fit(image, CONVERT_SIZE, method=PIL.Image.ANTIALIAS, centering=(0.5, 0.5))
        new_file = StringIO()
        result.save(new_file, format, quality=88)
        new_file.seek(0)

        return new_file, mimetype
