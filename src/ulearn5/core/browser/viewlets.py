from five import grok
from hashlib import sha1
from plone import api
from Acquisition import aq_inner
from zope.interface import Interface
from zope.component.hooks import getSite
from zope.security import checkPermission
from plone.app.layout.viewlets.interfaces import IPortalHeader

from ulearn5.core.gwuuid import IGWUUID
from ulearn5.core.content.community import ICommunity
from ulearn5.core import _
from Acquisition import aq_chain

from plone.app.contenttypes.interfaces import INewsItem
from plone.app.layout.viewlets.interfaces import IAboveContentTitle
from plone.memoize.view import memoize_contextless
from Products.CMFCore.utils import getToolByName
from base5.core.adapters import IImportant
from base5.core.adapters import IFlash
from base5.core.adapters import IOutOfList
from base5.core.utils import genweb_config

from ulearn5.core.interfaces import IUlearn5CoreLayer
from souper.soup import get_soup
from repoze.catalog.query import Eq
import json

from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletAssignmentMapping
from zope.component import getUtility, getMultiAdapter


class CommunityNGDirective(grok.Viewlet):
    grok.context(Interface)
    grok.name('ulearn.communityngdirective')
    grok.viewletmanager(IPortalHeader)

    def update(self):
        self.community_hash = ''
        self.community_gwuuid = ''
        self.community_url = ''
        self.community_type = ''
        for obj in aq_chain(self.context):
            if ICommunity.providedBy(obj):
                self.community_hash = sha1(obj.absolute_url()).hexdigest()
                self.community_gwuuid = IGWUUID(obj).get()
                self.community_url = obj.absolute_url()
                self.community_type = obj.community_type


