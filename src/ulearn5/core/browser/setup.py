# -*- coding: utf-8 -*-
from five import grok
from zope.component import queryUtility
from zope.component import getUtility
from zope.component import getMultiAdapter
from zope.component.hooks import getSite


from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletAssignmentMapping
from plone.dexterity.utils import createContentInContainer

from Products.CMFPlone.interfaces import IPloneSiteRoot

from base5.portlets.browser.manager import IColStorage

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from plone import api
from zope.interface import alsoProvides
from mrs5.max.utilities import IMAXClient
# from ulearn5.core.api.people import Person
from base5.core.utils import remove_user_from_catalog
from repoze.catalog.query import Eq
from souper.soup import get_soup
from ulearn5.core.gwuuid import IGWUUID
from ulearn5.core.browser.security import execute_under_special_role

import transaction
from datetime import datetime
from Acquisition import aq_inner
from zope.site.hooks import setSite
from Products.CMFCore.utils import getToolByName
from plone.namedfile.file import NamedBlobFile

from zope.component import queryUtility
from ulearn5.core.browser.sharing import IElasticSharing
from ulearn5.core.content.community import ICommunity
from base5.core.utilities import IElasticSearch
from ulearn5.core.browser.sharing import ElasticSharing


import logging
logger = logging.getLogger(__name__)


grok.templatedir("views_templates")


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
        import transaction
        transaction.commit()

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
