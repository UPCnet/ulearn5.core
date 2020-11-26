from Acquisition import aq_chain
from Acquisition import aq_inner

from five import grok
from hashlib import sha1
from plone import api
from plone.app.contenttypes.interfaces import INewsItem
from plone.app.layout.viewlets.interfaces import IAboveContentTitle
from plone.app.layout.viewlets.interfaces import IPortalHeader
from plone.dexterity.interfaces import IDexterityContent
from plone.memoize.view import memoize_contextless
from plone.portlets.interfaces import IPortletAssignmentMapping
from plone.portlets.interfaces import IPortletManager
from repoze.catalog.query import Eq
from souper.soup import get_soup
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component.hooks import getSite
from zope.interface import Interface
from zope.security import checkPermission

from base5.core.adapters import IFlash
from base5.core.adapters import IImportant
from base5.core.adapters import IOutOfList
from base5.core.adapters import IShowInApp
from base5.core.utils import base_config
from ulearn5.core import _
from ulearn5.core.content.community import ICommunity
from ulearn5.core.gwuuid import IGWUUID
from ulearn5.core.interfaces import IUlearn5CoreLayer

import json


class CommunityNGDirective(grok.Viewlet):
    grok.context(Interface)
    grok.name('ulearn.communityngdirective')
    grok.viewletmanager(IPortalHeader)

    def update(self):
        self.community_hash = ''
        self.community_gwuuid = ''
        self.community_url = ''
        self.community_type = ''
        self.community_tab_view = ''
        for obj in aq_chain(self.context):
            if ICommunity.providedBy(obj):
                self.community_hash = sha1(obj.absolute_url()).hexdigest()
                self.community_gwuuid = IGWUUID(obj).get()
                self.community_url = obj.absolute_url()
                self.community_type = obj.community_type
                self.community_tab_view = obj.tab_view


class ULearnNGDirectives(grok.Viewlet):
    grok.context(Interface)
    grok.name('ulearn.ulearnngdirectives')
    grok.viewletmanager(IPortalHeader)
    grok.layer(IUlearn5CoreLayer)

    def get_communities(self):
        """ Gets the communities to show in the stats selectize dropdown
        """
        lang = api.user.get_current().getProperty('language')
        if lang not in ['ca', 'en', 'es']:
            lang = 'ca'

        pc = api.portal.get_tool('portal_catalog')
        tool = api.portal.get_tool(name='translation_service')
        all_communities = [{'hash': 'all', 'title': tool.translate(_(u'Todas las comunidades'), 'ulearn5.core', target_language=lang)}]
        all_communities += [{'hash': community.community_hash, 'title': community.Title} for community in pc.searchResults(portal_type='ulearn.community')]
        return json.dumps(all_communities)

    def get_pageviews_info(self):
        """ Gets the another options to show in the stats/pageviews selectize dropdown
        """
        lang = api.user.get_current().getProperty('language')
        if lang not in ['ca', 'en', 'es']:
            lang = 'ca'

        tool = api.portal.get_tool(name='translation_service')
        info = [{'hash': 'site', 'title': tool.translate(_(u'Todo el contenido'), 'ulearn5.core', target_language=lang)}]
        info += [{'hash': 'news', 'title': tool.translate(_(u'Noticias'), 'ulearn5.core', target_language=lang)}]
        communities = json.loads(self.get_communities())
        return json.dumps(info + communities)

    def show_extended(self):
        """ This attribute from the directive is used to show special buttons or
            links in the stats tabs. This is common in client packages.
        """
        return api.portal.get_registry_record(name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.stats_button')


class csrfNGDirective(grok.Viewlet):
    grok.context(Interface)
    grok.name('ulearn.csrfngdirective')
    grok.viewletmanager(IPortalHeader)
    grok.layer(IUlearn5CoreLayer)

    def update(self):
        self.csrf = ''
        from plone.protect.authenticator import createToken
        self.csrf = createToken()


class viewletBase(grok.Viewlet):
    grok.baseclass()

    @memoize_contextless
    def portal_url(self):
        return self.portal().absolute_url()

    @memoize_contextless
    def portal(self):
        return getSite()

    def base_config(self):
        return base_config()

    def pref_lang(self):
        """ Extracts the current language for the current user
        """
        lt = api.portal.get_tool(name='portal_languages')
        return lt.getPreferredLanguage()


class newsToolBar(viewletBase):
    grok.name('ulearn.newstoolbar')
    grok.context(INewsItem)
    grok.template('newstoolbar')
    grok.viewletmanager(IAboveContentTitle)
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

    def isNewApp(self):
        context = aq_inner(self.context)
        return IShowInApp(context).is_inapp

    def autoCheckPortletsSetted(self):
        site = getSite()
        active_portlets = []
        portlets_slots = ["plone.leftcolumn", "plone.rightcolumn",
                          "ContentWellPortlets.AbovePortletManager1", "ContentWellPortlets.AbovePortletManager2",
                          "ContentWellPortlets.AbovePortletManager3", "ContentWellPortlets.BelowPortletManager1",
                          "ContentWellPortlets.BelowPortletManager2", "ContentWellPortlets.BelowPortletManager3",
                          "ContentWellPortlets.BelowTitlePortletManager1", "ContentWellPortlets.BelowTitlePortletManager2",
                          "ContentWellPortlets.BelowTitlePortletManager3"]

        for manager_name in portlets_slots:
            if 'ContentWellPortlets' in manager_name:
                manager = getUtility(IPortletManager, name=manager_name, context=site['front-page'])
                mapping = getMultiAdapter((site['front-page'], manager), IPortletAssignmentMapping)
                [active_portlets.append(item[0]) for item in mapping.items()]
            else:
                manager = getUtility(IPortletManager, name=manager_name, context=site)
                mapping = getMultiAdapter((site, manager), IPortletAssignmentMapping)
                [active_portlets.append(item[0]) for item in mapping.items()]

        return active_portlets

    def isPortletListActivate(self):
        active_portlets = self.autoCheckPortletsSetted()
        show_news = api.portal.get_registry_record(
            name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.activate_news')
        return True if ('buttonbar' in active_portlets) and show_news else False

    def isPortletFlashActivate(self):
        active_portlets = self.autoCheckPortletsSetted()
        return True if 'flashes_informativos' in active_portlets else False

    def isPortletImportantActivate(self):
        active_portlets = self.autoCheckPortletsSetted()
        return True if 'importantnews' in active_portlets else False

    def isViewInAppChecked(self):
        show_news_in_app = api.portal.get_registry_record(
            name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.show_news_in_app')
        return show_news_in_app

    def isManagementNewsActivate(self):
        active_portlets = self.autoCheckPortletsSetted()
        if 'buttonbar' in active_portlets or 'flashes_informativos' in active_portlets or 'importantnews' in active_portlets or self.isViewInAppChecked():
            return True
        else:
            return False


class ListTagsNews(viewletBase):
    grok.name('ulearn.listtags')
    grok.context(INewsItem)
    grok.template('listtags')
    grok.viewletmanager(IAboveContentTitle)
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


class ObjectUniversalLink(viewletBase):
    grok.name('ulearn.universallink')
    grok.context(IDexterityContent)
    grok.template('universallink')
    grok.viewletmanager(IAboveContentTitle)
    grok.layer(IUlearn5CoreLayer)

    def universalLink(self):
        return api.portal.get().absolute_url() + '/resolveuid/' + self.context.UID()

    def viewViewlet(self):
        if self.context.id == 'front-page':
            return False
        return True
