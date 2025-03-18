# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime
from hashlib import sha1

import requests
import transaction
from Acquisition import aq_inner
from base5.core.adapters.favorites import IFavorite
from base5.core.utilities import IElasticSearch
from base5.core.utils import remove_user_from_catalog
from base5.portlets.browser.manager import IColStorage
from mrs5.max.utilities import IMAXClient
from plone import api
from plone.app.discussion.interfaces import IDiscussionSettings
from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from plone.portlets.interfaces import (IPortletAssignmentMapping,
                                       IPortletManager)
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.interfaces import ILanguageSchema, ISearchSchema
from Products.CMFPlone.interfaces.constrains import ISelectableConstrainTypes
from Products.CMFPlone.interfaces.controlpanel import ISiteSchema
from Products.CMFPlone.interfaces.syndication import ISiteSyndicationSettings
from Products.Five.browser import BrowserView
from ulearn5.core.browser.sharing import ElasticSharing, IElasticSharing
from ulearn5.core.content.community import ICommunity
from ulearn5.core.controlpanel import IUlearnControlPanelSettings
from ulearn5.core.gwuuid import IGWUUID
from ulearn5.core.services.person import Person
from ulearn5.core.setuphandlers import setup_ulearn_portlets
from ulearn5.core.utils import (get_or_initialize_annotation,
                                is_activate_etherpad,
                                is_activate_externalstorage)
from zope.component import getMultiAdapter, getUtility, queryUtility
from zope.component.hooks import getSite
from zope.interface import alsoProvides

ATTRIBUTE_NAME_FAVORITE = "_favoritedBy"

logger = logging.getLogger(__name__)

NEWS_QUERY = [
    {
        "i": "portal_type",
        "o": "plone.app.querystring.operation.selection.any",
        "v": ["News Item"],
    },
    {
        "i": "review_state",
        "o": "plone.app.querystring.operation.selection.any",
        "v": ["published", "intranet", "esborrany"],
    },
    {
        "i": "path",
        "o": "plone.app.querystring.operation.string.relativePath",
        "v": "..",
    },
]
QUERY_SORT_ON = "effective"


def createOrGetObject(context, newid, title, type_name):
    if newid in context.contentIds():
        obj = context[newid]
    else:
        obj = createContentInContainer(
            context, type_name, title=title, checkConstrains=False
        )
        transaction.savepoint()
        if obj.id != newid:
            context.manage_renameObject(obj.id, newid)
        obj.reindexObject()
    return obj


def newPrivateFolder(context, newid, title):
    return createOrGetObject(context, newid, title, "privateFolder")


def getDestinationFolder(stats_folder, create_month=True):
    """
    This function creates if it doesn't exist a folder in <stats_folder>/<year>/<month>.
    If  create_month is False, then only the <year> folder is created
    """
    portal = api.portal.get()
    # setSite(portal)
    # Create 'stats_folder' folder if not exists
    if portal.get(stats_folder) is None:
        makeFolder(portal, stats_folder)
    portal = portal.get(stats_folder)
    today = datetime.now()
    context = aq_inner(portal)
    #    tool = api.portal.get_tool(name='translation_service')
    #    month = tool.translate(today.strftime("%B"), 'ulearn', context=context).encode()
    month = "march"
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
    obj = createContentInContainer(
        portal,
        "Folder",
        id="{}".format(name),
        title="{}".format(name),
        description="{}".format(name),
    )
    obj.reindexObject()
    transaction.commit()


class debug(BrowserView):
    """Convenience view for faster debugging. Needs to be manager."""

    def __call__(self):
        import ipdb

        ipdb.set_trace()  # Magic! Do not delete!!! :)
        pass


