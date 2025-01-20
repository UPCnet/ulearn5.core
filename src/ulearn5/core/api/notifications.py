# -*- coding: utf-8 -*-
from datetime import datetime
from five import grok
from plone import api
from Products.CMFPlone.interfaces import IPloneSiteRoot
import re
from repoze.catalog.query import Eq
from souper.soup import get_soup
from souper.soup import Record
from ulearn5.core.api import ApiResponse
from ulearn5.core.api import api_resource
from ulearn5.core.api import BadParameters
from ulearn5.core.api import REST
from ulearn5.core.api.root import APIRoot
from six.moves import range


class Notifications(REST):
    """
        /api/notifications?username={username}

        http://localhost:8090/Plone/api/notifications?username=ulearn.user2
        
        :param user: username of user
        
        * general tiene un soup donde leer y guardar información
        * birthday en web funciona con una cookie y no tiene soup asociado
        
        Returns

        {
            'general': {
                'is_active': True|False,
                'is_dismissed': True|False,
                'message': [],
            },
            'birthday': {
                'is_active': True|False,
                'is_dismissed': True|False,
                'message': [],
            }
        }

    """
    placeholder_type = 'notifications'
    placeholder_id = 'notifications'

    grok.adapts(APIRoot, IPloneSiteRoot)
    grok.require('base.authenticated')
    
    def replaceImagePathByURL(self, msg):
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
    
    def getGeneralInformationNotification(self, result, portal, user):
        active = True if api.portal.get_registry_record('ulearn5.core.controlpopup.IPopupSettings.activate_notify') else False
        if active:
            map = {
            'fullname': user.getProperty('fullname', user.id),
            }
            try:
                msg = portal['gestion']['popup']['notify'].text.raw % map
                msg = self.replaceImagePathByURL(msg)
            except:
                try:
                    msg = portal['gestion']['popup']['notify'].text.raw
                    msg = self.replaceImagePathByURL(msg)
                except:
                    msg = ''
            soup = get_soup('notify_popup', portal)
            user_soup = [r for r in soup.query(Eq('id', user.id))]
            object = dict(
                is_active=True,
                is_dismissed=False if not user_soup else True,
                message=msg
            )
        else:
            object = dict(
                is_active=False,
            )
        result['general'] = object
        
    def getBirthdayInformationNotification(self, result, portal, user):
        active = True if api.portal.get_registry_record('ulearn5.core.controlpopup.IPopupSettings.activate_birthday') else False
        if active:
            birthday = user.getProperty('birthday')
            if "/" in birthday:
                birthday = datetime.strptime(birthday, '%d/%m/%Y')
            elif "-" in birthday:
                birthday = datetime.strptime(birthday, '%d-%m-%Y')
            user_year = int(birthday.strftime('%Y'))
            current_year = int(datetime.now().strftime('%Y'))
            map = {
                'fullname': user.getProperty('fullname', user.id),
                'years': current_year - user_year
            }
            try:
                msg = portal['gestion']['popup']['birthday'].text.raw % map
                msg = self.replaceImagePathByURL(msg)
            except:
                try:
                    msg = portal['gestion']['popup']['birthday'].text.raw
                    msg = self.replaceImagePathByURL(msg)
                except:
                    msg = ''
            object = dict(
                is_active=True,
                is_dismissed=False,
                message=msg
            )
        else:
            object = dict(
                is_active=False,
            )
        result['birthday'] = object

    @api_resource(required=['username'])
    def GET(self):
        """ Return the notification object. """
        user = api.user.get(username=self.params['username'])
        if not user:
            raise BadParameters(self.params['username'])
        portal = api.portal.get()

        result = {
            'general': {},
            'birthday': {}
        }
        
        self.getGeneralInformationNotification(result, portal, user)
        self.getBirthdayInformationNotification(result, portal, user)
        
        return ApiResponse(result)
    
    @api_resource(required=['username'])
    def POST(self):
        """ Dismiss notification. """
        user = api.user.get(username=self.params['username'])
        if not user:
            raise BadParameters(self.params['username'])
        portal = api.portal.get()
        soup = get_soup('notify_popup', portal)
        exist = [r for r in soup.query(Eq('id', user.id))]
        if not exist:
            record = Record()
            record.attrs['id'] = user.id
            soup.add(record)
            soup.reindex()
        
        return ApiResponse({"success": "Notificació general tancada amb èxit."})
