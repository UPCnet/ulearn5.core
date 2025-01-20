from __future__ import print_function
from plone import api
from Acquisition import aq_parent
from Acquisition import aq_inner
from zope.component import getUtility
from zope.component import queryUtility
from zope.component import getMultiAdapter

from zope.interface import alsoProvides
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent
from Products.Five.browser import BrowserView
from Products.CMFPlone.interfaces.constrains import ISelectableConstrainTypes

from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletAssignmentMapping
from plone.subrequest import subrequest
from plone.uuid.interfaces import IUUIDGenerator

from Products.CMFPlone.interfaces import IPloneSiteRoot

from ulearn5.core.interfaces import (
    IDocumentFolder,
    ILinksFolder,
    IPhotosFolder,
    IEventsFolder,
    INewsItemFolder,
    IFolder,
)
from ulearn5.core.content.community import IInitializedCommunity
from ulearn5.core.content.community import Community

from ulearn5.core.gwuuid import ATTRIBUTE_NAME
from ulearn5.core import _
from base5.core.utils import get_safe_member_by_id
from mrs5.max.utilities import IMAXClient
from max5.client.rest import RequestError

from itertools import chain
import logging

logger = logging.getLogger(__name__)


def listPloneSites(zope):
    """List the available plonesites to be used by other function"""
    out = []
    for item in list(zope.values()):
        if IFolder.providedBy(item) and not IPloneSiteRoot.providedBy(item):
            for site in list(item.values()):
                if IPloneSiteRoot.providedBy(site):
                    out.append(site)
        elif IPloneSiteRoot.providedBy(item):
            out.append(item)
    return out


def createMAXUser(username):
    maxclient, settings = getUtility(IMAXClient)()
    maxclient.setActor(settings.max_restricted_username)
    maxclient.setToken(settings.max_restricted_token)

    try:
        maxclient.people[username].post()

        if maxclient.last_response_code == 201:
            logger.info("MAX user created for user: %s" % username)
        elif maxclient.last_response_code == 200:
            logger.info("MAX user already created for user: %s" % username)

    except RequestError:
        import ipdb

        ipdb.set_trace()
    except Exception as e:
        print(e)
        logger.error("Error creating MAX user for user: %s" % username)


class Portletfix(BrowserView):

    def __call__(self):
        pc = api.portal.get_tool(name="portal_catalog")
        communities = pc.searchResults(portal_type="ulearn.community")

        for community in communities:
            community = community.getObject()
            target_manager = queryUtility(
                IPortletManager, name="plone.leftcolumn", context=community
            )
            target_manager_assignments = getMultiAdapter(
                (community, target_manager), IPortletAssignmentMapping
            )
            for portlet in list(target_manager_assignments.keys()):
                del target_manager_assignments[portlet]

            target_manager = queryUtility(
                IPortletManager, name="plone.rightcolumn", context=community
            )
            target_manager_assignments = getMultiAdapter(
                (community, target_manager), IPortletAssignmentMapping
            )
            for portlet in list(target_manager_assignments.keys()):
                del target_manager_assignments[portlet]


class LinkFolderFix(BrowserView):

    def __call__(self):
        pc = api.portal.get_tool(name="portal_catalog")
        folder_ifaces = {
            IDocumentFolder.__identifier__: "documents",
            ILinksFolder.__identifier__: "links",
            IPhotosFolder.__identifier__: "media",
            IEventsFolder.__identifier__: "events",
            INewsItemFolder.__identifier__: "news",
        }

        for iface in list(folder_ifaces.keys()):
            results = pc.searchResults(object_provides=iface)
            for result in results:
                parent = aq_parent(aq_inner(result.getObject()))
                parent.manage_renameObjects((result.id,), (folder_ifaces[iface],))
                print(
                    (
                        "renamed {} to {} in community {}".format(
                            result.id, folder_ifaces[iface], parent
                        )
                    )
                )