class setupHomePage(BrowserView):
    """Add the portlets and add the values of settings"""

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)
            pass
        portal = getSite()
        frontpage = portal["front-page"]
        frontpage.description = ""

        frontpage.text = RichTextValue("", "text/plain", "text/html")
        wftool = api.portal.get_tool(name="portal_workflow")
        wftool.doActionFor(frontpage, "reject")
        wftool.doActionFor(frontpage, "publishtointranet")
        frontpage._Delete_objects_Permission = (
            "Site Administrator",
            "Manager",
        )
        transaction.commit()

        # Delete original 'aggregator' collection from 'News' folder
        if getattr(portal["news"], "aggregator", False):
            api.content.delete(obj=portal["news"]["aggregator"])

        # Create the aggregator with new criteria
        col_news = self.create_content(
            portal["news"],
            "Collection",
            "aggregator",
            title="aggregator",
            description="Site news",
        )
        col_news.title = "News"
        col_news.query = NEWS_QUERY
        col_news.sort_on = QUERY_SORT_ON
        col_news.sort_reversed = True
        col_news.item_count = 10
        col_news._Delete_objects_Permission = (
            "Site Administrator",
            "Manager",
        )
        col_news.reindexObject()

        # Set default view from aggregator
        portal["news"]["aggregator"].setLayout("collection_news_view")

        # Set default page from 'News' folder
        portal["news"].setDefaultPage("aggregator")
        portal["news"]._Delete_objects_Permission = (
            "Site Administrator",
            "Manager",
        )

        from plone.portlets.constants import CONTEXT_CATEGORY
        from plone.portlets.interfaces import ILocalPortletAssignmentManager

        # Get the proper portlet manager
        manager = getUtility(IPortletManager, name="plone.rightcolumn")
        # Get the current blacklist for the location
        blacklist = getMultiAdapter(
            (self.context, manager), ILocalPortletAssignmentManager
        )
        # Turn off the manager
        blacklist.setBlacklistStatus(CONTEXT_CATEGORY, True)

        # Get the proper portlet manager
        manager = getUtility(IPortletManager, name="plone.footerportlets")
        # Get the current blacklist for the location
        blacklist = getMultiAdapter(
            (self.context, manager), ILocalPortletAssignmentManager
        )
        # Turn off the manager
        blacklist.setBlacklistStatus(CONTEXT_CATEGORY, True)

        # Get the proper portlet manager
        manager = getUtility(IPortletManager, name="plone.leftcolumn")
        # Get the current blacklist for the location
        blacklist = getMultiAdapter(
            (frontpage, manager), ILocalPortletAssignmentManager
        )
        # Turn off the manager
        blacklist.setBlacklistStatus(CONTEXT_CATEGORY, True)

        from mrs5.max.portlets.maxui import Assignment as maxAssignment
        from mrs5.max.portlets.maxuichat import Assignment as chatAssignment
        from ulearn5.theme.portlets.angularrouteview import \
            Assignment as angularrouteviewAssignment
        from ulearn5.theme.portlets.buttonbar.buttonbar import \
            Assignment as buttonbarAssignment
        from ulearn5.theme.portlets.calendar import \
            Assignment as calendarAssignment
        from ulearn5.theme.portlets.communities import \
            Assignment as communitiesAssignment
        from ulearn5.theme.portlets.profile.profile import \
            Assignment as profileAssignment
        from ulearn5.theme.portlets.thinnkers import \
            Assignment as thinnkersAssignment
        from zope.container.interfaces import INameChooser

        # Add portlets programatically
        column = getUtility(
            IPortletManager, name="ContentWellPortlets.BelowTitlePortletManager1"
        )
        manager = getMultiAdapter((frontpage, column), IPortletAssignmentMapping)
        for portlet in manager:
            del manager[portlet]
        chooser = INameChooser(manager)
        manager[chooser.chooseName(None, profileAssignment())] = profileAssignment()
        manager[chooser.chooseName(None, communitiesAssignment())] = (
            communitiesAssignment()
        )
        manager[chooser.chooseName(None, chatAssignment())] = chatAssignment()
        manager[chooser.chooseName(None, thinnkersAssignment())] = thinnkersAssignment()

        column = getUtility(
            IPortletManager, name="ContentWellPortlets.BelowTitlePortletManager2"
        )
        manager = getMultiAdapter((frontpage, column), IPortletAssignmentMapping)
        for portlet in manager:
            del manager[portlet]
        chooser = INameChooser(manager)
        manager[chooser.chooseName(None, angularrouteviewAssignment())] = (
            angularrouteviewAssignment()
        )
        manager[chooser.chooseName(None, buttonbarAssignment())] = buttonbarAssignment()
        manager[chooser.chooseName(None, maxAssignment())] = maxAssignment()

        column = getUtility(
            IPortletManager, name="ContentWellPortlets.BelowTitlePortletManager3"
        )
        manager = getMultiAdapter((frontpage, column), IPortletAssignmentMapping)
        for portlet in manager:
            del manager[portlet]
        chooser = INameChooser(manager)
        manager[chooser.chooseName(None, calendarAssignment())] = calendarAssignment()

        portletManager = getUtility(
            IPortletManager, "ContentWellPortlets.BelowTitlePortletManager1"
        )
        colstorage = getMultiAdapter((frontpage, portletManager), IColStorage)
        colstorage.col = "3"

        portletManager = getUtility(
            IPortletManager, "ContentWellPortlets.BelowTitlePortletManager2"
        )
        colstorage = getMultiAdapter((frontpage, portletManager), IColStorage)
        colstorage.col = "6"

        portletManager = getUtility(
            IPortletManager, "ContentWellPortlets.BelowTitlePortletManager3"
        )
        colstorage = getMultiAdapter((frontpage, portletManager), IColStorage)
        colstorage.col = "3"

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
        lan_tool = registry.forInterface(ILanguageSchema, prefix="plone")
        lan_tool.use_cookie_negotiation = True

        # Toolbar position
        site_tool = registry.forInterface(ISiteSchema, prefix="plone")
        site_tool.toolbar_position = "top"

        # Enabled comments globally
        discussion_tool = registry.forInterface(IDiscussionSettings)
        discussion_tool.globally_enabled = True

        # Livesearch
        search_tool = registry.forInterface(ISearchSchema, prefix="plone")
        search_tool.search_results_description_length = 140

        # Types permited in news folder
        news_tool = ISelectableConstrainTypes(portal["news"])
        news_tool.setLocallyAllowedTypes(
            (
                "News Item",
                "Folder",
                "Collection",
            )
        )
        news_tool.setImmediatelyAddableTypes(
            (
                "News Item",
                "Folder",
                "Collection",
            )
        )
        transaction.commit()

        return "Done"

    def create_content(self, container, portal_type, id, publish=True, **kwargs):
        if not getattr(container, id, False):
            createContentInContainer(
                container, portal_type, checkConstraints=False, **kwargs
            )
        return getattr(container, id)


class createMenuFolders(BrowserView):
    """Create the directory structure of the menu"""

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)
            pass

        portal = getSite()
        gestion = newPrivateFolder(portal, "gestion", "Gestión")
        gestion.exclude_from_nav = False
        gestion.setLayout("folder_listing")
        behavior = ISelectableConstrainTypes(gestion)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(
            (
                "Folder",
                "privateFolder",
            )
        )
        behavior.setImmediatelyAddableTypes(
            (
                "Folder",
                "privateFolder",
            )
        )
        gestion._Delete_objects_Permission = (
            "Site Administrator",
            "Manager",
        )

        enlaces_cabecera = newPrivateFolder(gestion, "menu", "Menu")
        enlaces_cabecera.exclude_from_nav = False
        enlaces_cabecera._Delete_objects_Permission = (
            "Site Administrator",
            "Manager",
        )
        enlaces_cabecera.reindexObject()

        for language in api.portal.get_tool(
            name="portal_languages"
        ).getSupportedLanguages():
            language_folder = newPrivateFolder(enlaces_cabecera, language, language)
            language_folder.exclude_from_nav = False
            language_folder._Delete_objects_Permission = (
                "Site Administrator",
                "Manager",
            )
            language_folder.reindexObject()
            behavior = ISelectableConstrainTypes(language_folder)
            behavior.setConstrainTypesMode(1)
            behavior.setLocallyAllowedTypes(
                (
                    "Folder",
                    "privateFolder",
                )
            )
            behavior.setImmediatelyAddableTypes(
                (
                    "Folder",
                    "privateFolder",
                )
            )

        transaction.commit()
        return "Done"


