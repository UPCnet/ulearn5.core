# -*- coding: utf-8 -*-
from Acquisition import aq_inner
from Products.CMFPlone.interfaces import ILanguageSchema
from Products.CMFPlone.interfaces import IPloneSiteRoot
from Products.CMFPlone.interfaces import ISearchSchema
from Products.CMFPlone.interfaces.constrains import ISelectableConstrainTypes
from Products.CMFPlone.interfaces.controlpanel import ISiteSchema
from Products.CMFPlone.interfaces.syndication import ISiteSyndicationSettings

from datetime import datetime
from five import grok
from mimetypes import MimeTypes
from plone import api
from plone.app.discussion.interfaces import IDiscussionSettings
from plone.app.layout.navigation.root import getNavigationRootObject
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from plone.namedfile.file import NamedBlobImage
from plone.portlets.interfaces import IPortletAssignmentMapping
from plone.portlets.interfaces import IPortletManager
from plone.registry.interfaces import IRegistry
from repoze.catalog.query import Eq
from souper.soup import get_soup
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.hooks import getSite
from zope.interface import Interface
from zope.interface import alsoProvides

from base5.core.adapters.favorites import IFavorite
from base5.core.utilities import IElasticSearch
from base5.core.utils import add_user_to_catalog
from base5.core.utils import get_all_user_properties
from base5.core.utils import json_response
from base5.core.utils import remove_user_from_catalog
from base5.portlets.browser.manager import IColStorage
from mrs5.max.utilities import IMAXClient
from ulearn5.core.api import api_resource
from ulearn5.core.api.people import Person
from ulearn5.core.browser.sharing import ElasticSharing
from ulearn5.core.browser.sharing import IElasticSharing
from ulearn5.core.content.community import ICommunity
from ulearn5.core.content.community import ICommunityACL
from ulearn5.core.controlpanel import IUlearnControlPanelSettings
from ulearn5.core.gwuuid import ATTRIBUTE_NAME
from ulearn5.core.gwuuid import IGWUUID
from ulearn5.core.setuphandlers import setup_ulearn_portlets
from ulearn5.core.utils import is_activate_owncloud, is_activate_externalstorage, is_activate_etherpad
from ulearn5.owncloud.api.owncloud import HTTPResponseError
from ulearn5.owncloud.api.owncloud import OCSResponseError
from ulearn5.owncloud.utilities import IOwncloudClient
from ulearn5.owncloud.utils import get_domain
from ulearn5.owncloud.utils import update_owncloud_permission

import base64
import json
import logging
import os
import requests
import shutil
import subprocess
import time
import transaction


ATTRIBUTE_NAME_FAVORITE = '_favoritedBy'

logger = logging.getLogger(__name__)


grok.templatedir("views_templates")
NEWS_QUERY = [{'i': u'portal_type', 'o': u'plone.app.querystring.operation.selection.any', 'v': [u'News Item']},
              {'i': u'review_state', 'o': u'plone.app.querystring.operation.selection.any', 'v': [u'published', u'intranet', u'esborrany']},
              {'i': u'path', 'o': u'plone.app.querystring.operation.string.relativePath', 'v': u'..'}]
QUERY_SORT_ON = u'effective'


def createOrGetObject(context, newid, title, type_name):
    if newid in context.contentIds():
        obj = context[newid]
    else:
        obj = createContentInContainer(context, type_name, title=title, checkConstrains=False)
        transaction.savepoint()
        if obj.id != newid:
            context.manage_renameObject(obj.id, newid)
        obj.reindexObject()
    return obj


def newPrivateFolder(context, newid, title):
    return createOrGetObject(context, newid, title, u'privateFolder')


class debug(grok.View):
    """ Convenience view for faster debugging. Needs to be manager. """
    grok.context(Interface)
    grok.require('cmf.ManagePortal')

    def render(self):
        import ipdb; ipdb.set_trace()  # Magic! Do not delete!!! :)