class CreateMAXUserForAllExistingUsers(BrowserView):

    def __call__(self):
        mtool = api.portal.get_tool(name="portal_membership")

        searchView = getMultiAdapter(
            (aq_inner(self.context), self.request), name="pas_search"
        )

        searchString = ""

        self.request.set("__ignore_group_roles__", True)
        self.request.set("__ignore_direct_roles__", False)
        explicit_users = searchView.merge(
            chain(
                *[
                    searchView.searchUsers(**{field: searchString})
                    for field in ["login", "fullname", "email"]
                ]
            ),
            "userid",
        )

        for user_info in explicit_users:
            userId = user_info["id"]
            user = mtool.getMemberById(userId)
            createMAXUser(user.getUserName())


class InitializeAllCommunities(BrowserView):

    def __call__(self):
        pc = api.portal.get_tool(name="portal_catalog")
        results = pc.searchResults(portal_type="ulearn.community")
        for result in results:
            community = result.getObject()
            if not IInitializedCommunity.providedBy(community):
                logger.error(
                    "Initializing community {}".format(community.absolute_url())
                )
                alsoProvides(community, IInitializedCommunity)
                notify(ObjectModifiedEvent(community))


class InitializeVideos(BrowserView):

    def __call__(self):
        pc = api.portal.get_tool(name="portal_catalog")
        communities = pc.searchResults(portal_type="ulearn.community")

        text = []
        for community in communities:
            community = community.getObject()
            media_folder = community.media

            behavior = ISelectableConstrainTypes(media_folder)
            behavior.setConstrainTypesMode(1)
            behavior.setLocallyAllowedTypes(("Image", "ulearn.video", "Folder"))
            behavior.setImmediatelyAddableTypes(("Image", "ulearn.video", "Folder"))

            if media_folder.title != "Media":
                media_folder.setTitle(community.translate(_("Media")))

            text.append("Added type video to {}\n".format(community.absolute_url()))
        return "".join(text)


class MigrateCommunities(BrowserView):
    """It should be executed on an running instance with no MAX hooks enabled
    to avoid them to be executed when persisting the new communities objects
    """

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)
            pass
        portal = api.portal.get()
        pc = api.portal.get_tool(name="portal_catalog")
        communities = pc.searchResults(portal_type="ulearn.community")

        text = []
        for community_brain in communities:
            # We assume that there will be only communities in Portal Site Root
            community = portal[community_brain.id]
            if community.__class__ != Community:
                portal._delOb(community_brain.id)

                community.__class__ = Community
                portal._setOb(community.id, community)

                text.append("Migrated community {}\n".format(community.absolute_url()))
        return "".join(text) + "\nDone!"


class MigrateTypesDocumentsCommunities(BrowserView):
    """It should be executed on an running instance with no MAX hooks enabled
    to avoid them to be executed when persisting the new communities objects
    """

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)
            pass
        portal = api.portal.get()
        pc = api.portal.get_tool(name="portal_catalog")
        communities = pc.searchResults(portal_type="ulearn.community")

        text = []
        for community_brain in communities:
            # We assume that there will be only communities in Portal Site Root
            community = portal[community_brain.id]

            # Set on them the allowable content types
            behavior = ISelectableConstrainTypes(community["documents"])
            behavior.setConstrainTypesMode(1)
            behavior.setLocallyAllowedTypes(
                (
                    "Document",
                    "File",
                    "Folder",
                    "Link",
                    "Image",
                    "privateFolder",
                    "ulearn.video",
                    "ulearn.video_embed",
                )
            )
            behavior.setImmediatelyAddableTypes(
                (
                    "Document",
                    "File",
                    "Folder",
                    "Link",
                    "Image",
                    "privateFolder",
                    "ulearn.video",
                    "ulearn.video_embed",
                )
            )

            community.reindexObject()

            text.append(
                "Migrated types community {}\n".format(community.absolute_url())
            )

        return "".join(text) + "\nDone!"