class createCustomizedHeaderFolder(BrowserView):
    """Create the directory structure of the customized header"""

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)
            pass

        portal = getSite()
        gestion = newPrivateFolder(portal, "gestion", "Gestión")
        gestion.exclude_from_nav = False
        gestion.setLayout("folder_listing")
        behavior = ISelectableConstrainTypes(gestion)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(
            (
                "Folder",
                "privateFolder",
            )
        )
        behavior.setImmediatelyAddableTypes(
            (
                "Folder",
                "privateFolder",
            )
        )
        gestion._Delete_objects_Permission = (
            "Site Administrator",
            "Manager",
        )

        description = "La capçalera utilitzarà la primera imatge del directori, aquesta imatge ha de tenir una alçada de 83px. \nLa cabecera utilizará la primera imagen del directorio, esta imagen tiene que tener una altura de 83px. \nThe header will use the first image of the directory, this image must have a height of 83px."

        header = newPrivateFolder(gestion, "header", "Header")
        header.exclude_from_nav = False
        header.setLayout("folder_listing")
        behavior = ISelectableConstrainTypes(header)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(
            (
                "Folder",
                "privateFolder",
            )
        )
        behavior.setImmediatelyAddableTypes(
            (
                "Folder",
                "privateFolder",
            )
        )
        header._Delete_objects_Permission = (
            "Site Administrator",
            "Manager",
        )

        for language in api.portal.get_tool(
            name="portal_languages"
        ).getSupportedLanguages():
            language_folder = newPrivateFolder(header, language, language)
            language_folder.exclude_from_nav = False
            language_folder.setLayout("folder_listing")
            language_folder.description = description
            language_folder._Delete_objects_Permission = (
                "Site Administrator",
                "Manager",
            )
            language_folder.reindexObject()
            behavior = ISelectableConstrainTypes(language_folder)
            behavior.setConstrainTypesMode(1)
            behavior.setLocallyAllowedTypes(("Image",))
            behavior.setImmediatelyAddableTypes(("Image",))

        header.reindexObject()
        return "Done"


class createCustomizedFooterFolder(BrowserView):
    """Create the directory structure of the customized footer"""

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)
            pass

        description = "El peu de pàgina utilizarà el primer document del directori.\nEl pie de página utilizará el primer documento del directorio.\nThe footer will use the first document in the directory."

        portal = getSite()
        gestion = newPrivateFolder(portal, "gestion", "Gestión")
        gestion.exclude_from_nav = False
        gestion.setLayout("folder_listing")
        behavior = ISelectableConstrainTypes(gestion)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(
            (
                "Folder",
                "privateFolder",
            )
        )
        behavior.setImmediatelyAddableTypes(
            (
                "Folder",
                "privateFolder",
            )
        )
        gestion._Delete_objects_Permission = (
            "Site Administrator",
            "Manager",
        )

        footer = newPrivateFolder(gestion, "footer", "Footer")
        footer.exclude_from_nav = False
        footer.setLayout("folder_listing")
        behavior = ISelectableConstrainTypes(footer)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(
            (
                "Folder",
                "privateFolder",
            )
        )
        behavior.setImmediatelyAddableTypes(
            (
                "Folder",
                "privateFolder",
            )
        )
        footer._Delete_objects_Permission = (
            "Site Administrator",
            "Manager",
        )

        for language in api.portal.get_tool(
            name="portal_languages"
        ).getSupportedLanguages():
            language_folder = newPrivateFolder(footer, language, language)
            language_folder.exclude_from_nav = False
            language_folder.setLayout("folder_listing")
            language_folder.description = description
            language_folder._Delete_objects_Permission = (
                "Site Administrator",
                "Manager",
            )
            language_folder.reindexObject()
            behavior = ISelectableConstrainTypes(language_folder)
            behavior.setConstrainTypesMode(1)
            behavior.setLocallyAllowedTypes(("Document",))
            behavior.setImmediatelyAddableTypes(("Document",))

        footer.reindexObject()
        return "Done"


class createBannersFolder(BrowserView):
    """Create the directory banners in gestion"""

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)
            pass

        portal = getSite()
        gestion = newPrivateFolder(portal, "gestion", "Gestión")
        gestion.exclude_from_nav = False
        gestion.setLayout("folder_listing")
        behavior = ISelectableConstrainTypes(gestion)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(
            (
                "Folder",
                "privateFolder",
            )
        )
        behavior.setImmediatelyAddableTypes(
            (
                "Folder",
                "privateFolder",
            )
        )
        gestion._Delete_objects_Permission = (
            "Site Administrator",
            "Manager",
        )

        banners = newPrivateFolder(gestion, "banners", "Banners")
        banners.exclude_from_nav = False
        banners.setLayout("folder_listing")
        behavior = ISelectableConstrainTypes(banners)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(("ulearn.banner",))
        behavior.setImmediatelyAddableTypes(("ulearn.banner",))
        banners._Delete_objects_Permission = (
            "Site Administrator",
            "Manager",
        )

        transaction.commit()
        return "Done"


