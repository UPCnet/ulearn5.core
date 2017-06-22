from plone import api
from Products.Five.browser import BrowserView
from zope.component import queryUtility
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot
from ulearn5.core.controlpanel import IUlearnControlPanelSettings
from zope.component import getUtility
# from mrs.max.utilities import IMAXClient
import transaction
from ulearn5.core.controlpanel import IUlearnControlPanelSettings
import json
from souper.soup import get_soup
from repoze.catalog.query import Eq


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

def pref_lang():
    """ Extracts the current language for the current user
    """
    portal = api.portal.get()
    lt = getToolByName(portal, 'portal_languages')
    return lt.getPreferredLanguage()


def get_safe_member_by_id(username):
    """Gets user info from the repoze.catalog based user properties catalog.
       This is a safe implementation for getMemberById portal_membership to
       avoid useless searches to the LDAP server. It gets only exact matches (as
       the original does) and returns a dict. It DOES NOT return a Member
       object.
    """
    portal = api.portal.get()

    # soup = get_soup('user_properties', portal)
    # username = username.lower()
    # records = [r for r in soup.query(Eq('id', username))]
    # if records:
    #     properties = {}
    #     for attr in records[0].attrs:
    #         if records[0].attrs.get(attr, False):
    #             properties[attr] = records[0].attrs[attr]

    #     # Make sure that the key 'fullname' is returned anyway for it's used in
    #     # the wild without guards
    #     if 'fullname' not in properties:
    #         properties['fullname'] = ''

    #     return properties
    # else:
    # No such member: removed?  We return something useful anyway.
    return {'username': username, 'description': '', 'language': '',
            'home_page': '', 'name_or_id': username, 'location': '',
            'fullname': ''}

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
        # self.maxclient, self.settings = getUtility(IMAXClient)()
        #return self.settings.max_server
        return True

    def is_activate_sharedwithme(self):
        if (api.portal.get_registry_record('genweb.controlpanel.core.IGenwebCoreControlPanelSettings.elasticsearch') != None) and (api.portal.get_registry_record('ulearn5.core.controlpanel.IUlearnControlPanelSettings.activate_sharedwithme') == True):
            portal = api.portal.get()
            if portal.portal_actions.object.local_roles.visible == False:
                portal.portal_actions.object.local_roles.visible = True
                transaction.commit()
            return True
        else:
            return False
