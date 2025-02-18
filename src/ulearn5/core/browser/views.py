# -*- coding: utf-8 -*-
import io
import json
import logging
import os
import uuid
from io import StringIO
from itertools import chain

import PIL
import requests
from base5.core.utils import json_response, portal_url
from mrs5.max.utilities import IMAXClient
from plone import api
from plone.namedfile.utils import set_headers, stream_data
from plone.portlets.interfaces import (IPortletAssignmentMapping,
                                       IPortletManager)
from plone.registry.interfaces import IRegistry
from Products.Five.browser import BrowserView
from Products.statusmessages.interfaces import IStatusMessage
from ulearn5.core import _
from ulearn5.core.controlpanel import IUlearnControlPanelSettings
from ulearn5.core.utils import (get_or_initialize_annotation,
                                getSearchersFromUser)
from zope.component import getMultiAdapter, getUtility, queryUtility
from zope.component.hooks import getSite

logger = logging.getLogger(__name__)


class monitoringView(BrowserView):
    """Convenience view for monitoring software"""

    def __call__(self):
        return '1'


class AjaxUserSearch(BrowserView):

    def __call__(self):
        self.request.response.setHeader('Content-type', 'application/json')
        query = self.request.form.get('q', '')
        results = dict(more=False, results=[])
        registry = queryUtility(IRegistry)
        settings = registry.forInterface(IUlearnControlPanelSettings)

        if query:
            portal = getSite()
            hunter = getMultiAdapter((portal, self.request), name='pas_search')
            fulluserinfo = hunter.merge(chain(*[hunter.searchUsers(**{field: query}) for field in ['fullname', 'name']]), 'userid')
            values = [dict(id=userinfo.get('login'), text='{} ({})'.format(userinfo.get('title').decode('utf-8'), userinfo.get('login'))) for userinfo in fulluserinfo]

            if settings.nonvisibles:
                if query in settings.nonvisibles:
                    # Fa falta?
                    pass

            results['results'] = values
            return json.dumps(results)
        else:
            return json.dumps({'error': 'No query found'})


class addUserSearch(BrowserView):

    def __call__(self):
        current_user = api.user.get_current()
        userid = current_user.id
        search_items_string = self.request.form['items']
        search_items = search_items_string.split(',')

        user_news_searches = get_or_initialize_annotation('user_news_searches')
        record = next((r for r in user_news_searches.values() if r.get('id') == userid), None)
        if not record:
            record = {
                'id': userid,
                'searches': list(search_items)
            }
            unique_key = str(uuid.uuid4())
            user_news_searches[unique_key] = record
        else:
            in_list = any(
                all(item in search for i, item in enumerate(search_items)) and 
                (len(search_items) >= len(search))
                for search in record.get('searches', [])
            )

            if not in_list:
                record['searches'].append(search_items)
        
        return json.dumps(getSearchersFromUser())


class removeUserSearch(BrowserView):

    def __call__(self):
        current_user = api.user.get_current()
        userid = current_user.id
        search_items = self.request.form['items']
        search_items = search_items.split(',')

        user_news_searches = get_or_initialize_annotation('user_news_searches')
        record = next((r for r in user_news_searches.values() if r.get('id') == userid), None)

        if record:
            total_searches = record.get('searches', [])
            in_list = False

            for search in total_searches:
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
                    except Exception as e:
                        print(e)
                        pass
                    record['searches'] = total_searches

        return json.dumps(getSearchersFromUser())



class isSearchInSearchers(BrowserView):

    def __call__(self):
        portal = getSite()
        current_user = api.user.get_current()
        userid = current_user.id
        search_items = self.request.form['items']
        search_items = search_items.split(',')
        user_news_searches = get_or_initialize_annotation('user_news_searches')
        record = next((r for r in user_news_searches.values() if r.get('id') == userid), None)
        if record:
            if record.get('searches'):
                for search in record.get('searches'):
                    for i, item in enumerate(search_items):
                        if item not in search:
                            break
                        if i == len(search_items) - 1:
                            if len(search_items) < len(search):
                                break
                            else:
                                return True
        return False

class getUserSearchers(BrowserView):

    def __call__(self):
        return json.dumps(getSearchersFromUser())


class MigrateAvatars(BrowserView):
    """
    Migrate avatar images from disk to web (migration on sunday 27/11/2017)
    """

    def __call__(self):
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
        except Exception as e:
            print(e)
            portrait_url = portal_url() + '/++theme++ulearn5/assets/images/defaultUser.png'
            imgData = requests.get(portrait_url).content
            image = PIL.Image.open(io.BytesIO(imgData))
            image.filename = 'defaultUser'

        format = image.format
        mimetype = 'image/%s' % format.lower()

        result = PIL.ImageOps.fit(
            image, CONVERT_SIZE, method=PIL.Image.ANTIALIAS, centering=(0.5, 0.5)
        )

        # Bypass CMYK problem in conversion
        if result.mode not in ["1", "L", "P", "RGB", "RGBA"]:
            result = result.convert("RGB")

        new_file = StringIO()
        result.save(new_file, format, quality=88)
        new_file.seek(0)

        return new_file, mimetype


class ImagePortletImageView(BrowserView):
    """
    Expose image fields as downloadable BLOBS from the image portlet.
    Allow set caching rules (content caching for this view)
    Ex: ulearn5.nomines.portlets.banner
    """
    def __call__(self):
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


class ResetNotify(BrowserView):

    def __call__(self):
        if 'confirm' in self.request.form:
            notify_popup = get_or_initialize_annotation('notify_popup')
            notify_popup.clear()

            IStatusMessage(self.request).addStatusMessage(_('Reset notify from all users'), type='info')
            self.request.response.redirect(getSite().absolute_url() + '/@@ulearn-control-popup')


class ViewAnnotationNotifyPopup(BrowserView):

    @json_response
    def __call__(self):
        notify_popup = get_or_initialize_annotation('notify_popup')
        records = [r for r in list(notify_popup.values())]
        result = [record.get('id') for record in records]
        return result


class CloseNotifyPopup(BrowserView):

    def __call__(self):
        user = api.user.get_current()
        notify_popup = get_or_initialize_annotation('notify_popup')
        record = next((r for r in notify_popup.values() if r.get('id') == user.id), None)

        if not record:
            record = {'id': user.id}
            unique_key = str(uuid.uuid4())
            notify_popup[unique_key] = record

class CloseNotifyPopupBirthday(BrowserView):

    def __call__(self):
        self.request.response.expireCookie('popup_birthday', path='/')


class UpdateBirthdayProfileByMail(BrowserView):

    def __call__(self):
        email = self.request.form.get('email', '')
        birthday = self.request.form.get('birthday', '')
        if email == '' or birthday == '':
            return 'Es necessario pasar los parámetros email y birthday'

        user_properties = get_or_initialize_annotation('user_properties')
        records = [r for r in user_properties.values() if r.get('email') == email]

        if not records:
            return f'KO {email}. No se encontró ningún usuario con este correo'
        
        if len(records) > 1:
            return f'KO {email}. Más de un usuario tiene este correo'
        
        username = records[0].get('username')
        if username:
            user = api.user.get(userid = username)
            user.setMemberProperties({'birthday': birthday})
            return f'OK {email}'