class createPersonalBannerFolder(BrowserView):
    """Create the directory banners in personal folder"""

    def createOrGetObject(self, context, newid, title, type_name):
        if newid in context.contentIds():
            obj = context[newid]
        else:
            obj = createContentInContainer(
                context, type_name, title=title, checkConstrains=False
            )
            transaction.savepoint()
            if obj.id != newid:
                context.manage_renameObject(obj.id, newid)
            obj.reindexObject()
        return obj

    def __call__(self):
        # /createPersonalBannerFolder?user=nom.cognom
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)
            pass

        if "user" in self.request.form:
            userid = self.request.form["user"]
            user = api.user.get(username=userid)
            if user:
                portal = getSite()
                perFolder = self.createOrGetObject(
                    portal["Members"], userid, userid, "privateFolder"
                )
                perFolder.exclude_from_nav = False
                perFolder.setLayout("folder_listing")
                behavior = ISelectableConstrainTypes(perFolder)
                behavior.setConstrainTypesMode(1)
                behavior.setLocallyAllowedTypes(("Folder",))
                behavior.setImmediatelyAddableTypes(("Folder",))
                perFolder._Delete_objects_Permission = (
                    "Site Administrator",
                    "Manager",
                )

                api.content.disable_roles_acquisition(perFolder)
                for username, roles in perFolder.get_local_roles():
                    perFolder.manage_delLocalRoles([username])
                perFolder.manage_setLocalRoles(
                    userid, ["Contributor", "Editor", "Reader"]
                )

                banFolder = self.createOrGetObject(
                    perFolder, "banners", "Banners", "Folder"
                )
                banFolder.exclude_from_nav = False
                banFolder.setLayout("folder_listing")
                behavior = ISelectableConstrainTypes(banFolder)
                behavior.setConstrainTypesMode(1)
                behavior.setLocallyAllowedTypes(("ulearn.banner",))
                behavior.setImmediatelyAddableTypes(("ulearn.banner",))
                banFolder._Delete_objects_Permission = (
                    "Site Administrator",
                    "Manager",
                )

                transaction.commit()
                return "Done" + ", " + userid + "."
            else:
                return "Error, user " + userid + " not exist."
        else:
            return (
                "Error add user parameter - /createPersonalBannerFolder?user=user.name"
            )


class createPopupStructure(BrowserView):
    """Create the directory structure of the popup menu"""

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)
            pass

        portal = getSite()
        gestion = newPrivateFolder(portal, "gestion", "Gestión")
        gestion.exclude_from_nav = False
        gestion.setLayout("folder_listing")
        behavior = ISelectableConstrainTypes(gestion)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(
            (
                "Folder",
                "privateFolder",
            )
        )
        behavior.setImmediatelyAddableTypes(
            (
                "Folder",
                "privateFolder",
            )
        )
        gestion._Delete_objects_Permission = (
            "Site Administrator",
            "Manager",
        )

        popup = newPrivateFolder(gestion, "popup", "Popup")
        popup.exclude_from_nav = False
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(
            (
                "Document",
                "Image",
            )
        )
        behavior.setImmediatelyAddableTypes(
            (
                "Document",
                "Image",
            )
        )
        popup._Delete_objects_Permission = (
            "Site Administrator",
            "Manager",
        )
        popup.description = "Important: no modificar el nom curt d'aquest document.\nImportante: no modificar el nombre corto de estos documentos.\nImportant: do not modify the short name of these documents."

        notify = createOrGetObject(popup, "notify", "Notify", "Document")
        notify._Delete_objects_Permission = (
            "Site Administrator",
            "Manager",
        )

        birthday = createOrGetObject(popup, "birthday", "Birthday", "Document")
        birthday._Delete_objects_Permission = (
            "Site Administrator",
            "Manager",
        )

        transaction.commit()
        return "Done"


class ldapKillah(BrowserView):

    def __call__(self):
        portal = getSite()

        if getattr(portal.acl_users, "ldapUPC", None):
            portal.acl_users.manage_delObjects("ldapUPC")

        if getattr(portal.acl_users, "ldapexterns", None):
            portal.acl_users.manage_delObjects("ldapexterns")


class memberFolderSetup(BrowserView):

    def __call__(self):
        portal = getSite()
        if not getattr(portal, "users", None):
            users_folder = createContentInContainer(
                portal, "Folder", title="users", checkConstraints=False
            )
            users_folder.setDefaultPage("member_search_form")
            portal.manage_delObjects("Members")


class changeURLCommunities(BrowserView):
    """Aquesta vista canvia la url de les comunitats"""

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)
            pass
        if self.request.environ["REQUEST_METHOD"] == "POST":
            pc = api.portal.get_tool("portal_catalog")
            communities = pc.searchResults(portal_type="ulearn.community")

            if self.request.form["url"] != "":
                url_nova = self.request.form["url"]
                url_antiga = self.request.form["url_antiga"]
                logger.info("Buscant comunitats per modificar la url")

                for brain in communities:
                    obj = brain.getObject()
                    community = obj.adapted()
                    community_url = url_antiga + "/" + obj.id
                    community_url_nova = url_nova + "/" + obj.id
                    properties_to_update = dict(url=community_url_nova)

                    community.maxclient.contexts[community_url].put(
                        **properties_to_update
                    )
                    logger.info(
                        "Comunitat amb url {} actualitzada per {}".format(
                            community_url, community_url_nova
                        )
                    )


