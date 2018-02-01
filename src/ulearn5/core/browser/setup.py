# -*- coding: utf-8 -*-
from five import grok
from zope.component import queryUtility
from zope.component import getUtility
from zope.component import getMultiAdapter
from zope.component.hooks import getSite
from zope.interface import alsoProvides
from zope.interface import Interface

from Products.CMFPlone.interfaces import ILanguageSchema
from Products.CMFPlone.interfaces import IPloneSiteRoot
from Products.CMFPlone.interfaces.constrains import ISelectableConstrainTypes
from Products.CMFPlone.interfaces.syndication import ISiteSyndicationSettings
from Products.CMFCore.utils import getToolByName

from plone import api
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletAssignmentMapping
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from plone.registry.interfaces import IRegistry

from repoze.catalog.query import Eq
from souper.soup import get_soup
import transaction
from datetime import datetime
from Acquisition import aq_inner

from base5.core.utilities import IElasticSearch
from base5.portlets.browser.manager import IColStorage
from ulearn5.core.gwuuid import IGWUUID
from ulearn5.core.browser.sharing import IElasticSharing
from ulearn5.core.content.community import ICommunity
from ulearn5.core.browser.sharing import ElasticSharing
# from ulearn5.core.api.people import Person

import logging
logger = logging.getLogger(__name__)


grok.templatedir("views_templates")
NEWS_QUERY = [{'i': u'portal_type', 'o': u'plone.app.querystring.operation.selection.is', 'v': [u'News Item']},
              {'i': u'review_state', 'o': u'plone.app.querystring.operation.selection.is', 'v': [u'published', u'intranet']},
              {'i': u'path', 'o': u'plone.app.querystring.operation.string.relativePath', 'v': u'..'}]
QUERY_SORT_ON = u'effective'


class debug(grok.View):
    """ Convenience view for faster debugging. Needs to be manager. """
    grok.context(Interface)
    grok.require('cmf.ManagePortal')

    def render(self):
        import ipdb; ipdb.set_trace()  # Magic! Do not delete!!! :)


class setupHomePage(grok.View):
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
        from ulearn5.theme.portlets.communities import Assignment as communitiesAssignment
        from ulearn5.theme.portlets.thinnkers import Assignment as thinnkersAssignment
        from mrs5.max.portlets.maxui import Assignment as maxAssignment
        from ulearn5.theme.portlets.buttonbar.buttonbar import Assignment as buttonbarAssignment
        from ulearn5.theme.portlets.calendar import Assignment as calendarAssignment
        from ulearn5.theme.portlets.angularrouteview import Assignment as angularrouteviewAssignment

        # Add portlets programatically
        column = getUtility(IPortletManager, name='ContentWellPortlets.BelowTitlePortletManager1')
        manager = getMultiAdapter((frontpage, column), IPortletAssignmentMapping)
        chooser = INameChooser(manager)
        manager[chooser.chooseName(None, communitiesAssignment())] = communitiesAssignment()
        #manager[chooser.chooseName(None, chatAssignment())] = chatAssignment()
        manager[chooser.chooseName(None, thinnkersAssignment())] = thinnkersAssignment()

        column = getUtility(IPortletManager, name='ContentWellPortlets.BelowTitlePortletManager2')
        manager = getMultiAdapter((frontpage, column), IPortletAssignmentMapping)
        chooser = INameChooser(manager)
        manager[chooser.chooseName(None, angularrouteviewAssignment())] = angularrouteviewAssignment()
        manager[chooser.chooseName(None, buttonbarAssignment())] = buttonbarAssignment()
        manager[chooser.chooseName(None, maxAssignment())] = maxAssignment()

        column = getUtility(IPortletManager, name='ContentWellPortlets.BelowTitlePortletManager3')
        manager = getMultiAdapter((frontpage, column), IPortletAssignmentMapping)
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
        lan_tool.use_content_negotiation = True
        lan_tool.use_cookie_negotiation = True
        transaction.commit()

        return 'Done'

    def create_content(self, container, portal_type, id, publish=True, **kwargs):
        if not getattr(container, id, False):
            createContentInContainer(container, portal_type, checkConstraints=False, **kwargs)
        return getattr(container, id)


