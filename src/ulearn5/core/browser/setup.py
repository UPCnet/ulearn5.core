# -*- coding: utf-8 -*-
from Acquisition import aq_inner
from base5.core.utilities import IElasticSearch
from base5.core.utils import json_response
from base5.portlets.browser.manager import IColStorage
from datetime import datetime
from five import grok
from mimetypes import MimeTypes
from plone import api
from plone.app.discussion.interfaces import IDiscussionSettings
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from plone.namedfile.file import NamedBlobImage
from plone.portlets.interfaces import IPortletAssignmentMapping
from plone.portlets.interfaces import IPortletManager
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces import ILanguageSchema
from Products.CMFPlone.interfaces import IPloneSiteRoot
from Products.CMFPlone.interfaces.constrains import ISelectableConstrainTypes
from Products.CMFPlone.interfaces.controlpanel import ISiteSchema
from Products.CMFPlone.interfaces.syndication import ISiteSyndicationSettings
from repoze.catalog.query import Eq
from souper.soup import get_soup
from ulearn5.core.browser.sharing import ElasticSharing
from ulearn5.core.browser.sharing import IElasticSharing
from ulearn5.core.content.community import ICommunity
from ulearn5.core.gwuuid import ATTRIBUTE_NAME
from ulearn5.core.gwuuid import IGWUUID
from ulearn5.core.setuphandlers import setup_ulearn_portlets
from ulearn5.core.utils import is_activate_owncloud
from ulearn5.owncloud.utils import update_owncloud_permission
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.hooks import getSite
from zope.interface import alsoProvides
from zope.interface import Interface

import base64
import json
import logging
import os
import requests
import shutil
import time
import transaction


ATTRIBUTE_NAME_FAVORITE = '_favoritedBy'

# from ulearn5.core.api.people import Person

logger = logging.getLogger(__name__)