class ReinstalluLearn(BrowserView):
    """Reinstalls uLearn in the current Plone site."""

    def __call__(self):
        context = aq_inner(self.context)
        output = []
        qi = api.portal.get_tool(name="portal_quickinstaller")

        if qi.isProductInstalled("ulearn5.core"):
            qi.reinstallProducts(["ulearn5.core"])
            output.append("{}: Successfully reinstalled ulearn5.core".format(context))
        return "\n".join(output)


class ReinstalluLearnControlPanel(BrowserView):
    """Reinstalls uLearn in the current Plone site."""

    def __call__(self):
        context = aq_inner(self.context)
        output = []

        setup = api.portal.get_tool("portal_setup")
        profile_id = "profile-ulearn5.core:default"
        step_id = "plone.app.registry"
        setup.runImportStepFromProfile(
            profile_id, step_id, run_dependencies=True, purge_old=None
        )
        output.append(
            "{}: Successfully reinstalled ulearn5.core control panel".format(context)
        )

        return "\n".join(output)


class BulkReinstalluLearn(BrowserView):
    """
    Reinstall base5.core.controlpanel in all the Plone instance of this Zope.
    Useful when added some parameter to the control panel and you want to
    apply it at the same time in all the existing Plone sites in the Zope.
    """

    def __call__(self):
        context = aq_inner(self.context)
        plonesites = listPloneSites(context)
        output = []
        for plonesite in plonesites:
            response = subrequest(
                "/".join(plonesite.getPhysicalPath()) + "/reinstall_ulearncontrolpanel"
            )
            output.append(response.getBody())
        return "\n".join(output)


class GiveAllCommunitiesGWUUID(BrowserView):

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)
            pass
        pc = api.portal.get_tool("portal_catalog")
        communities = pc.searchResults(portal_type="ulearn.community")

        generator = queryUtility(IUUIDGenerator)
        if generator is None:
            return

        for community in communities:
            obj = community.getObject()
            if not getattr(obj, ATTRIBUTE_NAME, False):
                uuid = generator()
                if not uuid:
                    return

                setattr(obj, ATTRIBUTE_NAME, uuid)
                obj.reindexObject(idxs=["gwuuid"])

        # pc.clearFindAndRebuild()

        return "Done"


class GiveGWUUID(BrowserView):

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)
            pass
        pc = api.portal.get_tool("portal_catalog")
        communities = pc.unrestrictedSearchResults(portal_type="ulearn.community")

        generator = queryUtility(IUUIDGenerator)
        if generator is None:
            return

        for community in communities:
            obj_community = community.getObject()
            results = pc.unrestrictedSearchResults(
                path=("/".join(obj_community.getPhysicalPath()))
            )
            for result in results:
                obj = result.getObject()
                if not getattr(obj, ATTRIBUTE_NAME, False):
                    uuid = generator()
                    if not uuid:
                        return

                    setattr(obj, ATTRIBUTE_NAME, uuid)
                    obj.reindexObject(idxs=["gwuuid"])
        # pc.clearFindAndRebuild()

        return "Done"


class MigrateOldStyleACLs(BrowserView):

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)
            pass
        pc = api.portal.get_tool("portal_catalog")
        communities = pc.searchResults(portal_type="ulearn.community")
        permission_map = {
            "readers": "reader",
            "subscribed": "writer",
            "owners": "owner",
        }

        for brain in communities:
            acl = dict(users=[], groups=[])
            community = brain.getObject()
            adapter = community.adapted()

            logger.warning("{} -- {}".format(community.id, community.absolute_url()))

            for old_role in permission_map:
                users = getattr(community, old_role)
                for username in users:
                    acl["users"].append(
                        dict(
                            id=username,
                            displayName=get_safe_member_by_id(username).get(
                                "fullname", ""
                            ),
                            role=permission_map[old_role],
                        )
                    )
            adapter.update_acl(acl)
            try:
                adapter.update_hub_subscriptions()
            except Exception as e:
                print(e)
                pass

            logger.warning(
                "migrated community {} with acl: {}".format(
                    community.absolute_url(), acl
                )
            )

        return "Done"


