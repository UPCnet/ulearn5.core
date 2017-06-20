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