class createMenuFolders(grok.View):
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

    def newPrivateFolder(self, context, newid, title):
        return self.createOrGetObject(context, newid, title, u'privateFolder')

    def render(self):
        portal = getSite()
        gestion = self.newPrivateFolder(portal, 'gestion', u'Gestión')
        gestion.exclude_from_nav = False
        gestion.setLayout('folder_listing')
        behavior = ISelectableConstrainTypes(gestion)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(('Folder', 'privateFolder',))
        behavior.setImmediatelyAddableTypes(('Folder', 'privateFolder',))

        enlaces_cabecera = self.newPrivateFolder(gestion, 'menu', u'Menu')
        enlaces_cabecera.exclude_from_nav = False
        enlaces_cabecera.reindexObject()

        for language in getToolByName(portal, 'portal_languages').getSupportedLanguages():
            language_folder = self.newPrivateFolder(enlaces_cabecera, language, language)
            language_folder.exclude_from_nav = False
            language_folder.reindexObject()
            behavior = ISelectableConstrainTypes(language_folder)
            behavior.setConstrainTypesMode(1)
            behavior.setLocallyAllowedTypes(('Folder', 'privateFolder', 'Link',))
            behavior.setImmediatelyAddableTypes(('Folder', 'privateFolder', 'Link',))


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

# class deleteUsers(grok.View):
#     """ Delete users from the plone & max & communities """
#     grok.name('deleteusers')
#      grok.template('deleteusers')
#     grok.context(IPloneSiteRoot)

#     render = ViewPageTemplateFile('views_templates/deleteusers.pt')

#     def update(self):
#         try:
#             from plone.protect.interfaces import IDisableCSRFProtection
#             alsoProvides(self.request, IDisableCSRFProtection)
#         except:
#             pass
#         if self.request.environ['REQUEST_METHOD'] == 'POST':

#             if self.request.form['users'] != '':
#                 users = self.request.form['users'].split(',')

#                 for user in users:
#                     user = user.strip()
#                     try:
#                         person = Person(self.context, [user])
#                         person.deleteMembers([user])
#                         remove_user_from_catalog(user.lower())
#                         pc = api.portal.get_tool(name='portal_catalog')
#                         username = user
#                         comunnities = pc.unrestrictedSearchResults(portal_type="ulearn.community")
#                         for num, community in enumerate(comunnities):
#                             obj = community._unrestrictedGetObject()
#                             self.context.plone_log('Processant {} de {}. Comunitat {}'.format(num, len(comunnities), obj))
#                             gwuuid = IGWUUID(obj).get()
#                             portal = api.portal.get()
#                             soup = get_soup('communities_acl', portal)

#                             records = [r for r in soup.query(Eq('gwuuid', gwuuid))]

#                             # Save ACL into the communities_acl soup
#                             if records:
#                                 acl_record = records[0]
#                                 acl = acl_record.attrs['acl']
#                                 exist = [a for a in acl['users'] if a['id'] == unicode(username)]
#                                 if exist:
#                                     acl['users'].remove(exist[0])
#                                     acl_record.attrs['acl'] = acl
#                                     soup.reindex(records=[acl_record])
#                                     adapter = obj.adapted()
#                                     adapter.set_plone_permissions(adapter.get_acl())

#                         maxclient, settings = getUtility(IMAXClient)()
#                         maxclient.setActor(settings.max_restricted_username)
#                         maxclient.setToken(settings.max_restricted_token)
#                         maxclient.people[username].delete()
#                         logger.info('Delete user: {}'.format(user))
#                     except:
#                         logger.error('User not deleted: {}'.format(user))
#                         pass

#                 logger.info('Finished deleted users: {}'.format(users))

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
