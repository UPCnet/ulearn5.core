# -*- coding: utf-8 -*-
from PIL import ImageOps
from Products.statusmessages.interfaces import IStatusMessage
from cStringIO import StringIO

from five import grok
from itertools import chain
from plone import api
from plone.namedfile.utils import set_headers
from plone.namedfile.utils import stream_data
from plone.portlets.interfaces import IPortletAssignmentMapping
from plone.portlets.interfaces import IPortletManager
from plone.registry.interfaces import IRegistry
from repoze.catalog.query import Eq
from souper.soup import Record
from souper.soup import get_soup
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.hooks import getSite
from zope.interface import Interface

from base5.core.utils import json_response
from base5.core.utils import portal_url
from mrs5.max.utilities import IMAXClient

from ulearn5.core import _
from ulearn5.core.controlpanel import IUlearnControlPanelSettings
from ulearn5.core.interfaces import IUlearn5CoreLayer
from ulearn5.core.utils import getSearchersFromUser

import PIL
import io
import json
import logging
import os
import requests


logger = logging.getLogger(__name__)


class monitoringView(grok.View):
    """ Convenience view for monitoring software """
    grok.name('ping')
    grok.context(Interface)
    grok.require('zope2.View')

    def render(self):
        return '1'


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
            values = [dict(id=userinfo.get('login'), text=u'{} ({})'.format(userinfo.get('title').decode('utf-8'), userinfo.get('login'))) for userinfo in fulluserinfo]

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
        return json.dumps(getSearchersFromUser())


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
                        try:
                            total_searches.remove(search_items)
                        except:
                            pass
                        acl_record.attrs['searches'] = total_searches
                        soup_searches.reindex(records=[acl_record])

        return json.dumps(getSearchersFromUser())


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
        return json.dumps(getSearchersFromUser())


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
        try:
            image = PIL.Image.open(image_file)
        except:
            portrait_url = portal_url() + '/++theme++ulearn5/assets/images/defaultUser.png'
            imgData = requests.get(portrait_url).content
            image = PIL.Image.open(io.BytesIO(imgData))
            image.filename = 'defaultUser'

        format = image.format
        mimetype = 'image/%s' % format.lower()

        result = ImageOps.fit(image, CONVERT_SIZE, method=PIL.Image.ANTIALIAS, centering=(0.5, 0.5))

        # Bypass CMYK problem in conversion
        if result.mode not in ["1", "L", "P", "RGB", "RGBA"]:
            result = result.convert("RGB")

        new_file = StringIO()
        result.save(new_file, format, quality=88)
        new_file.seek(0)

        return new_file, mimetype


class ImagePortletImageView(grok.View):
    grok.name('image-portlet-view')
    grok.context(Interface)
    grok.require('zope2.View')

    """
    Expose image fields as downloadable BLOBS from the image portlet.
    Allow set caching rules (content caching for this view)
    Ex: ulearn5.nomines.portlets.banner
    """
    def render(self):
        content = self.context
        # Read portlet assignment pointers from the GET query
        name = self.request.form.get("portletName")
        portletManager = self.request.form.get("portletManager")
        imageId = self.request.form.get("image")
        # Resolve portlet and its image field
        manager = getUtility(IPortletManager, name=portletManager, context=content)
        mapping = getMultiAdapter((content, manager), IPortletAssignmentMapping)
        portlet = mapping[name]
        image = getattr(portlet, imageId, None)
        if not image:
            return ""
        # Set content type and length headers
        set_headers(image, self.request.response)
        # Push data to the downstream clients
        return stream_data(image)


class ResetNotify(grok.View):
    grok.name('reset_notify')
    grok.context(Interface)
    grok.template('reset_notify')
    grok.require('base.webmaster')
    grok.layer(IUlearn5CoreLayer)

    def update(self):
        if 'confirm' in self.request.form:
            portal = api.portal.get()
            soup = get_soup('notify_popup', portal)
            soup.clear()

            IStatusMessage(self.request).addStatusMessage(_(u'Reset notify from all users'), type='info')
            self.request.response.redirect(getSite().absolute_url() + '/@@ulearn-control-popup')


class ViewAnnotationNotifyPopup(grok.View):
    grok.name('view_annotation_notify_popup')
    grok.context(Interface)
    grok.require('cmf.ManagePortal')
    grok.layer(IUlearn5CoreLayer)

    @json_response
    def render(self):
        portal = api.portal.get()
        soup = get_soup('notify_popup', portal)
        records = [r for r in soup.data.items()]
        result = []
        for record in records:
            result.append(record[1].attrs['id'])
        return result


class CloseNotifyPopup(grok.View):
    grok.name('close_notify_popup')
    grok.context(Interface)
    grok.require('zope2.View')
    grok.layer(IUlearn5CoreLayer)

    def render(self):
        user = api.user.get_current()
        portal = api.portal.get()
        soup = get_soup('notify_popup', portal)
        exist = [r for r in soup.query(Eq('id', user.id))]
        if not exist:
            record = Record()
            record.attrs['id'] = user.id
            soup.add(record)
            soup.reindex()


class CloseNotifyPopupBirthday(grok.View):
    grok.name('close_notify_popup_birthday')
    grok.context(Interface)
    grok.require('zope2.View')
    grok.layer(IUlearn5CoreLayer)

    def render(self):
        self.request.response.expireCookie('popup_birthday', path='/')


class UpdateBirthdayProfileByMail(grok.View):
    grok.name('update_birthday_profile_by_mail')
    grok.context(Interface)
    grok.require('cmf.ManagePortal')
    grok.layer(IUlearn5CoreLayer)

    def render(self):
        email = self.request.form.get('email', '')
        birthday = self.request.form.get('birthday', '')
        if email == '' or birthday == '':
            return 'Es necessario pasar los parámetros email y birthday'

        portal = api.portal.get()
        soup = get_soup('user_properties', portal)
        records = [r for r in soup.query(Eq('email', email))]
        if records:
            if len(records) > 1:
                return 'KO ' + email + '. Más de un usuario tiene este correo'

            username = records[0].attrs.get('username')
            if username:
                user = api.user.get(userid=username)
                user.setMemberProperties({'birthday': birthday})
                return 'OK ' + email

        return 'KO ' + email + '. No se encontro ningún usuario con este correo'