class ULearnNGDirectives(grok.Viewlet):
    grok.context(Interface)
    grok.name('ulearn.ulearnngdirectives')
    grok.viewletmanager(IPortalHeader)
    grok.layer(IUlearn5CoreLayer)

    def get_communities(self):
        """ Gets the communities to show in the stats selectize dropdown
        """
        pc = api.portal.get_tool('portal_catalog')
        all_communities = [{'hash': 'all', 'title': _(u'Todas las comunidades')}]
        all_communities += [{'hash': community.community_hash, 'title': community.Title} for community in pc.searchResults(portal_type='ulearn.community')]
        return json.dumps(all_communities)

    def show_extended(self):
        """ This attribute from the directive is used to show special buttons or
            links in the stats tabs. This is common in client packages.
        """
        return api.portal.get_registry_record(name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.stats_button')


class viewletBase(grok.Viewlet):
    grok.baseclass()

    @memoize_contextless
    def portal_url(self):
        return self.portal().absolute_url()

    @memoize_contextless
    def portal(self):
        return getSite()

    def genweb_config(self):
        return genweb_config()

    def pref_lang(self):
        """ Extracts the current language for the current user
        """
        lt = getToolByName(self.portal(), 'portal_languages')
        return lt.getPreferredLanguage()


class newsToolBar(viewletBase):
    grok.name('ulearn.newstoolbar')
    grok.context(INewsItem)
    grok.template('newstoolbar')
    grok.viewletmanager(IAboveContentTitle)
    grok.layer(IUlearn5CoreLayer)
    grok.require('cmf.ModifyPortalContent')

    def permisos_important(self):
        # TODO: Comprovar que l'usuari tingui permisos per a marcar com a important
        return not IImportant(self.context).is_important and checkPermission("plone.app.controlpanel.Overview", self.portal())

    def permisos_notimportant(self):
        # TODO: Comprovar que l'usuari tingui permisos per a marcar com a notimportant
        return IImportant(self.context).is_important and checkPermission("plone.app.controlpanel.Overview", self.portal())

    def canManageSite(self):
        return checkPermission("plone.app.controlpanel.Overview", self.portal())

    def isNewImportant(self):
        context = aq_inner(self.context)
        is_important = IImportant(context).is_important
        return is_important

    def permisos_flash(self):
        # TODO: Comprovar que l'usuari tingui permisos per a marcar com a important
        return not IFlash(self.context).is_flash and checkPermission("plone.app.controlpanel.Overview", self.portal())

    def permisos_notflash(self):
        # TODO: Comprovar que l'usuari tingui permisos per a marcar com a notimportant
        return IFlash(self.context).is_flash and checkPermission("plone.app.controlpanel.Overview", self.portal())

    def isNewFlash(self):
        context = aq_inner(self.context)
        is_flash = IFlash(context).is_flash
        return is_flash

    def permisos_outoflist(self):
        # TODO: Comprovar que l'usuari tingui permisos per a marcar com a important
        return not IOutOfList(self.context).is_outoflist and checkPermission("plone.app.controlpanel.Overview", self.portal())

    def permisos_notoutoflist(self):
        # TODO: Comprovar que l'usuari tingui permisos per a marcar com a notimportant
        return IOutOfList(self.context).is_outoflist and checkPermission("plone.app.controlpanel.Overview", self.portal())

    def isNewOutOfList(self):
        context = aq_inner(self.context)
        is_outoflist = IOutOfList(context).is_outoflist
        return is_outoflist

    def getListOfPortlets(self):
        site = getSite()
        activate_portlets = []
        portlets_slots = ["plone.leftcolumn", "plone.rightcolumn",
                          "genweb.portlets.HomePortletManager1", "genweb.portlets.HomePortletManager2",
                          "genweb.portlets.HomePortletManager3", "genweb.portlets.HomePortletManager4",
                          "genweb.portlets.HomePortletManager5", "genweb.portlets.HomePortletManager6",
                          "genweb.portlets.HomePortletManager7", "genweb.portlets.HomePortletManager8",
                          "genweb.portlets.HomePortletManager9", "genweb.portlets.HomePortletManager10"]

        for manager_name in portlets_slots:
            if 'genweb' in manager_name:
                manager = getUtility(IPortletManager, name=manager_name, context=site['front-page'])
                mapping = getMultiAdapter((site['front-page'], manager), IPortletAssignmentMapping)
                [activate_portlets.append(item[0]) for item in mapping.items()]
            else:
                manager = getUtility(IPortletManager, name=manager_name, context=site)
                mapping = getMultiAdapter((site, manager), IPortletAssignmentMapping)
                [activate_portlets.append(item[0]) for item in mapping.items()]
        return activate_portlets

    def isPortletListActivate(self):
        activate_portlets = self.getListOfPortlets()
        return True if 'my-subscribed-news' in activate_portlets else False

    def isPortletFlashActivate(self):
        activate_portlets = self.getListOfPortlets()
        return True if 'flashesinformativos' in activate_portlets else False

    def isPortletImportantActivate(self):
        activate_portlets = self.getListOfPortlets()
        return True if 'importantnews' in activate_portlets else False

    def isManagementNewsActivate(self):
        activate_portlets = self.getListOfPortlets()
        if 'my-subscribed-news' in activate_portlets or 'flashesinformativos' in activate_portlets or 'importantnews' in activate_portlets:
            return True
        else:
            return False


class ListTagsNews(viewletBase):
    grok.name('genweb.listtags')
    grok.context(INewsItem)
    grok.template('listtags')
    grok.viewletmanager(IAboveContentTitle)
    # grok.require('base.authenticated')
    grok.layer(IUlearn5CoreLayer)

    def isTagFollowed(self, category):
        portal = getSite()
        current_user = api.user.get_current()
        userid = current_user.id

        soup_tags = get_soup('user_subscribed_tags', portal)
        tags_soup = [r for r in soup_tags.query(Eq('id', userid))]
        if tags_soup:
            tags = tags_soup[0].attrs['tags']
            return True if category in tags else False
        else:
            return False