class deleteUsers(BrowserView):
    """Delete users from the plone & max & communities"""

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)
            pass
        if self.request.environ["REQUEST_METHOD"] == "POST":

            if self.request.form["users"] != "":
                users = self.request.form["users"].split(",")

                for user in users:
                    user = user.strip()
                    try:
                        person = Person(self.context, self.request, user)
                        person.delete_member()
                        remove_user_from_catalog(user.lower())
                        pc = api.portal.get_tool(name="portal_catalog")
                        username = user

                        maxclient, settings = getUtility(IMAXClient)()
                        maxclient.setActor(settings.max_restricted_username)
                        maxclient.setToken(settings.max_restricted_token)

                        communities_subscription = maxclient.people[
                            username
                        ].subscriptions.get()

                        if communities_subscription != []:

                            for num, community_subscription in enumerate(
                                communities_subscription
                            ):
                                community = pc.unrestrictedSearchResults(
                                    portal_type="ulearn.community",
                                    community_hash=community_subscription["hash"],
                                )
                                try:
                                    obj = community[0]._unrestrictedGetObject()
                                    logger.info(
                                        "Processant {} de {}. Comunitat {}".format(
                                            num, len(communities_subscription), obj
                                        )
                                    )

                                    gwuuid = IGWUUID(obj).get()
                                    communities_acl = get_or_initialize_annotation("communities_acl")

                                    acl_record = next((r for r in communities_acl.values() if r.get("gwuuid") == gwuuid), None)

                                    # Save ACL into the communities_acl annotation
                                    if acl_record:
                                        acl = acl_record["acl"]
                                        exist = next((a for a in acl["users"] if a["id"] == str(username)), None)

                                        if exist:
                                            acl["users"].remove(exist)
                                            acl_record["acl"] = acl

                                            adapter = obj.adapted()
                                            adapter.set_plone_permissions(adapter.get_acl())


                                except Exception as e:
                                    print(e)
                                    continue

                        try:
                            maxclient.people[username].delete()
                        except Exception as e:
                            # No existe el usuari en max
                            print(e)
                        logger.info("Delete user: {}".format(user))
                    except Exception as e:
                        logger.error("User not deleted: {}".format(user))
                        print(e)

                logger.info("Finished deleted users: {}".format(users))


class deleteUsersInCommunities(BrowserView):
    """Delete users from the plone & max & communities"""

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)

        if self.request.environ["REQUEST_METHOD"] == "POST":

            if self.request.form["users"] != "":
                users = self.request.form["users"].split(",")

                for user in users:
                    user = user.strip()
                    try:
                        pc = api.portal.get_tool(name="portal_catalog")
                        username = user
                        comunnities = pc.unrestrictedSearchResults(
                            portal_type="ulearn.community"
                        )
                        for num, community in enumerate(comunnities):
                            obj = community._unrestrictedGetObject()
                            logger.info(
                                "Processant {} de {}. Comunitat {}".format(
                                    num, len(comunnities), obj
                                )
                            )

                            gwuuid = IGWUUID(obj).get()
                            communities_acl = get_or_initialize_annotation("communities_acl")

                            acl_record = next((r for r in communities_acl.values() if r.get("gwuuid") == gwuuid), None)

                            # Save ACL into the communities_acl annotation
                            if acl_record:
                                acl = acl_record["acl"]
                                exist = next((a for a in acl["users"] if a["id"] == str(username)), None)

                                if exist:
                                    acl["users"].remove(exist)
                                    acl_record["acl"] = acl

                                    adapter = obj.adapted()
                                    adapter.set_plone_permissions(adapter.get_acl())



                        logger.info("Delete user in communities: {}".format(user))
                    except:
                        logger.error("User not deleted in communities: {}".format(user))
                        pass

                logger.info("Finished deleted users in communities: {}".format(users))


class importFileToFolder(BrowserView):
    """This view takes 2 arguments on the request GET data :
    folder: the path without the '/' at the beginning, which is the base folder
        where the 'year' folders should be created
    local_file: the complete path and filename of the file on server. Be carefully if the view is called
        and there are many instanes. The best way is to call it through <ip>:<instance_port>

    To test it: run python script with requests and:
    payload={'folder':'test','local_file': '/home/vicente.iranzo/mongodb_VPN_2016_upcnet.xls'}
    r = requests.get('http://localhost:8080/Plone/importfiletofolder', params=payload, auth=HTTPBasicAuth('admin', 'admin'))
    """

    def __call__(self):
        folder_name = self.request.get("folder")
        local_file = self.request.get("local_file")

        f = open(local_file, "r")
        content = f.read()
        f.close()

        plone_folder = getDestinationFolder(folder_name, create_month=False)
        from plone.protect.interfaces import IDisableCSRFProtection
        from zope.interface import alsoProvides

        alsoProvides(self.request, IDisableCSRFProtection)
        file = NamedBlobFile(
            data=content,
            filename="{}".format(local_file),
            contentType="application/xls",
        )
        obj = createContentInContainer(
            plone_folder,
            "AppFile",
            id="{}".format(local_file.split("/")[-1]),
            title="{}".format(local_file.split("/")[-1]),
            file=file,
            checkConstraints=False,
        )
        self.response.setBody("OK")


class updateSharingCommunityElastic(BrowserView):
    """Aquesta vista actualitza tots els objectes de la comunitat al elasticsearch"""

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)

        if self.request.environ["REQUEST_METHOD"] == "POST":
            pc = api.portal.get_tool("portal_catalog")
            portal = getSite()
            absolute_path = "/".join(portal.getPhysicalPath())
            if self.request.form["id"] != "":
                id_community = absolute_path + "/" + self.request.form["id"]
                logger.info(
                    "Actualitzant elasticsearch dades comunitat {}".format(id_community)
                )
                community = pc.unrestrictedSearchResults(path=id_community)

                if community:
                    obj = community[0]._unrestrictedGetObject()

                elastic_index = ElasticSharing().get_index_name().lower()
                try:
                    self.elastic = getUtility(IElasticSearch)
                    self.elastic().search(index=elastic_index)
                except Exception as e:
                    print(e)
                    self.elastic().indices.create(
                        index=elastic_index,
                        body={
                            "mappings": {
                                "properties": {
                                    "path": {"type": "text"},
                                    "principal": {"type": "keyword", "index": "true"},
                                    "roles": {"type": "text"},
                                    "uuid": {"type": "text"},
                                }
                            }
                        },
                    )

                for brain in community:
                    obj = brain._unrestrictedGetObject()
                    if not ICommunity.providedBy(obj):
                        elastic_sharing = queryUtility(IElasticSharing)
                        elastic_sharing.modified(obj)
                        logger.info(
                            "Actualitzat el objecte {} de la comunitat {}".format(
                                obj, id_community
                            )
                        )