class MigrateOldStyleFolders(BrowserView):

    def __call__(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection

            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception as e:
            print(e)
            pass
        pc = api.portal.get_tool("portal_catalog")
        communities = pc.searchResults(portal_type="ulearn.community")

        for brain in communities:
            obj = brain.getObject()

            # Set the default view to 'documents' folder
            obj["documents"].setLayout("filtered_contents_search_view")

            if "media" in obj.objectIds():
                if IPhotosFolder.providedBy(obj["media"]):
                    try:
                        api.content.move(
                            source=obj["media"], target=obj["documents"], safe_id=True
                        )
                        logger.warning(
                            'Successfully migrated "links" community folder {}.'.format(
                                obj.absolute_url()
                            )
                        )
                    except Exception as e:
                        print(e)
                        logger.error(
                            'Error moving content from "media" folder: {}'.format(
                                obj.absolute_url()
                            )
                        )

            if "links" in obj.objectIds():
                if ILinksFolder.providedBy(obj["links"]):
                    # If it's empty do nothing
                    if obj["links"].objectIds():
                        try:
                            api.content.move(
                                source=obj["links"],
                                target=obj["documents"],
                                safe_id=True,
                            )
                            logger.warning(
                                'Successfully migrated "links" community folder {}.'.format(
                                    obj.absolute_url()
                                )
                            )
                        except Exception as e:
                            print(e)
                            logger.error(
                                'Error moving content from "links" folder: {}'.format(
                                    obj.absolute_url()
                                )
                            )
                    else:
                        logger.warning(
                            "The links folder in {} is empty. Doing nothing.".format(
                                obj.absolute_url()
                            )
                        )

        return "Done"


class BulkRestrictTransformuLearn(BrowserView):
    """
    Restrict script and other nasty tags to uLearn
    """

    def setup_safe_html_transform(self, portal):
        transforms = api.portal.get_tool(name="portal_transforms")
        transform = getattr(transforms, "safe_html")

        valid = transform.get_parameter_value("valid_tags")
        nasty = transform.get_parameter_value("nasty_tags")
        stripped = transform.get_parameter_value("stripped_attributes")

        # uLearn nasty tags
        ulearn_nasty = ["script", "applet", "iframe"]
        for tag in ulearn_nasty:
            if tag in valid:
                # Delete from valid
                valid[tag] = 0
                del valid[tag]
            # Add to nasty
            if tag not in nasty:
                nasty[tag] = 1

        current_style_whitelist = [
            a for a in transform.get_parameter_value("style_whitelist")
        ]
        current_style_whitelist.append("color")

        kwargs = {}
        kwargs["valid_tags"] = valid
        kwargs["nasty_tags"] = nasty
        kwargs["stripped_attributes"] = stripped
        kwargs["style_whitelist"] = current_style_whitelist
        for k in list(kwargs):
            if isinstance(kwargs[k], dict):
                v = kwargs[k]
                kwargs[k + "_key"] = list(v.keys())
                kwargs[k + "_value"] = [str(s) for s in list(v.values())]
                del kwargs[k]

        transform.set_parameters(**kwargs)
        transform._p_changed = True
        transform.reload()

    def __call__(self):
        context = aq_inner(self.context)
        plonesites = listPloneSites(context)
        output = []
        for plonesite in plonesites:
            self.setup_safe_html_transform(plonesite)
            output.append("Restricted {}".format(plonesite.id))
            # response = subrequest('/'.join(plonesite.getPhysicalPath()) + '/reinstall_ulearncontrolpanel')
            # output.append(response.getBody())
        return "\n".join(output)