grok.templatedir("views_templates")
NEWS_QUERY = [{'i': u'portal_type', 'o': u'plone.app.querystring.operation.selection.any', 'v': [u'News Item']},
              {'i': u'review_state', 'o': u'plone.app.querystring.operation.selection.any', 'v': [u'published', u'intranet']},
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
        wftool = getToolByName(frontpage, 'portal_workflow')
        wftool.doActionFor(frontpage, 'reject')
        wftool.doActionFor(frontpage, 'publishtointranet')
        transaction.commit()

        # Delete original 'aggregator' collection from 'News' folder
        if getattr(portal['news'], 'aggregator', False):
                api.content.delete(obj=portal['news']['aggregator'])

        # Create the aggregator with new criteria
        col_news = self.create_content(portal['news'], 'Collection', 'aggregator', title='aggregator', description=u'Site news')
        col_news.title = 'News'
        col_news.query = NEWS_QUERY
        col_news.sort_on = QUERY_SORT_ON

        col_news.reindexObject()

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

        enlaces_cabecera = newPrivateFolder(gestion, 'menu', u'Menu')
        enlaces_cabecera.exclude_from_nav = False
        enlaces_cabecera.reindexObject()

        for language in getToolByName(portal, 'portal_languages').getSupportedLanguages():
            language_folder = newPrivateFolder(enlaces_cabecera, language, language)
            language_folder.exclude_from_nav = False
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

        description = u'La capçalera utilitzarà la primera imatge del directori, aquesta imatge ha de tenir una alçada de 83px. \nLa cabecera utilizará la primera imagen del directorio, esta imagen tiene que tener una altura de 83px. \nThe header will use the first image of the directory, this image must have a height of 83px.'

        header = newPrivateFolder(gestion, 'header', u'Header')
        header.exclude_from_nav = False
        header.description = description
        header.setLayout('folder_listing')
        behavior = ISelectableConstrainTypes(header)
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

        footer = newPrivateFolder(gestion, 'footer', u'Footer')
        footer.exclude_from_nav = False
        footer.setLayout('folder_listing')
        behavior = ISelectableConstrainTypes(footer)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(('Folder', 'privateFolder',))
        behavior.setImmediatelyAddableTypes(('Folder', 'privateFolder',))

        for language in getToolByName(portal, 'portal_languages').getSupportedLanguages():
            language_folder = newPrivateFolder(footer, language, language)
            language_folder.exclude_from_nav = False
            language_folder.setLayout('folder_listing')
            language_folder.description = description
            language_folder.reindexObject()
            behavior = ISelectableConstrainTypes(language_folder)
            behavior.setConstrainTypesMode(1)
            behavior.setLocallyAllowedTypes(('Document',))
            behavior.setImmediatelyAddableTypes(('Document',))

        footer.reindexObject()
        return 'Done'


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
                self.context.plone_log('Buscant comunitats per modificar la url')

                for brain in communities:
                    obj = brain.getObject()
                    community = obj.adapted()
                    community_url = url_antiga + '/' + obj.id
                    community_url_nova = url_nova + '/' + obj.id
                    properties_to_update = dict(url=community_url_nova)

                    community.maxclient.contexts[community_url].put(**properties_to_update)
                    self.context.plone_log('Comunitat amb url {} actualitzada per {}'.format(community_url, community_url_nova))


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
                        comunnities = pc.unrestrictedSearchResults(portal_type="ulearn.community")
                        for num, community in enumerate(comunnities):
                            obj = community._unrestrictedGetObject()
                            self.context.plone_log('Processant {} de {}. Comunitat {}'.format(num, len(comunnities), obj))
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

                        maxclient, settings = getUtility(IMAXClient)()
                        maxclient.setActor(settings.max_restricted_username)
                        maxclient.setToken(settings.max_restricted_token)
                        maxclient.people[username].delete()
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
                            self.context.plone_log('Processant {} de {}. Comunitat {}'.format(num, len(comunnities), obj))
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
#    tool = getToolByName(context, 'translation_service')
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
    """
    This view takes 2 arguments on the request GET data :
    folder: the path without the '/' at the beginning, which is the base folder
        where the 'year' folders should be created
    local_file: the complete path and filename of the file on server. Be carefully if the view is called
        and there are many instanes. The best way is to call it through <ip>:<instance_port>

    To test it: run python script with requests and:
    payload={'folder':'test','local_file': '/home/vicente.iranzo/mongodb_VPN_2016_upcnet.xls'}
    r = requests.get('http://localhost:8080/Plone/importfiletofolder', params=payload, auth=HTTPBasicAuth('admin', 'admin'))
    """
    grok.context(IPloneSiteRoot)
    grok.name('importfiletofolder')
    grok.require('base.webmaster')

    def render(self):
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
                mtool = getToolByName(self.context, 'portal_membership')
                portrait = mtool.getPersonalPortrait(userID)
                typePortrait = portrait.__class__.__name__
                if typePortrait == 'FSImage' or (typePortrait == 'Image' and portrait.size == 9715):
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

class migrationCommunities(grok.View):
    """ Aquesta vista migra comunitats de Plone 4 a la nova versió en Plone 5 """
    grok.name('migrationcommunities')
    grok.template('migrationcommunities')
    grok.context(IPloneSiteRoot)


    def update(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        if self.request.environ['REQUEST_METHOD'] == 'POST':
            hscope = 'widgetcli'
            pc = api.portal.get_tool('portal_catalog')
            communities = pc.searchResults(portal_type='ulearn.community')

            if self.request.form['url_instance_v4'] != '':
                url_instance_v4 = self.request.form['url_instance_v4']
                husernamev4 = self.request.form['husernamev4']
                htokenv4 = self.request.form['htokenv4']
                comunitats_no_migrar = self.request.form['comunitats_no_migrar']
                comunitats_a_migrar = self.request.form['comunitats_a_migrar']

                json_communities = requests.get(url_instance_v4 + '/api/communitiesmigration', headers={'X-Oauth-Username': husernamev4,'X-Oauth-Token': htokenv4, 'X-Oauth-Scope': hscope})
                logger.info('Buscant comunitats per migrar')
                communities = json.loads(json_communities.content)

                for community in communities:

                    if (community['id'] not in comunitats_no_migrar) and (community['id'] in comunitats_a_migrar or comunitats_a_migrar == ''):

                        logger.info('Migrant comunitat {}'.format(community['title']))
                        result = pc.unrestrictedSearchResults(portal_type='ulearn.community', id=str(community['id']))


                        if result:
                            success_response = 'community already exists: ' + community['title']
                            status = 200
                        else:
                            # Creo la comunidad
                            imageObj = ''
                            if community['image']:
                                mime = MimeTypes()
                                mime_type = mime.guess_type(community['image'])
                                imgName = (community['image'].split('/')[-1]).decode('utf-8')
                                imgData = base64.decodestring(str(community['rawimage']))
                                imageObj = NamedBlobImage(data=imgData,
                                                          filename=imgName,
                                                          contentType=mime_type[0])

                            new_community_id = self.context.invokeFactory('ulearn.community', str(community['id']),
                                                                          title=community['title'],
                                                                          description=community['description'],
                                                                          image=imageObj,
                                                                          community_type=community['type'],
                                                                          activity_view=community['activity_view'],
                                                                          twitter_hashtag=community['twitter_hashtag'],
                                                                          notify_activity_via_push=community['notify_activity_via_push'],
                                                                          notify_activity_via_push_comments_too=community['notify_activity_via_push_comments_too'],
                                                                          checkConstraints=False)

                            # Modifico los datos de la comunidad
                            brain = pc.unrestrictedSearchResults(portal_type='ulearn.community', id=new_community_id)
                            if brain:
                                community_new = brain[0].getObject()

                                setattr(community_new, ATTRIBUTE_NAME_FAVORITE, str(community['favoritedBy']))
                                community_new.reindexObject(idxs=['favoritedBy'])

                                setattr(community_new, ATTRIBUTE_NAME, str(community['gwuuid']))
                                community_new.reindexObject(idxs=['gwuuid'])

                                community_new.listCreators = community['listCreators']
                                community_new.ModificationDate = community['ModificationDate']
                                community_new.created = community['CreationDate']
                                community_new.CreationDate = community['CreationDate']

                                community_new.is_shared = community['is_shared']
                                community_new.Creator = community['Creator']
                                community_new.UID = community['UID']

                                community_new.reindexObject()

                                # Migro los permisos del EDITACL

                                adapter = community_new.adapted()

                                # Ejemplo editacl
                                #community['editacl'] = {u'users': [{u'role': u'owner', u'displayName': u'Victor Fernandez', u'id': u'alberto.duran'}], u'groups': []}

                                # Change the uLearn part of the community

                                adapter.update_acl(community['editacl'])
                                acl = adapter.get_acl()
                                adapter.set_plone_permissions(acl)

                                # Communicate the change in the community subscription to the uLearnHub
                                # XXX: Until we do not have a proper Hub online
                                adapter.update_hub_subscriptions()

                                # If is activate owncloud modify permissions owncloud
                                if is_activate_owncloud(self.context):
                                    update_owncloud_permission(community_new, acl)

                            success_response = 'Created community: ' + community['title']

                        logger.info(success_response)

            logger.info('Ha finalitzat la migració de les comunitats.')


class migrationDocumentsCommunities(grok.View):
    """ Aquesta vista migra la carpeta Documents de les comunitats de Plone 4 a la nova versió en Plone 5 """
    grok.name('migrationdocumentscommunities')
    grok.template('migrationdocumentscommunities')
    grok.context(IPloneSiteRoot)


    def update(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        if self.request.environ['REQUEST_METHOD'] == 'POST':
            hscope = 'widgetcli'
            pc = api.portal.get_tool('portal_catalog')
            communities = pc.searchResults(portal_type='ulearn.community')

            if self.request.form['url_instance_v4'] != '':
                url_instance_v4 = self.request.form['url_instance_v4']
                husernamev4 = self.request.form['husernamev4']
                htokenv4 = self.request.form['htokenv4']
                url_instance_v5 = self.request.form['url_instance_v5']
                remote_username = self.request.form['remote_username']
                remote_password = self.request.form['remote_password']
                comunitats_no_migrar = self.request.form['comunitats_no_migrar']
                comunitats_a_migrar = self.request.form['comunitats_a_migrar']

                json_communities = requests.get(url_instance_v4 + '/api/communitiesmigration', headers={'X-Oauth-Username': husernamev4,'X-Oauth-Token': htokenv4, 'X-Oauth-Scope': hscope})
                logger.info('Buscant comunitats per migrar')
                communities = json.loads(json_communities.content)
                for community in communities:
                    if os.path.exists('/tmp/content_documents'):
                        shutil.rmtree('/tmp/content_documents')
                    if (community['id'] not in comunitats_no_migrar) and (community['id'] in comunitats_a_migrar or comunitats_a_migrar == ''):
                        logger.info('Migrant comunitat {}'.format(community['title']))
                        result = requests.get(url_instance_v4 + '/' + community['id'] + '/documents/export_dexterity?dir=/tmp',
                                                headers={'X-Oauth-Username': husernamev4,'X-Oauth-Token': htokenv4, 'X-Oauth-Scope': hscope})
                        if result.ok == False:
                            logger.info('Ha fallat export_dexterity')
                            time.sleep(10)
                            result = requests.get(url_instance_v4 + '/' + community['id'] + '/documents/export_dexterity?dir=/tmp',
                                                    headers={'X-Oauth-Username': husernamev4,'X-Oauth-Token': htokenv4, 'X-Oauth-Scope': hscope})

                        if result.ok == True:
                            requests.get(url_instance_v5 + '/' + community['id'] + '/documents/comunitats_import', auth=(remote_username, remote_password))
                            logger.info('He migrat la carpeta documents de: ' + community['title'])
                logger.info('Ha finalitzat la migració de les comunitats.')


class migrationEditaclCommunities(grok.View):
    """ Aquesta vista migra els permisos del editacl de les comunitats de Plone 4 a la nova versió en Plone 5 """
    grok.name('migrationeditaclcommunities')
    grok.template('migrationeditaclcommunities')
    grok.context(IPloneSiteRoot)


    def update(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        if self.request.environ['REQUEST_METHOD'] == 'POST':
            hscope = 'widgetcli'
            pc = api.portal.get_tool('portal_catalog')
            communities = pc.searchResults(portal_type='ulearn.community')

            if self.request.form['url_instance_v4'] != '':
                url_instance_v4 = self.request.form['url_instance_v4']
                husernamev4 = self.request.form['husernamev4']
                htokenv4 = self.request.form['htokenv4']
                comunitats_no_migrar = self.request.form['comunitats_no_migrar']
                comunitats_a_migrar = self.request.form['comunitats_a_migrar']

                json_communities = requests.get(url_instance_v4 + '/api/communitiesmigration', headers={'X-Oauth-Username': husernamev4,'X-Oauth-Token': htokenv4, 'X-Oauth-Scope': hscope})
                logger.info('Buscant comunitats per migrar els permisos del editacl')
                communities = json.loads(json_communities.content)

                for community in communities:

                    if (community['id'] not in comunitats_no_migrar) and (community['id'] in comunitats_a_migrar or comunitats_a_migrar == ''):

                        brain = pc.unrestrictedSearchResults(portal_type='ulearn.community', id=str(community['id']))
                        if brain:
                            community_new = brain[0].getObject()
                            adapter = community_new.adapted()

                            # Ejemplo editacl
                            #community['editacl'] = {u'users': [{u'role': u'owner', u'displayName': u'Victor Fernandez', u'id': u'alberto.duran'}], u'groups': []}

                            # Change the uLearn part of the community

                            adapter.update_acl(community['editacl'])
                            acl = adapter.get_acl()
                            adapter.set_plone_permissions(acl)

                            # Communicate the change in the community subscription to the uLearnHub
                            # XXX: Until we do not have a proper Hub online
                            adapter.update_hub_subscriptions()

                            # If is activate owncloud modify permissions owncloud
                            if is_activate_owncloud(self.context):
                                update_owncloud_permission(community_new, acl)

                            success_response = 'Migrat editacl comunitat: ' + community['title']
                            logger.info(success_response)


            logger.info('Ha finalitzat la migració del editacl de les comunitats.')