class listAllCommunitiesObjects(BrowserView):
    """returns a json with all the comunities and the number of objects of each one"""

    def __call__(self):
        pc = api.portal.get_tool(name="portal_catalog")
        communities = pc.unrestrictedSearchResults(portal_type="ulearn.community")
        result_list = []
        for num, community in enumerate(communities):
            num_docs = len(pc(path={"query": community.getPath(), "depth": 2}))
            new_com = {
                "community_name": community.getPath(),
                "community_docs": str(num_docs),
            }
            result_list.append(new_com)
        return json.dumps(result_list)


class updateSharingCommunitiesElastic(BrowserView):
    """Aquesta vista actualitza el sharing de tots els objectes de totes les comunitats al elasticsearch"""

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)

        pc = api.portal.get_tool("portal_catalog")
        portal = getSite()
        absolute_path = "/".join(portal.getPhysicalPath())

        comunnities = pc.unrestrictedSearchResults(portal_type="ulearn.community")
        for num, community in enumerate(comunnities):
            obj = community._unrestrictedGetObject()
            id_community = absolute_path + "/" + obj.id
            logger.info(
                "Processant {} de {}. Comunitat {}".format(num, len(comunnities), obj)
            )
            community = pc.unrestrictedSearchResults(path=id_community)
            elastic_index = ElasticSharing().get_index_name().lower()
            try:
                self.elastic = getUtility(IElasticSearch)
                self.elastic().search(index=elastic_index)
            except Exception as e:
                print(e)
                self.elastic().indices.create(
                    index=elastic_index,
                    body={
                        "mappings": {
                            "properties": {
                                "path": {"type": "text"},
                                "principal": {"type": "keyword", "index": "true"},
                                "roles": {"type": "text"},
                                "uuid": {"type": "text"},
                            }
                        }
                    },
                )

            for brain in community:
                obj = brain._unrestrictedGetObject()
                if not ICommunity.providedBy(obj):
                    elastic_sharing = queryUtility(IElasticSharing)
                    elastic_sharing.modified(obj)

                    logger.info(
                        "Actualitzat el objecte {} de la comunitat {}".format(
                            obj, id_community
                        )
                    )

        logger.info(
            "Finished update sharing in communities: {}".format(portal.absolute_url())
        )
        self.response.setBody("OK")


class createElasticSharing(BrowserView):
    """Aquesta vista crea l'index de l'elasticsearch i li diu que el camp principal pot tenir caracters especials 'index': 'not_analyzed'"""

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)
        elastic_index = ElasticSharing().get_index_name().lower()
        try:
            self.elastic = getUtility(IElasticSearch)
            self.elastic().search(index=elastic_index)
        except Exception as e:
            print(e)

            self.elastic().indices.create(
                index=elastic_index,
                body={
                    "mappings": {
                        "properties": {
                            "path": {"type": "text"},
                            "principal": {"type": "keyword", "index": "true"},
                            "roles": {"type": "text"},
                            "uuid": {"type": "text"},
                        }
                    }
                },
            )

            self.response.setBody("OK")


class viewUsersWithNotUpdatedPhoto(BrowserView):
    """Shows the user list that the photo has not been changed"""

    def __call__(self):
        user_properties = get_or_initialize_annotation("user_properties")

        result = {}
        for record in user_properties.values():
            userID = record.get("id")
            if userID and userID != "admin":
                mtool = api.portal.get_tool(name="portal_membership")
                portrait = mtool.getPersonalPortrait(userID)
                typePortrait = portrait.__class__.__name__

                if typePortrait == "FSImage" or (
                    typePortrait == "Image"
                    and portrait.size in (9715, 4831)
                ):
                    fullname = record.get("fullname", "")
                    result[userID] = {"fullname": fullname}

        return result



class deletePhotoFromUser(BrowserView):
    """Delete photo from user, add parameter ?user=nom.cognom"""

    def __call__(self):
        # /deleteUserPhoto?user=nom.cognom
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)

        if "user" in self.request.form and self.request.form["user"] != "":
            user = api.user.get(username=self.request.form["user"])
            if user:
                context = aq_inner(self.context)
                try:
                    context.portal_membership.deletePersonalPortrait(
                        self.request.form["user"]
                    )
                    return (
                        "Done, photo has been removed from user "
                        + self.request.form["user"]
                    )
                except Exception as e:
                    print(e)
                    return (
                        "Error while deleting photo from user "
                        + self.request.form["user"]
                    )
            else:
                return "Error, user " + self.request.form["user"] + " not exist"
        else:
            return "Add parameter ?user=nom.cognom in url"


class executeCronTasks(BrowserView):
    """TODO: .....
    url/execute_cron_tasks/?user=victor&pass=123123
    """

    def __call__(self):
        url = self.context.absolute_url()

        info_cron = {}

        registry = queryUtility(IRegistry)
        settings = registry.forInterface(IUlearnControlPanelSettings, check=False)
        tasks = settings.cron_tasks

        try:
            username = self.request.form["user"]
            password = self.request.form["pass"]
        except Exception as e:
            print(e)
            info_cron.update({"status": "Error not username or password"})
            logger.info(url + ":" + str(info_cron))
            return json.dumps(info_cron)

        info_cron.update({"status": ""})
        for task in tasks:
            result = requests.get(url + "/" + task, auth=(username, password))
            if result.status_code == 200 and "Error" not in result.text:
                info_cron.update({task: "OK"})
            else:
                info_cron.update({task: "Error"})

        info_cron["status"] = "Done executeCronTasks"
        logger.info(url + ":" + str(info_cron))

        return json.dumps(info_cron)


class getInfoCronTasks(BrowserView):
    """TODO: .....
    url/get_info_cron_tasks
    """

    def __call__(self):
        info_cron = {}
        portal = api.portal.get()
        info_cron.update({"site": portal.getPhysicalPath()[2]})
        registry = queryUtility(IRegistry)
        settings = registry.forInterface(IUlearnControlPanelSettings, check=False)
        info_cron.update({"tasks": settings.cron_tasks})
        return json.dumps(info_cron)