class setupHomePage(grok.View):
    """ Add the portlets and add the values of settings """
    grok.context(IPloneSiteRoot)
    grok.require('zope2.ViewManagementScreens')

    def render(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass
        portal = getSite()
        frontpage = portal['front-page']
        frontpage.description = u''
        from plone.app.textfield.value import RichTextValue
        frontpage.text = RichTextValue(u'', 'text/plain', 'text/html')
        wftool = api.portal.get_tool(name='portal_workflow')
        wftool.doActionFor(frontpage, 'reject')
        wftool.doActionFor(frontpage, 'publishtointranet')
        frontpage._Delete_objects_Permission = ('Site Administrator','Manager',)
        transaction.commit()

        # Delete original 'aggregator' collection from 'News' folder
        if getattr(portal['news'], 'aggregator', False):
                api.content.delete(obj=portal['news']['aggregator'])

        # Create the aggregator with new criteria
        col_news = self.create_content(portal['news'], 'Collection', 'aggregator', title='aggregator', description=u'Site news')
        col_news.title = 'News'
        col_news.query = NEWS_QUERY
        col_news.sort_on = QUERY_SORT_ON
        col_news.sort_reversed = True
        col_news.item_count = 10
        col_news._Delete_objects_Permission = ('Site Administrator','Manager',)
        col_news.reindexObject()

        # Set default view from aggregator
        portal['news']['aggregator'].setLayout('collection_news_view')

        # Set default page from 'News' folder
        portal['news'].setDefaultPage('aggregator')
        portal['news']._Delete_objects_Permission = ('Site Administrator','Manager',)

        from plone.portlets.interfaces import ILocalPortletAssignmentManager
        from plone.portlets.constants import CONTEXT_CATEGORY

        # Get the proper portlet manager
        manager = getUtility(IPortletManager, name=u"plone.rightcolumn")
        # Get the current blacklist for the location
        blacklist = getMultiAdapter((self.context, manager), ILocalPortletAssignmentManager)
        # Turn off the manager
        blacklist.setBlacklistStatus(CONTEXT_CATEGORY, True)

        # Get the proper portlet manager
        manager = getUtility(IPortletManager, name=u"plone.footerportlets")
        # Get the current blacklist for the location
        blacklist = getMultiAdapter((self.context, manager), ILocalPortletAssignmentManager)
        # Turn off the manager
        blacklist.setBlacklistStatus(CONTEXT_CATEGORY, True)

        # Get the proper portlet manager
        manager = getUtility(IPortletManager, name=u"plone.leftcolumn")
        # Get the current blacklist for the location
        blacklist = getMultiAdapter((frontpage, manager), ILocalPortletAssignmentManager)
        # Turn off the manager
        blacklist.setBlacklistStatus(CONTEXT_CATEGORY, True)

        from zope.container.interfaces import INameChooser
        from ulearn5.theme.portlets.profile.profile import Assignment as profileAssignment
        from ulearn5.theme.portlets.communities import Assignment as communitiesAssignment
        from ulearn5.theme.portlets.thinnkers import Assignment as thinnkersAssignment
        from mrs5.max.portlets.maxui import Assignment as maxAssignment
        from mrs5.max.portlets.maxuichat import Assignment as chatAssignment
        from ulearn5.theme.portlets.buttonbar.buttonbar import Assignment as buttonbarAssignment
        from ulearn5.theme.portlets.calendar import Assignment as calendarAssignment
        from ulearn5.theme.portlets.angularrouteview import Assignment as angularrouteviewAssignment

        # Add portlets programatically
        column = getUtility(IPortletManager, name='ContentWellPortlets.BelowTitlePortletManager1')
        manager = getMultiAdapter((frontpage, column), IPortletAssignmentMapping)
        for portlet in manager:
            del manager[portlet]
        chooser = INameChooser(manager)
        manager[chooser.chooseName(None, profileAssignment())] = profileAssignment()
        manager[chooser.chooseName(None, communitiesAssignment())] = communitiesAssignment()
        manager[chooser.chooseName(None, chatAssignment())] = chatAssignment()
        manager[chooser.chooseName(None, thinnkersAssignment())] = thinnkersAssignment()

        column = getUtility(IPortletManager, name='ContentWellPortlets.BelowTitlePortletManager2')
        manager = getMultiAdapter((frontpage, column), IPortletAssignmentMapping)
        for portlet in manager:
            del manager[portlet]
        chooser = INameChooser(manager)
        manager[chooser.chooseName(None, angularrouteviewAssignment())] = angularrouteviewAssignment()
        manager[chooser.chooseName(None, buttonbarAssignment())] = buttonbarAssignment()
        manager[chooser.chooseName(None, maxAssignment())] = maxAssignment()

        column = getUtility(IPortletManager, name='ContentWellPortlets.BelowTitlePortletManager3')
        manager = getMultiAdapter((frontpage, column), IPortletAssignmentMapping)
        for portlet in manager:
            del manager[portlet]
        chooser = INameChooser(manager)
        manager[chooser.chooseName(None, calendarAssignment())] = calendarAssignment()

        portletManager = getUtility(IPortletManager, 'ContentWellPortlets.BelowTitlePortletManager1')
        colstorage = getMultiAdapter((frontpage, portletManager), IColStorage)
        colstorage.col = '3'

        portletManager = getUtility(IPortletManager, 'ContentWellPortlets.BelowTitlePortletManager2')
        colstorage = getMultiAdapter((frontpage, portletManager), IColStorage)
        colstorage.col = '6'

        portletManager = getUtility(IPortletManager, 'ContentWellPortlets.BelowTitlePortletManager3')
        colstorage = getMultiAdapter((frontpage, portletManager), IColStorage)
        colstorage.col = '3'

        setup_ulearn_portlets()

        registry = queryUtility(IRegistry)
        settings = registry.forInterface(ISiteSyndicationSettings)
        settings.allowed = True
        settings.default_enabled = True
        settings.search_rss_enabled = True
        settings.show_author_info = True
        settings.render_body = True
        settings.show_syndication_button = True
        settings.show_syndication_link = True

        # Cookies
        lan_tool = registry.forInterface(ILanguageSchema, prefix='plone')
        lan_tool.use_cookie_negotiation = True

        # Toolbar position
        site_tool = registry.forInterface(ISiteSchema, prefix='plone')
        site_tool.toolbar_position = 'top'

        # Enabled comments globally
        discussion_tool = registry.forInterface(IDiscussionSettings)
        discussion_tool.globally_enabled = True

        # Livesearch
        search_tool = registry.forInterface(ISearchSchema, prefix='plone')
        search_tool.search_results_description_length = 140

        # Types permited in news folder
        news_tool = ISelectableConstrainTypes(portal['news'])
        news_tool.setLocallyAllowedTypes(('News Item', 'Folder', 'Collection',))
        news_tool.setImmediatelyAddableTypes(('News Item', 'Folder', 'Collection',))
        transaction.commit()

        return 'Done'

    def create_content(self, container, portal_type, id, publish=True, **kwargs):
        if not getattr(container, id, False):
            createContentInContainer(container, portal_type, checkConstraints=False, **kwargs)
        return getattr(container, id)


class createMenuFolders(grok.View):
    """ Create the directory structure of the menu """
    grok.context(IPloneSiteRoot)
    grok.require('zope2.ViewManagementScreens')

    def render(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        portal = getSite()
        gestion = newPrivateFolder(portal, 'gestion', u'Gestión')
        gestion.exclude_from_nav = False
        gestion.setLayout('folder_listing')
        behavior = ISelectableConstrainTypes(gestion)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(('Folder', 'privateFolder',))
        behavior.setImmediatelyAddableTypes(('Folder', 'privateFolder',))
        gestion._Delete_objects_Permission = ('Site Administrator', 'Manager',)

        enlaces_cabecera = newPrivateFolder(gestion, 'menu', u'Menu')
        enlaces_cabecera.exclude_from_nav = False
        enlaces_cabecera._Delete_objects_Permission = ('Site Administrator', 'Manager',)
        enlaces_cabecera.reindexObject()

        for language in api.portal.get_tool(name='portal_languages').getSupportedLanguages():
            language_folder = newPrivateFolder(enlaces_cabecera, language, language)
            language_folder.exclude_from_nav = False
            language_folder._Delete_objects_Permission = ('Site Administrator', 'Manager',)
            language_folder.reindexObject()
            behavior = ISelectableConstrainTypes(language_folder)
            behavior.setConstrainTypesMode(1)
            behavior.setLocallyAllowedTypes(('Folder', 'privateFolder',))
            behavior.setImmediatelyAddableTypes(('Folder', 'privateFolder',))

        transaction.commit()
        return 'Done'


class createCustomizedHeaderFolder(grok.View):
    """ Create the directory structure of the customized header """
    grok.context(IPloneSiteRoot)
    grok.require('zope2.ViewManagementScreens')

    def render(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        portal = getSite()
        gestion = newPrivateFolder(portal, 'gestion', u'Gestión')
        gestion.exclude_from_nav = False
        gestion.setLayout('folder_listing')
        behavior = ISelectableConstrainTypes(gestion)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(('Folder', 'privateFolder',))
        behavior.setImmediatelyAddableTypes(('Folder', 'privateFolder',))
        gestion._Delete_objects_Permission = ('Site Administrator','Manager',)

        description = u'La capçalera utilitzarà la primera imatge del directori, aquesta imatge ha de tenir una alçada de 83px. \nLa cabecera utilizará la primera imagen del directorio, esta imagen tiene que tener una altura de 83px. \nThe header will use the first image of the directory, this image must have a height of 83px.'

        header = newPrivateFolder(gestion, 'header', u'Header')
        header.exclude_from_nav = False
        header.setLayout('folder_listing')
        behavior = ISelectableConstrainTypes(header)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(('Folder', 'privateFolder',))
        behavior.setImmediatelyAddableTypes(('Folder', 'privateFolder',))
        header._Delete_objects_Permission = ('Site Administrator','Manager',)

        for language in api.portal.get_tool(name='portal_languages').getSupportedLanguages():
            language_folder = newPrivateFolder(header, language, language)
            language_folder.exclude_from_nav = False
            language_folder.setLayout('folder_listing')
            language_folder.description = description
            language_folder._Delete_objects_Permission = ('Site Administrator','Manager',)
            language_folder.reindexObject()
            behavior = ISelectableConstrainTypes(language_folder)
            behavior.setConstrainTypesMode(1)
            behavior.setLocallyAllowedTypes(('Image',))
            behavior.setImmediatelyAddableTypes(('Image',))

        header.reindexObject()
        return 'Done'



class createCustomizedFooterFolder(grok.View):
    """ Create the directory structure of the customized footer """
    grok.context(IPloneSiteRoot)
    grok.require('zope2.ViewManagementScreens')

    def render(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        description = u'El peu de pàgina utilizarà el primer document del directori.\nEl pie de página utilizará el primer documento del directorio.\nThe footer will use the first document in the directory.'

        portal = getSite()
        gestion = newPrivateFolder(portal, 'gestion', u'Gestión')
        gestion.exclude_from_nav = False
        gestion.setLayout('folder_listing')
        behavior = ISelectableConstrainTypes(gestion)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(('Folder', 'privateFolder',))
        behavior.setImmediatelyAddableTypes(('Folder', 'privateFolder',))
        gestion._Delete_objects_Permission = ('Site Administrator','Manager',)

        footer = newPrivateFolder(gestion, 'footer', u'Footer')
        footer.exclude_from_nav = False
        footer.setLayout('folder_listing')
        behavior = ISelectableConstrainTypes(footer)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(('Folder', 'privateFolder',))
        behavior.setImmediatelyAddableTypes(('Folder', 'privateFolder',))
        footer._Delete_objects_Permission = ('Site Administrator','Manager',)

        for language in api.portal.get_tool(name='portal_languages').getSupportedLanguages():
            language_folder = newPrivateFolder(footer, language, language)
            language_folder.exclude_from_nav = False
            language_folder.setLayout('folder_listing')
            language_folder.description = description
            language_folder._Delete_objects_Permission = ('Site Administrator','Manager',)
            language_folder.reindexObject()
            behavior = ISelectableConstrainTypes(language_folder)
            behavior.setConstrainTypesMode(1)
            behavior.setLocallyAllowedTypes(('Document',))
            behavior.setImmediatelyAddableTypes(('Document',))

        footer.reindexObject()
        return 'Done'


class createBannersFolder(grok.View):
    """ Create the directory banners in gestion """
    grok.context(IPloneSiteRoot)
    grok.require('zope2.ViewManagementScreens')

    def render(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        portal = getSite()
        gestion = newPrivateFolder(portal, 'gestion', u'Gestión')
        gestion.exclude_from_nav = False
        gestion.setLayout('folder_listing')
        behavior = ISelectableConstrainTypes(gestion)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(('Folder', 'privateFolder',))
        behavior.setImmediatelyAddableTypes(('Folder', 'privateFolder',))
        gestion._Delete_objects_Permission = ('Site Administrator','Manager',)

        banners = newPrivateFolder(gestion, 'banners', u'Banners')
        banners.exclude_from_nav = False
        banners.setLayout('folder_listing')
        behavior = ISelectableConstrainTypes(banners)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(('ulearn.banner',))
        behavior.setImmediatelyAddableTypes(('ulearn.banner',))
        banners._Delete_objects_Permission = ('Site Administrator','Manager',)

        transaction.commit()
        return 'Done'


class createPersonalBannerFolder(grok.View):
    """ Create the directory banners in personal folder """
    grok.context(IPloneSiteRoot)
    grok.require('zope2.ViewManagementScreens')

    def createOrGetObject(self, context, newid, title, type_name):
        if newid in context.contentIds():
            obj = context[newid]
        else:
            obj = createContentInContainer(context, type_name, title=title, checkConstrains=False)
            transaction.savepoint()
            if obj.id != newid:
                context.manage_renameObject(obj.id, newid)
            obj.reindexObject()
        return obj

    def render(self):
        # /createPersonalBannerFolder?user=nom.cognom
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        if 'user' in self.request.form:
            userid = self.request.form['user']
            user = api.user.get(username=userid)
            if user:
                portal = getSite()
                perFolder = self.createOrGetObject(portal['Members'], userid, userid, u'privateFolder')
                perFolder.exclude_from_nav = False
                perFolder.setLayout('folder_listing')
                behavior = ISelectableConstrainTypes(perFolder)
                behavior.setConstrainTypesMode(1)
                behavior.setLocallyAllowedTypes(('Folder',))
                behavior.setImmediatelyAddableTypes(('Folder',))
                perFolder._Delete_objects_Permission = ('Site Administrator','Manager',)

                api.content.disable_roles_acquisition(perFolder)
                for username, roles in perFolder.get_local_roles():
                    perFolder.manage_delLocalRoles([username])
                perFolder.manage_setLocalRoles(userid, ['Contributor', 'Editor', 'Reader'])

                banFolder = self.createOrGetObject(perFolder, 'banners', 'Banners', u'Folder')
                banFolder.exclude_from_nav = False
                banFolder.setLayout('folder_listing')
                behavior = ISelectableConstrainTypes(banFolder)
                behavior.setConstrainTypesMode(1)
                behavior.setLocallyAllowedTypes(('ulearn.banner',))
                behavior.setImmediatelyAddableTypes(('ulearn.banner',))
                banFolder._Delete_objects_Permission = ('Site Administrator','Manager',)

                transaction.commit()
                return 'Done' + ', ' + userid + '.'
            else:
                return 'Error, user ' + userid + ' not exist.'
        else:
            return 'Error add user parameter - /createPersonalBannerFolder?user=user.name'


class ldapkillah(grok.View):
    grok.context(IPloneSiteRoot)
    grok.require('zope2.ViewManagementScreens')

    def render(self):
        portal = getSite()

        if getattr(portal.acl_users, 'ldapUPC', None):
            portal.acl_users.manage_delObjects('ldapUPC')

        if getattr(portal.acl_users, 'ldapexterns', None):
            portal.acl_users.manage_delObjects('ldapexterns')


class memberFolderSetup(grok.View):
    grok.context(IPloneSiteRoot)
    grok.require('zope2.ViewManagementScreens')

    def render(self):
        portal = getSite()
        if not getattr(portal, 'users', None):
            users_folder = createContentInContainer(portal, 'Folder', title='users', checkConstraints=False)
            users_folder.setDefaultPage('member_search_form')
            portal.manage_delObjects('Members')


class changeURLCommunities(grok.View):
    """ Aquesta vista canvia la url de les comunitats """
    grok.name('changeurlcommunities')
    grok.template('changeurlcommunities')
    grok.context(IPloneSiteRoot)

    #render = ViewPageTemplateFile('views_templates/changeurlcommunities.pt')

    def update(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass
        if self.request.environ['REQUEST_METHOD'] == 'POST':
            pc = api.portal.get_tool('portal_catalog')
            communities = pc.searchResults(portal_type='ulearn.community')

            if self.request.form['url'] != '':
                url_nova = self.request.form['url']
                url_antiga = self.request.form['url_antiga']
                logger.info('Buscant comunitats per modificar la url')

                for brain in communities:
                    obj = brain.getObject()
                    community = obj.adapted()
                    community_url = url_antiga + '/' + obj.id
                    community_url_nova = url_nova + '/' + obj.id
                    properties_to_update = dict(url=community_url_nova)

                    community.maxclient.contexts[community_url].put(**properties_to_update)
                    logger.info('Comunitat amb url {} actualitzada per {}'.format(community_url, community_url_nova))


class deleteUsers(grok.View):
    """ Delete users from the plone & max & communities """
    grok.name('deleteusers')
    grok.template('deleteusers')
    grok.context(IPloneSiteRoot)

    #render = ViewPageTemplateFile('views_templates/deleteusers.pt')

    def update(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass
        if self.request.environ['REQUEST_METHOD'] == 'POST':

            if self.request.form['users'] != '':
                users = self.request.form['users'].split(',')

                for user in users:
                    user = user.strip()
                    try:
                        person = Person(self.context, [user])
                        person.deleteMembers([user])
                        remove_user_from_catalog(user.lower())
                        pc = api.portal.get_tool(name='portal_catalog')
                        username = user

                        maxclient, settings = getUtility(IMAXClient)()
                        maxclient.setActor(settings.max_restricted_username)
                        maxclient.setToken(settings.max_restricted_token)

                        communities_subscription = maxclient.people[username].subscriptions.get()

                        if communities_subscription != []:

                            for num, community_subscription in enumerate(communities_subscription):
                                community = pc.unrestrictedSearchResults(portal_type="ulearn.community", community_hash=community_subscription['hash'])
                                try:
                                    obj = community[0]._unrestrictedGetObject()
                                    logger.info('Processant {} de {}. Comunitat {}'.format(num, len(communities_subscription), obj))
                                    gwuuid = IGWUUID(obj).get()
                                    portal = api.portal.get()
                                    soup = get_soup('communities_acl', portal)

                                    records = [r for r in soup.query(Eq('gwuuid', gwuuid))]

                                    # Save ACL into the communities_acl soup
                                    if records:
                                        acl_record = records[0]
                                        acl = acl_record.attrs['acl']
                                        exist = [a for a in acl['users'] if a['id'] == unicode(username)]
                                        if exist:
                                            acl['users'].remove(exist[0])
                                            acl_record.attrs['acl'] = acl
                                            soup.reindex(records=[acl_record])
                                            adapter = obj.adapted()
                                            adapter.set_plone_permissions(adapter.get_acl())

                                except:
                                    continue

                        try:
                            maxclient.people[username].delete()
                        except:
                            # No existe el usuari en max
                            pass
                        logger.info('Delete user: {}'.format(user))
                    except:
                        logger.error('User not deleted: {}'.format(user))
                        pass

                logger.info('Finished deleted users: {}'.format(users))

class deleteUsersInCommunities(grok.View):
    """ Delete users from the plone & max & communities """
    grok.name('deleteusersincommunities')
    grok.template('deleteusersincommunities')
    grok.context(IPloneSiteRoot)

    # render = ViewPageTemplateFile('views_templates/deleteusersincommunities.pt')

    def update(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        if self.request.environ['REQUEST_METHOD'] == 'POST':

            if self.request.form['users'] != '':
                users = self.request.form['users'].split(',')

                for user in users:
                    user = user.strip()
                    try:
                        pc = api.portal.get_tool(name='portal_catalog')
                        username = user
                        comunnities = pc.unrestrictedSearchResults(portal_type="ulearn.community")
                        for num, community in enumerate(comunnities):
                            obj = community._unrestrictedGetObject()
                            logger.info('Processant {} de {}. Comunitat {}'.format(num, len(comunnities), obj))
                            gwuuid = IGWUUID(obj).get()
                            portal = api.portal.get()
                            soup = get_soup('communities_acl', portal)

                            records = [r for r in soup.query(Eq('gwuuid', gwuuid))]

                            # Save ACL into the communities_acl soup
                            if records:
                                acl_record = records[0]
                                acl = acl_record.attrs['acl']
                                exist = [a for a in acl['users'] if a['id'] == unicode(username)]
                                if exist:
                                    acl['users'].remove(exist[0])
                                    acl_record.attrs['acl'] = acl
                                    soup.reindex(records=[acl_record])
                                    adapter = obj.adapted()
                                    adapter.set_plone_permissions(adapter.get_acl())

                        logger.info('Delete user in communities: {}'.format(user))
                    except:
                        logger.error('User not deleted in communities: {}'.format(user))
                        pass

                logger.info('Finished deleted users in communities: {}'.format(users))


def getDestinationFolder(stats_folder,create_month=True):
    """
    This function creates if it doesn't exist a folder in <stats_folder>/<year>/<month>.
    If  create_month is False, then only the <year> folder is created
    """
    portal = api.portal.get()
    #setSite(portal)
    # Create 'stats_folder' folder if not exists
    if portal.get(stats_folder) is None:
        makeFolder(portal, stats_folder)
    portal = portal.get(stats_folder)
    today = datetime.now()
    context = aq_inner(portal)
#    tool = api.portal.get_tool(name='translation_service')
#    month = tool.translate(today.strftime("%B"), 'ulearn', context=context).encode()
    month = 'march'
    month = month.lower()
    year = today.strftime("%G")
    # Create year folder and month folder if not exists
    if portal.get(year) is None:
        makeFolder(portal, year)
        if create_month:
            portal = portal.get(year)
            makeFolder(portal, month)
    # Create month folder if not exists
    else:
        portal = portal.get(year)
        if portal.get(month) is None and create_month:
            makeFolder(portal, month)
            portal = portal.get(month)
    return portal


def makeFolder(portal, name):
    transaction.begin()
    obj = createContentInContainer(portal, 'Folder', id='{}'.format(name), title='{}'.format(name), description='{}'.format(name))
    obj.reindexObject()
    transaction.commit()


class ImportFileToFolder(grok.View):
    """  This view takes 2 arguments on the request GET data :
folder: the path without the '/' at the beginning, which is the base folder
    where the 'year' folders should be created
local_file: the complete path and filename of the file on server. Be carefully if the view is called
    and there are many instanes. The best way is to call it through <ip>:<instance_port>

To test it: run python script with requests and:
payload={'folder':'test','local_file': '/home/vicente.iranzo/mongodb_VPN_2016_upcnet.xls'}
r = requests.get('http://localhost:8080/Plone/importfiletofolder', params=payload, auth=HTTPBasicAuth('admin', 'admin')) """
    grok.context(IPloneSiteRoot)
    grok.name('importfiletofolder')
    grok.require('base.webmaster')

    def update(self):
        folder_name = self.request.get("folder")
        local_file = self.request.get("local_file")

        f = open(local_file, 'r')
        content = f.read()
        f.close()

        plone_folder = getDestinationFolder(folder_name, create_month=False)
        from plone.protect.interfaces import IDisableCSRFProtection
        from zope.interface import alsoProvides
        alsoProvides(self.request, IDisableCSRFProtection)
        file = NamedBlobFile(
            data=content,
            filename=u'{}'.format(local_file),
            contentType='application/xls'
            )
        obj = createContentInContainer(
            plone_folder,
            'AppFile',
            id='{}'.format(local_file.split('/')[-1]),
            title='{}'.format(local_file.split('/')[-1]),
            file=file,
            checkConstraints=False
            )
        self.response.setBody('OK')


class updateSharingCommunityElastic(grok.View):
    """ Aquesta vista actualitza tots els objectes de la comunitat al elasticsearch """
    grok.name('updatesharingcommunityelastic')
    grok.template('updatesharingcommunityelastic')
    grok.context(IPloneSiteRoot)

    # render = ViewPageTemplateFile('views_templates/updatesharingcommunityelastic.pt')

    def update(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass
        if self.request.environ['REQUEST_METHOD'] == 'POST':
            pc = api.portal.get_tool('portal_catalog')
            portal = getSite()
            absolute_path = '/'.join(portal.getPhysicalPath())

            if self.request.form['id'] != '':
                id_community = absolute_path + '/' + self.request.form['id']
                logger.info('Actualitzant elasticsearch dades comunitat {}'.format(id_community))
                community = pc.unrestrictedSearchResults(path=id_community)

                if community:
                    obj = community[0]._unrestrictedGetObject()

                elastic_index = ElasticSharing().get_index_name().lower()
                try:
                    self.elastic = getUtility(IElasticSearch)
                    self.elastic().search(index=elastic_index)
                except:
                    self.elastic().indices.create(
                        index=elastic_index,
                        body={
                            'mappings': {
                                'sharing': {
                                    'properties': {
                                        'path': {'type': 'string'},
                                        'principal': {'type': 'string', 'index': 'not_analyzed' },
                                        'roles': {'type': 'string'},
                                        'uuid': {'type': 'string'}
                                        }
                                    }
                                }
                            }
                        )

                for brain in community:
                    obj = brain._unrestrictedGetObject()
                    if not ICommunity.providedBy(obj):
                        elastic_sharing = queryUtility(IElasticSharing)
                        elastic_sharing.modified(obj)
                        logger.info('Actualitzat el objecte {} de la comunitat {}'.format(obj, id_community))


class listAllCommunitiesObjects(grok.View):
    """ returns a json with all the comunities and the number of objects of each one"""
    grok.name('listallcommunitiesobjects')
    grok.context(IPloneSiteRoot)
    # only for admin users
    grok.require('cmf.ManagePortal')

    def render(self):
        pc = api.portal.get_tool(name='portal_catalog')
        communities = pc.unrestrictedSearchResults(portal_type="ulearn.community")
        result_list = []
        for num, community in enumerate(communities):
            num_docs = len(pc(path={"query": community.getPath(), "depth": 2}))
            new_com = {"community_name": community.getPath(),
                       "community_docs": str(num_docs),
                       }
            result_list.append(new_com)
        return json.dumps(result_list)

class updateSharingCommunitiesElastic(grok.View):
    """ Aquesta vista actualitza el sharing de tots els objectes de totes les comunitats al elasticsearch """
    grok.name('updatesharingcommunitieselastic')
    grok.context(IPloneSiteRoot)

    def render(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        pc = api.portal.get_tool('portal_catalog')
        portal = getSite()
        absolute_path = '/'.join(portal.getPhysicalPath())

        comunnities = pc.unrestrictedSearchResults(portal_type="ulearn.community")
        for num, community in enumerate(comunnities):
            obj = community._unrestrictedGetObject()
            id_community = absolute_path + '/' + obj.id
            logger.info('Processant {} de {}. Comunitat {}'.format(num, len(comunnities), obj))
            community = pc.unrestrictedSearchResults(path=id_community)
            elastic_index = ElasticSharing().get_index_name().lower()
            try:
                self.elastic = getUtility(IElasticSearch)
                self.elastic().search(index=elastic_index)
            except:
                self.elastic().indices.create(
                    index=elastic_index,
                    body={
                        'mappings': {
                            'sharing': {
                                'properties': {
                                    'path': {'type': 'string'},
                                    'principal': {'type': 'string', 'index': 'not_analyzed' },
                                    'roles': {'type': 'string'},
                                    'uuid': {'type': 'string'}
                                    }
                                }
                            }
                        }
                    )

            for brain in community:
                obj = brain._unrestrictedGetObject()
                if not ICommunity.providedBy(obj):
                    elastic_sharing = queryUtility(IElasticSharing)
                    elastic_sharing.modified(obj)

                    logger.info('Actualitzat el objecte {} de la comunitat {}'.format(obj, id_community))

        logger.info('Finished update sharing in communities: {}'.format(portal.absolute_url()))
        self.response.setBody('OK')


class createElasticSharing(grok.View):
    """ Aquesta vista crea l'index de l'elasticsearch i li diu que el camp principal pot tenir caracters especials 'index': 'not_analyzed' """
    grok.name('createelasticsharing')
    grok.context(IPloneSiteRoot)

    def render(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass
        elastic_index = ElasticSharing().get_index_name().lower()
        try:
            self.elastic = getUtility(IElasticSearch)
            self.elastic().search(index=elastic_index)
        except:
            self.elastic().indices.create(
                index=elastic_index,
                body={
                    'mappings': {
                        'sharing': {
                            'properties': {
                                'path': {'type': 'string'},
                                'principal': {'type': 'string', 'index': 'not_analyzed' },
                                'roles': {'type': 'string'},
                                'uuid': {'type': 'string'}
                                }
                            }
                        }
                    }
                )

            self.response.setBody('OK')


class viewUsersWithNotUpdatedPhoto(grok.View):
    """ Shows the user list that the photo has not been changed """
    grok.context(IPloneSiteRoot)
    grok.require('zope2.ViewManagementScreens')

    @json_response
    def render(self):
        portal = api.portal.get()
        soup = get_soup('user_properties', portal)
        records = [r for r in soup.data.items()]

        result = {}
        for record in records:
            userID = record[1].attrs['id']
            if userID != 'admin':
                mtool = api.portal.get_tool(name='portal_membership')
                portrait = mtool.getPersonalPortrait(userID)
                typePortrait = portrait.__class__.__name__
                if typePortrait == 'FSImage' or (typePortrait == 'Image' and portrait.size == 9715 or portrait.size == 4831):
                    fullname = record[1].attrs['fullname'] if 'fullname' in record[1].attrs else ''
                    userInfo = {'fullname' : fullname}
                    result[userID] = userInfo

        return result

class deletePhotoFromUser(grok.View):
    """ Delete photo from user, add parameter ?user=nom.cognom """
    grok.name('deletephotofromuser')
    grok.context(IPloneSiteRoot)
    grok.require('zope2.ViewManagementScreens')

    def render(self):
        # /deleteUserPhoto?user=nom.cognom
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        if 'user' in self.request.form and self.request.form['user'] != '':
            user = api.user.get(username=self.request.form['user'])
            if user:
                context = aq_inner(self.context)
                try:
                    context.portal_membership.deletePersonalPortrait(self.request.form['user'])
                    return 'Done, photo has been removed from user ' + self.request.form['user']
                except:
                    return 'Error while deleting photo from user ' + self.request.form['user']
            else:
                return 'Error, user ' + self.request.form['user'] + ' not exist'
        else:
            return 'Add parameter ?user=nom.cognom in url'


class syncPlatformsPermissions(grok.View):
    """ Syncronize permissions in plone site, in hub service and owncloud service for every community """
    grok.name('syncPlatformsPermissions')
    grok.context(IPloneSiteRoot)
    grok.require('cmf.ManagePortal')

    def render(self):
        portal = api.portal.get()
        if is_activate_owncloud(portal):
            username = api.portal.get_registry_record('ulearn5.owncloud.controlpanel.IOCSettings.connector_username')
            password = api.portal.get_registry_record('ulearn5.owncloud.controlpanel.IOCSettings.connector_password')
            pc = api.portal.get_tool('portal_catalog')
            comunities = pc.unrestrictedSearchResults(portal_type="ulearn.community")
            for community in comunities:
                gwuuid = community.gwuuid
                url = portal.absolute_url() + '/api/communities/' + gwuuid + '/subscriptions'
                response = requests.get(url, auth=(username, password))
                payload = response.json()
                headers = {"Content-Type":"application/json"}
                r = requests.post(url, auth=(username, password), headers=headers, json=payload)

            return "Done"

        else:
            return "OwnCloud is not active in this site."


class changePortalType(grok.View):
    """ Change Portal Type ulearn5.owncloud.file_owncloud by  CloudFile """
    grok.name('changeportaltype')
    grok.context(IPloneSiteRoot)

    def render(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        pc = api.portal.get_tool('portal_catalog')
        filesowncloud_old = pc.unrestrictedSearchResults(portal_type='ulearn5.owncloud.file_owncloud')

        for file in filesowncloud_old:
            obj = file.getObject()
            obj.portal_type = 'CloudFile'
            obj.reindexObject()

        transaction.commit()

        return 'Done'


class executeCronTasks(grok.View):
    """ TODO: .....
        url/execute_cron_tasks/?user=victor&pass=123123
    """
    grok.name('execute_cron_tasks')
    grok.context(IPloneSiteRoot)
    grok.require('ulearn.APIAccess')

    def render(self):
        url = self.context.absolute_url()

        info_cron = {}

        registry = queryUtility(IRegistry)
        settings = registry.forInterface(IUlearnControlPanelSettings, check=False)
        tasks = settings.cron_tasks

        try:
            username = self.request.form['user']
            password = self.request.form['pass']
        except:
            info_cron.update({"status": "Error not username or password"})
            logger.info(url + ':' + str(info_cron))
            return json.dumps(info_cron)

        info_cron.update({"status": ""})
        for task in tasks:
            result = requests.get(url + '/' + task, auth=(username, password))
            if result.status_code == 200 and 'Error' not in result.text:
                info_cron.update({task: 'OK'})
            else:
                info_cron.update({task: 'Error'})

        info_cron["status"] = "Done executeCronTasks"
        logger.info(url + ':' + str(info_cron))

        return json.dumps(info_cron)


class getInfoCronTasks(grok.View):
    """ TODO: .....
        url/get_info_cron_tasks
    """
    grok.name('get_info_cron_tasks')
    grok.context(IPloneSiteRoot)
    grok.require('ulearn.APIAccess')

    def render(self):
        info_cron = {}
        portal = api.portal.get()
        info_cron.update({"site": portal.getPhysicalPath()[2]})
        registry = queryUtility(IRegistry)
        settings = registry.forInterface(IUlearnControlPanelSettings, check=False)
        info_cron.update({"tasks": settings.cron_tasks})
        return json.dumps(info_cron)


class listFileUploadErrors(grok.View):
    """ Vista per veure tots el fitchers File Upload que no estàn ven sincronitzats amb el OwnCloud. """
    grok.name('list_fileupload_errors')
    grok.context(IPloneSiteRoot)

    def render(self):
        portal = api.portal.get()
        if is_activate_owncloud(portal):
            pc = api.portal.get_tool('portal_catalog')
            files = pc.searchResults(portal_type='CloudFile')

            if files:
                client = getUtility(IOwncloudClient)
                session = client.admin_connection()
                errors = ''
                for file in files:
                    domain = get_domain()
                    portal_state = file.unrestrictedTraverse('@@plone_portal_state')
                    root = getNavigationRootObject(file, portal_state.portal())
                    path = file.getPath().split('/')
                    path = domain + "/" + "/".join(path[len(root.getPhysicalPath()):])
                    try:
                        session.file_info(path)
                    except OCSResponseError:
                        pass
                    except HTTPResponseError:
                        errors += path + '\n'

                if errors:
                    return errors
                else:
                    return 'Todo OK'
            else:
                return 'No hay ficheros'
        else:
            return 'Owncloud no activado'


class changePermissionsToContent(grok.View):
    """ Canvia els permisos a tots el continguts que s'han creat autòmaticament (/news, /gestion, ...) """
    grok.context(IPloneSiteRoot)
    grok.require('zope2.ViewManagementScreens')

    def render(self):
        portal = getSite()
        langs = api.portal.get_tool(name='portal_languages').getSupportedLanguages()
        delete_permission = ('Site Administrator', 'Manager',)
        edit_permission = ('Site Administrator', 'Manager', 'WebMaster', 'Owner')

        portal['front-page']._Delete_objects_Permission = delete_permission

        if 'news' in portal:
            portal['news']._Delete_objects_Permission = delete_permission

            if 'aggregator' in portal['news']:
                portal['news']['aggregator']._Delete_objects_Permission = delete_permission

        if 'Members' in portal:
            for user in portal['Members']:
                portal['Members'][user]._Delete_objects_Permission = delete_permission

                if 'banners' in portal['Members'][user]:
                    portal['Members'][user]['banners']._Delete_objects_Permission = delete_permission

        if 'gestion' in portal:
            portal['gestion']._Delete_objects_Permission = delete_permission

            if 'menu' in portal['gestion']:
                portal['gestion']['menu']._Delete_objects_Permission = delete_permission

                for lang in langs:
                    if lang in portal['gestion']['menu']:
                        portal['gestion']['menu'][lang]._Delete_objects_Permission = delete_permission

            if 'header' in portal['gestion']:
                portal['gestion']['header']._Delete_objects_Permission = delete_permission

                for lang in langs:
                    if lang in portal['gestion']['header']:
                        portal['gestion']['header'][lang]._Delete_objects_Permission = delete_permission

            if 'footer' in portal['gestion']:
                portal['gestion']['footer']._Delete_objects_Permission = delete_permission

                for lang in langs:
                    if lang in portal['gestion']['footer']:
                        portal['gestion']['footer'][lang]._Delete_objects_Permission = delete_permission

            if 'banners' in portal['gestion']:
                portal['gestion']['banners']._Delete_objects_Permission = delete_permission

            if 'community-tags' in portal['gestion']:
                portal['gestion']['community-tags']._Delete_objects_Permission = delete_permission

        pc = api.portal.get_tool('portal_catalog')
        communities = pc.unrestrictedSearchResults(portal_type='ulearn.community')

        for community in communities:
            com = community.getObject()
            com.manage_delLocalRoles(['AuthenticatedUsers'])
            #community.getObject().manage_setLocalRoles('AuthenticatedUsers', ['Reader'])

            com._Delete_objects_Permission = ('Site Administrator', 'Manager', 'WebMaster', 'Owner')
            com._Modify_portal_content_Permission = edit_permission

            com = community.id
            if 'documents' in portal[com]:
                portal[com]['documents']._Delete_objects_Permission = delete_permission
                portal[com]['documents']._Modify_portal_content_Permission = edit_permission

            if 'events' in portal[com]:
                portal[com]['events']._Delete_objects_Permission = delete_permission
                portal[com]['events']._Modify_portal_content_Permission = edit_permission

            if 'news' in portal[com]:
                portal[com]['news']._Delete_objects_Permission = delete_permission
                portal[com]['news']._Modify_portal_content_Permission = edit_permission

                if 'aggregator' in portal[com]['news']:
                    portal[com]['news']['aggregator']._Delete_objects_Permission = delete_permission
                    portal[com]['news']['aggregator']._Modify_portal_content_Permission = edit_permission

        transaction.commit()
        return 'OK'


class addAllCommunitiesAsFavoriteFromAllUsers(grok.View):
    """ Añade a favorito todas las comunidades a las que esta suscrito los usuarios, si esta en un grupo no funciona actualmente """
    grok.context(IPloneSiteRoot)
    grok.require('zope2.ViewManagementScreens')

    def render(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        pc = api.portal.get_tool(name="portal_catalog")
        communities = pc.unrestrictedSearchResults(object_provides=ICommunity.__identifier__)

        for community in communities:
            communityObj = community.getObject()
            result = ICommunityACL(communityObj)().attrs.get('acl', '')
            for user in result['users']:
                IFavorite(communityObj).add(user['id'].strip())
        return 'OK'


class addCommunityAsFavoriteFromAllUsers(grok.View):
    """ Añade a favorito a todos los usuarios usuarios subcritos a X comunidad, si esta en un grupo no funciona actualmente """
    grok.context(IPloneSiteRoot)
    grok.require('zope2.ViewManagementScreens')

    def render(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        if 'community' in self.request.form:
            pc = api.portal.get_tool(name="portal_catalog")
            communities = pc.unrestrictedSearchResults(object_provides=ICommunity.__identifier__,
                                                       id=self.request.form['community'])
            if communities:
                for community in communities:
                    communityObj = community.getObject()
                    result = ICommunityACL(communityObj)().attrs.get('acl', '')
                    for user in result['users']:
                        IFavorite(communityObj).add(user['id'].strip())
                return 'OK'
            else:
                return 'Community ' + self.request.form['community'] + ' not exist'
        else:
            return 'Error add community parameter - /addcommunityasfavoritefromallusers?community=community.id'


class addProtectedFileInDocumentsCommunity(grok.View):
    """ Si esta instalado el paquete ulearn5.externalstorage, esta vista añade en la carpeta documentos de todas las comunidades que se puedan crear archivos protegidos """
    grok.name('add_protected_file_in_documents_community')
    grok.context(IPloneSiteRoot)
    grok.require('cmf.ManagePortal')

    def render(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        portal = api.portal.get()
        if is_activate_externalstorage(portal):
            pc = api.portal.get_tool('portal_catalog')
            comunnities = pc.unrestrictedSearchResults(portal_type="ulearn.community")
            for community in comunnities:
                com = community.getObject()
                com = community.id
                if 'documents' in portal[com]:
                    documents = portal[com]['documents']

                    behavior = ISelectableConstrainTypes(documents)
                    # Obtengo los contenidos que se pueden añadir en la carpeta documents
                    locallyAllowedTypes = behavior.getLocallyAllowedTypes()
                    logger.info('LocallyAllowedTypes {} community_id: {} in the portal: {}.'.format(locallyAllowedTypes, com, portal.absolute_url()))
                    if 'ExternalContent' not in locallyAllowedTypes:
                        # Le añado el ExternalContent a los contenidos que se pueden añadir en la carpeta documents
                        locallyAllowedTypes.append('ExternalContent')
                        behavior.setLocallyAllowedTypes(locallyAllowedTypes)
                        behavior.setImmediatelyAddableTypes(locallyAllowedTypes)
                        logger.info('Add ExternalContent in LocallyAllowedTypes {} community_id: {} in the portal: {}.'.format(locallyAllowedTypes, com, portal.absolute_url()))
            return "OK Add Protected File in Folder Documents Communities"

        else:
           return "ulearn5.externalstorage is not active in this site."

class addEtherpadInDocumentsCommunity(grok.View):
    """ Si esta instalado el paquete ulearn5.etherpad, esta vista añade en la carpeta documentos de todas las comunidades que se puedan crear documentos etherpad """
    grok.name('add_etherpad_in_documents_community')
    grok.context(IPloneSiteRoot)
    grok.require('cmf.ManagePortal')

    def render(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        portal = api.portal.get()
        if is_activate_etherpad(portal):
            pc = api.portal.get_tool('portal_catalog')
            comunnities = pc.unrestrictedSearchResults(portal_type="ulearn.community")
            for community in comunnities:
                com = community.getObject()
                com = community.id
                if 'documents' in portal[com]:
                    documents = portal[com]['documents']

                    behavior = ISelectableConstrainTypes(documents)
                    # Obtengo los contenidos que se pueden añadir en la carpeta documents
                    locallyAllowedTypes = behavior.getLocallyAllowedTypes()
                    logger.info('LocallyAllowedTypes {} community_id: {} in the portal: {}.'.format(locallyAllowedTypes, com, portal.absolute_url()))
                    if 'Etherpad' not in locallyAllowedTypes:
                        # Le añado el ExternalContent a los contenidos que se pueden añadir en la carpeta documents
                        locallyAllowedTypes.append('Etherpad')
                        behavior.setLocallyAllowedTypes(locallyAllowedTypes)
                        behavior.setImmediatelyAddableTypes(locallyAllowedTypes)
                        logger.info('Add Etherpad in LocallyAllowedTypes {} community_id: {} in the portal: {}.'.format(locallyAllowedTypes, com, portal.absolute_url()))
            return "OK Add Etherpad in Folder Documents Communities"

        else:
           return "ulearn5.ethepad is not active in this site."

class notifyManualInCommunity(grok.View):
    """ Somo por defecto la notificación por email es automatica esto te la cambia a manual para EBCN """
    grok.name('notify_manual_in_community')
    grok.context(IPloneSiteRoot)
    grok.require('cmf.ManagePortal')

    def render(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        portal = api.portal.get()
        pc = api.portal.get_tool('portal_catalog')
        comunnities = pc.unrestrictedSearchResults(portal_type="ulearn.community")
        for community in comunnities:
            com = community.getObject()
            if com.notify_activity_via_mail == True:
                com.type_notify = u'Manual'
                logger.info('Add Notify Manual in community_id: {} in the portal: {}.'.format(com.id, portal.absolute_url()))
                com.reindexObject()

        transaction.commit()
        return "OK Add notify Manual in Communities"

class deleteNominasMes(grok.View):
    """ Aquesta vista esborra les nomines de tots els usuaris d'un mes en concret """
    grok.name('deletenominasmes')
    grok.template('deletenominasmes')
    grok.context(IPloneSiteRoot)

    #render = ViewPageTemplateFile('views_templates/deletenominasmes.pt')

    def update(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass
        if self.request.environ['REQUEST_METHOD'] == 'POST':
            pc = api.portal.get_tool('portal_catalog')
            JSONproperties = api.portal.get_tool(name='portal_properties').nomines_properties
            nominas_folder_name = JSONproperties.getProperty('nominas_folder_name').lower()
            path = '/'.join(api.portal.get().getPhysicalPath()) + '/' + nominas_folder_name
            nominas = pc.unrestrictedSearchResults(portal_type='File', path=path)

            if self.request.form['mes'] != '':
                mes_a_borrar = self.request.form['mes']

                for brain in nominas:
                    obj = brain.getObject()
                    if mes_a_borrar in obj.id:
                        parent = obj.aq_parent
                        parent.manage_delObjects([obj.id])
                        logger.info('Nómina {} borrada'.format(obj.id))

                logger.info('Se han borrado las nóminas del mes {}'.format(mes_a_borrar))
