# -*- coding: utf-8 -*-
from datetime import datetime
from five import grok
from plone import api
from Products.CMFPlone.interfaces import IPloneSiteRoot
from repoze.catalog.query import Eq
from souper.soup import get_soup
from ulearn5.core.api import ApiResponse
from ulearn5.core.api import api_resource
from ulearn5.core.api import BadParameters
from ulearn5.core.api import REST
from ulearn5.core.api.root import APIRoot



class Notifications(REST):
    """
        /api/notifications?username={username}

        http://localhost:8090/Plone/api/notifications?username=ulearn.user2
        
        :param user: username of user
        
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
    
    def getGeneralInformationNotification(self, result, portal, user):
        active = True if api.portal.get_registry_record('ulearn5.core.controlpopup.IPopupSettings.activate_notify') else False
        map = {
            'fullname': user.getProperty('fullname', user.id),
        }   
        try:
            msg = portal['gestion']['popup']['notify'].text.raw % map
        except:
            try:
                msg = portal['gestion']['popup']['notify'].text.raw
            except:
                msg = ''
        if active:
            soup = get_soup('notify_popup', portal)
            user_soup = [r for r in soup.query(Eq('id', user.id))]
            object = dict(
                is_active=True,
                is_dismissed=False if not user_soup else True,
                message=msg
            )
        result['general'] = object
        
    def getBirthdayInformationNotification(self, result, portal, user):
        active = True if api.portal.get_registry_record('ulearn5.core.controlpopup.IPopupSettings.activate_birthday') else False
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
        except:
            try:
                msg = portal['gestion']['popup']['birthday'].text.raw
            except:
                msg = ''
        if active:
            object = dict(
                is_active=True,
                is_dismissed=False,
                message=msg
            )
        result['birthday'] = object

    @api_resource(required=['username'])
    def GET(self):
        """ Return the notification object. """
        # TODO:
        #   - Buscar las imagenes internas y añadirles /thumbnail-image
        #   - Implementar la lógica en frontend para que a partir de la fecha de nacimiento del usuario, del día actual y de 
        #       si está activa la notificación de cumpleaños, muestre un pop-up por pantalla. Sólo 1 vez al día.
        #   - Añadir endpoint POST para dismiss de notificación general
        
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