class changePermissionsToContent(BrowserView):
    """
    Canvia els permisos a tots el continguts que s'han creat autòmaticament (/news, /gestion, ...)
    """

    def __call__(self):
        portal = getSite()
        langs = api.portal.get_tool(name="portal_languages").getSupportedLanguages()
        delete_permission = (
            "Site Administrator",
            "Manager",
        )
        edit_permission = ("Site Administrator", "Manager", "WebMaster", "Owner")

        portal["front-page"]._Delete_objects_Permission = delete_permission

        if "news" in portal:
            portal["news"]._Delete_objects_Permission = delete_permission

            if "aggregator" in portal["news"]:
                portal["news"][
                    "aggregator"
                ]._Delete_objects_Permission = delete_permission

        if "Members" in portal:
            for user in portal["Members"]:
                portal["Members"][user]._Delete_objects_Permission = delete_permission

                if "banners" in portal["Members"][user]:
                    portal["Members"][user][
                        "banners"
                    ]._Delete_objects_Permission = delete_permission

        if "gestion" in portal:
            portal["gestion"]._Delete_objects_Permission = delete_permission

            if "menu" in portal["gestion"]:
                portal["gestion"]["menu"]._Delete_objects_Permission = delete_permission

                for lang in langs:
                    if lang in portal["gestion"]["menu"]:
                        portal["gestion"]["menu"][
                            lang
                        ]._Delete_objects_Permission = delete_permission

            if "header" in portal["gestion"]:
                portal["gestion"][
                    "header"
                ]._Delete_objects_Permission = delete_permission

                for lang in langs:
                    if lang in portal["gestion"]["header"]:
                        portal["gestion"]["header"][
                            lang
                        ]._Delete_objects_Permission = delete_permission

            if "footer" in portal["gestion"]:
                portal["gestion"][
                    "footer"
                ]._Delete_objects_Permission = delete_permission

                for lang in langs:
                    if lang in portal["gestion"]["footer"]:
                        portal["gestion"]["footer"][
                            lang
                        ]._Delete_objects_Permission = delete_permission

            if "banners" in portal["gestion"]:
                portal["gestion"][
                    "banners"
                ]._Delete_objects_Permission = delete_permission

            if "community-tags" in portal["gestion"]:
                portal["gestion"][
                    "community-tags"
                ]._Delete_objects_Permission = delete_permission

        pc = api.portal.get_tool("portal_catalog")
        communities = pc.unrestrictedSearchResults(portal_type="ulearn.community")

        for community in communities:
            com = community.getObject()
            com.manage_delLocalRoles(["AuthenticatedUsers"])
            # community.getObject().manage_setLocalRoles('AuthenticatedUsers', ['Reader'])

            com._Delete_objects_Permission = (
                "Site Administrator",
                "Manager",
                "WebMaster",
                "Owner",
            )
            com._Modify_portal_content_Permission = edit_permission

            com = community.id
            if "documents" in portal[com]:
                portal[com]["documents"]._Delete_objects_Permission = delete_permission
                portal[com][
                    "documents"
                ]._Modify_portal_content_Permission = edit_permission

            if "events" in portal[com]:
                portal[com]["events"]._Delete_objects_Permission = delete_permission
                portal[com][
                    "events"
                ]._Modify_portal_content_Permission = edit_permission

            if "news" in portal[com]:
                portal[com]["news"]._Delete_objects_Permission = delete_permission
                portal[com]["news"]._Modify_portal_content_Permission = edit_permission

                if "aggregator" in portal[com]["news"]:
                    portal[com]["news"][
                        "aggregator"
                    ]._Delete_objects_Permission = delete_permission
                    portal[com]["news"][
                        "aggregator"
                    ]._Modify_portal_content_Permission = edit_permission

        transaction.commit()
        return "OK"


class addAllCommunitiesAsFavoriteFromAllUsers(BrowserView):
    """
    Añade a favorito todas las comunidades a las que esta suscrito los usuarios
    """

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)

        pc = api.portal.get_tool(name="portal_catalog")
        communities = pc.unrestrictedSearchResults(
            object_provides=ICommunity.__identifier__
        )

        maxclient, settings = getUtility(IMAXClient)()
        maxclient.setActor(settings.max_restricted_username)
        maxclient.setToken(settings.max_restricted_token)

        for community in communities:
            communityObj = community._unrestrictedGetObject()
            community_hash = sha1(communityObj.absolute_url().encode('utf-8')).hexdigest()
            users_subscription = maxclient.contexts[community_hash].subscriptions.get(
                qs={"limit": 0}
            )
            for user in users_subscription:
                IFavorite(communityObj).add(user["username"].strip())
        return "OK"


class addCommunityAsFavoriteFromAllUsers(BrowserView):
    """
    Añade a favorito a todos los usuarios usuarios subcritos a X comunidad
    """

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)
            pass

        if "community" in self.request.form:
            maxclient, settings = getUtility(IMAXClient)()
            maxclient.setActor(settings.max_restricted_username)
            maxclient.setToken(settings.max_restricted_token)

            pc = api.portal.get_tool(name="portal_catalog")
            communities = pc.unrestrictedSearchResults(
                object_provides=ICommunity.__identifier__,
                id=self.request.form["community"],
            )
            if communities:
                for community in communities:
                    communityObj = community._unrestrictedGetObject()
                    community_hash = sha1(communityObj.absolute_url().encode('utf-8')).hexdigest()
                    users_subscription = maxclient.contexts[
                        community_hash
                    ].subscriptions.get(qs={"limit": 0})
                    for user in users_subscription:
                        IFavorite(communityObj).add(user["username"].strip())
                return "OK"
            else:
                return "Community " + self.request.form["community"] + " not exist"
        else:
            return "Error add community parameter - /addcommunityasfavoritefromallusers?community=community.id"


