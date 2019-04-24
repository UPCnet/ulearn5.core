# -*- coding: utf-8 -*-
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot
from Products.Five.browser import BrowserView

from plone import api
from plone.registry.interfaces import IRegistry
from repoze.catalog.query import Eq
from souper.soup import get_soup
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.hooks import getSite

from mrs5.max.utilities import IMAXClient
from ulearn5.core.controlpanel import IUlearnControlPanelSettings

import json
import transaction


def json_response(func):
    """ Decorator to transform the result of the decorated function to json.
        Expect a list (collection) that it's returned as is with response 200 or
        a dict with 'data' and 'status_code' as keys that gets extracted and
        applied the response.
    """
    def decorator(*args, **kwargs):
        instance = args[0]
        request = getattr(instance, 'request', None)
        request.response.setHeader(
            'Content-Type',
            'application/json; charset=utf-8'
        )
        result = func(*args, **kwargs)
        if isinstance(result, list):
            request.response.setStatus(200)
            return json.dumps(result, indent=2, sort_keys=True)
        else:
            request.response.setStatus(result.get('status_code', 200))
            return json.dumps(result.get('data', result), indent=2, sort_keys=True)

    return decorator


def is_activate_owncloud(self):
    """ Returns True id ulearn5.owncloud is installed """
    return isInstalledProduct(self, 'ulearn5.owncloud')


class ulearnUtils(BrowserView):
    """ Convenience methods placeholder ulearn.utils view. """

    def portal(self):
        return api.portal.get()

    def get_url_forget_password(self, context):
        """ return redirect url when forget user password """
        portal = getToolByName(context, 'portal_url').getPortalObject()
        base_path = '/'.join(portal.getPhysicalPath())
        registry = queryUtility(IRegistry)
        settings = registry.forInterface(IUlearnControlPanelSettings)
        if 'http' in settings.url_forget_password:
            return settings.url_forget_password
        else:
            return base_path + settings.url_forget_password

    def is_angularview(self):
        if IPloneSiteRoot.providedBy(self.context):
            return None
        else:
            return ''

    def is_siteroot(self):
        if IPloneSiteRoot.providedBy(self.context):
            return True
        else:
            return False

    def url_max_server(self):
        self.maxclient, self.settings = getUtility(IMAXClient)()
        return self.settings.max_server


    def is_activate_sharedwithme(self):
        if (api.portal.get_registry_record('base5.core.controlpanel.core.IBaseCoreControlPanelSettings.elasticsearch') != None) and (api.portal.get_registry_record('ulearn5.core.controlpanel.IUlearnControlPanelSettings.activate_sharedwithme') == True):
            portal = api.portal.get()
            if portal.portal_actions.object.local_roles.visible == False:
                portal.portal_actions.object.local_roles.visible = True
                transaction.commit()
            return True
        else:
            return False

    def is_activate_news(self):
        if api.portal.get_registry_record('ulearn5.core.controlpanel.IUlearnControlPanelSettings.activate_news') == True:
            return True
        else:
            return False


def isInstalledProduct(self, package):
    qi = getToolByName(self, 'portal_quickinstaller')
    prods = qi.listInstalledProducts()
    for prod in prods:
        if prod['id'] == package:
            return True
    return False


def getSearchersFromUser():
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