class addProtectedFileInDocumentsCommunity(BrowserView):
    """
    Si esta instalado el paquete ulearn5.externalstorage,
    esta vista añade en la carpeta documentos de todas las comunidades
    que se puedan crear archivos protegidos
    """

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)

        portal = api.portal.get()
        if is_activate_externalstorage(portal):
            pc = api.portal.get_tool("portal_catalog")
            comunnities = pc.unrestrictedSearchResults(portal_type="ulearn.community")
            for community in comunnities:
                com = community.getObject()
                com = community.id
                if "documents" in portal[com]:
                    documents = portal[com]["documents"]

                    behavior = ISelectableConstrainTypes(documents)
                    # Obtengo los contenidos que se pueden añadir en la carpeta documents
                    locallyAllowedTypes = behavior.getLocallyAllowedTypes()
                    logger.info(
                        "LocallyAllowedTypes {} community_id: {} in the portal: {}.".format(
                            locallyAllowedTypes, com, portal.absolute_url()
                        )
                    )
                    if "ExternalContent" not in locallyAllowedTypes:
                        # Le añado el ExternalContent a los contenidos que se pueden añadir en la carpeta documents
                        locallyAllowedTypes.append("ExternalContent")
                        behavior.setLocallyAllowedTypes(locallyAllowedTypes)
                        behavior.setImmediatelyAddableTypes(locallyAllowedTypes)
                        logger.info(
                            "Add ExternalContent in LocallyAllowedTypes {} community_id: {} in the portal: {}.".format(
                                locallyAllowedTypes, com, portal.absolute_url()
                            )
                        )
            return "OK Add Protected File in Folder Documents Communities"

        else:
            return "ulearn5.externalstorage is not active in this site."


class addEtherpadInDocumentsCommunity(BrowserView):
    """
    Si esta instalado el paquete ulearn5.etherpad, esta vista añade
    en la carpeta documentos de todas las comunidades que se puedan
    crear documentos etherpad
    """

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)

        portal = api.portal.get()
        if is_activate_etherpad(portal):
            pc = api.portal.get_tool("portal_catalog")
            comunnities = pc.unrestrictedSearchResults(portal_type="ulearn.community")
            for community in comunnities:
                com = community.getObject()
                com = community.id
                if "documents" in portal[com]:
                    documents = portal[com]["documents"]

                    behavior = ISelectableConstrainTypes(documents)
                    # Obtengo los contenidos que se pueden añadir en la carpeta documents
                    locallyAllowedTypes = behavior.getLocallyAllowedTypes()
                    logger.info(
                        "LocallyAllowedTypes {} community_id: {} in the portal: {}.".format(
                            locallyAllowedTypes, com, portal.absolute_url()
                        )
                    )
                    if "Etherpad" not in locallyAllowedTypes:
                        # Le añado el ExternalContent a los contenidos que se pueden añadir en la carpeta documents
                        locallyAllowedTypes.append("Etherpad")
                        behavior.setLocallyAllowedTypes(locallyAllowedTypes)
                        behavior.setImmediatelyAddableTypes(locallyAllowedTypes)
                        logger.info(
                            "Add Etherpad in LocallyAllowedTypes {} community_id: {} in the portal: {}.".format(
                                locallyAllowedTypes, com, portal.absolute_url()
                            )
                        )
            return "OK Add Etherpad in Folder Documents Communities"

        else:
            return "ulearn5.ethepad is not active in this site."


class notifyManualInCommunity(BrowserView):
    """
    Somo por defecto la notificación por email es automatica esto te la cambia
    a manual para EBCN
    """

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)

        portal = api.portal.get()
        pc = api.portal.get_tool("portal_catalog")
        comunnities = pc.unrestrictedSearchResults(portal_type="ulearn.community")
        for community in comunnities:
            com = community.getObject()
            if com.notify_activity_via_mail == True:
                com.type_notify = "Manual"
                logger.info(
                    "Add Notify Manual in community_id: {} in the portal: {}.".format(
                        com.id, portal.absolute_url()
                    )
                )
                com.reindexObject()

        transaction.commit()
        return "OK Add notify Manual in Communities"


class deleteNominasMes(BrowserView):
    """Aquesta vista esborra les nomines de tots els usuaris d'un mes en concret"""

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)
        if self.request.environ["REQUEST_METHOD"] == "POST":
            pc = api.portal.get_tool("portal_catalog")
            JSONproperties = api.portal.get_tool(
                name="portal_properties"
            ).nomines_properties
            nominas_folder_name = JSONproperties.getProperty(
                "nominas_folder_name"
            ).lower()
            path = (
                "/".join(api.portal.get().getPhysicalPath()) + "/" + nominas_folder_name
            )
            nominas = pc.unrestrictedSearchResults(portal_type="File", path=path)

            if self.request.form["mes"] != "":
                mes_a_borrar = self.request.form["mes"]

                for brain in nominas:
                    obj = brain.getObject()
                    if mes_a_borrar in obj.id:
                        parent = obj.aq_parent
                        parent.manage_delObjects([obj.id])
                        logger.info("Nómina {} borrada".format(obj.id))

                logger.info(
                    "Se han borrado las nóminas del mes {}".format(mes_a_borrar)
                )


class parcheReordenarCarpetas(BrowserView):
    """
    When new content is created, the default folders for news, events and
    Members get the ordering attribute set to unordered.
    Este parche hace que si las carpertas tienen marcado que no sean
    ordenables, lo quita y las permite ordenar
    """

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)

        pc = api.portal.get_tool("portal_catalog")
        for brain in pc(portal_type="Folder"):
            obj = brain.getObject()
            if obj._ordering == "unordered":
                obj.setOrdering("")
                order = obj.getOrdering()
                for id in obj._tree:
                    if id not in order._order():
                        order.notifyAdded(id)
                logger.info("Reordenada carpeta con id: {} .".format(obj.id))
