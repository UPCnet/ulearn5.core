# -*- coding: utf-8 -*-
import ast
import logging
from hashlib import sha1

from DateTime.DateTime import DateTime
from mrs5.max.utilities import IMAXClient
from plone import api
from plone.restapi.services import Service
from ulearn5.core.services import UnknownEndpoint, check_methods, check_roles
from zope.component import getUtility
from repoze.catalog.query import Eq
from souper.soup import get_soup

logger = logging.getLogger(__name__)


class UserSubscriptions(Service):
    """
    - Endpoint: @api/people/{username}/subscriptions
    - Method: GET
        Manages the user subscriptions.
    - Subpaths allowed: NO
    """

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request
        self.username = kwargs.get('username')

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if subpath:
            return UnknownEndpoint(f'Unknown sub-endpoint: {"/".join(subpath)}')

        return self.reply()

    @check_methods(methods=['GET'])
    @check_roles(roles=['Member',])
    def reply(self):
        communities = self.get_communities_for_current_user()
        maxclient = self.manage_maxclient()
        communities_subscription = maxclient.people[self.username].subscriptions.get()

        result = []
        favorites = self.get_favorites()
        notnotifypush = self.get_notnotifypush()

        pc = api.portal.get_tool(name='portal_catalog')
        portal_url = api.portal.get().absolute_url()

        for obj in communities_subscription:
            brain = pc.unrestrictedSearchResults(portal_type='ulearn.community', community_hash=obj['hash'])

            if not brain:
                logger.warning(f"No community found for hash: {obj['hash']}")
                continue

            brain = brain[0]
            can_write = True if 'write' in obj['permissions'] else False
            brainObj = self.context.unrestrictedTraverse(brain.getPath())

            if brainObj.mails_users_community_black_lists is None:
                brainObj.mails_users_community_black_lists = {}
            elif not isinstance(brainObj.mails_users_community_black_lists, dict):
                brainObj.mails_users_community_black_lists = ast.literal_eval(
                    brainObj.mails_users_community_black_lists)

            result.append({
                'id': brain.id,
                'title': brain.Title,
                'description': brain.Description,
                'url': brain.getURL(),
                'gwuuid': brain.gwuuid,
                'hash': sha1(brain.absolute_url().encode('utf-8')).hexdigest(),
                'type': brain.community_type,
                'image': brain.image_filename if brain.image_filename else False,
                'image_url': brain.getURL() + '/thumbnail-image' if brain.image_filename else portal_url + '/++theme++ulearn5/assets/images/avatar_default.png',
                'favorited': brain.id in favorites,
                'pending': self.get_pending_community_user(brain, self.username),
                'activate_notify_push': brainObj.notify_activity_via_push or brainObj.notify_activity_via_push_comments_too,
                'activate_notify_mail': brainObj.notify_activity_via_mail and brainObj.type_notify == 'Automatic',
                'not_notify_push': brain.id in notnotifypush,
                'not_notify_mail': self.username in brainObj.mails_users_community_black_lists,
                'can_manage': self.is_community_manager(brain),
                'can_write': can_write
            })

        return result

    def get_communities_for_current_user(self):
        pc = api.portal.get_tool('portal_catalog')
        r_results_organizative = pc.searchResults(
            portal_type="ulearn.community", community_type="Organizative",
            sort_on="sortable_title")
        r_results_closed = pc.searchResults(
            portal_type="ulearn.community", community_type="Closed",
            sort_on="sortable_title")
        ur_results_open = pc.unrestrictedSearchResults(
            portal_type="ulearn.community", community_type="Open",
            sort_on="sortable_title")

        return r_results_organizative + r_results_closed + ur_results_open

    def manage_maxclient(self):
        maxclient, settings = getUtility(IMAXClient)()
        maxclient.setActor(settings.max_restricted_username)
        maxclient.setToken(settings.max_restricted_token)

        return maxclient

    def check_if_current_user_is_manager(self):
        global_roles = api.user.get_roles()
        return 'Manager' in global_roles

    def get_favorites(self):
        pc = api.portal.get_tool('portal_catalog')

        results = pc.unrestrictedSearchResults(favoritedBy=self.username)
        return [favorites.id for favorites in results]

    def get_notnotifypush(self):
        pc = api.portal.get_tool('portal_catalog')

        results = pc.unrestrictedSearchResults(notNotifyPushBy=self.username)
        return [notnotifypush.id for notnotifypush in results]

    def get_pending_community_user(self, community, user):
        """ Returns the number of pending objects to see in the community. """
        data_access = self.get_data_access_community_user(community, user) + 0.001
        now = DateTime() + 0.001  # Suma 0.001 para que no muestre los que acaba de crear el usuario
        pc = api.portal.get_tool(name="portal_catalog")

        date_range_query = {'query': (data_access, now), 'range': 'min:max'}

        results = pc.searchResults(path=community.getPath(), created=date_range_query)
        return len(results) if results else 0

    def get_data_access_community_user(self, community, user):
        """ Returns the date of user access to the community. """
        portal = api.portal.get()
        user_community = user + '_' + community.id
        user_community_access = get_soup('user_community_access', portal)

        exist = [r for r in user_community_access.query(Eq('user_community', user_community))]

        if not exist:
            record = DateTime()
        else:
            record = exist[0].attrs['data_access']

        return record

    def is_community_manager(self, community):
        """ Check if user has role 'Manager' """
        global_roles = api.user.get_roles()
        if 'Manager' in global_roles:
            return True

        gwuuid = community.gwuuid
        catalog = api.portal.get_tool(name='portal_catalog')
        results = catalog.unrestrictedSearchResults({'gwuuid': gwuuid})

        if results:
            community_brain = results[0]
            community_obj = community_brain.getObject()
            acl = getattr(community_obj, 'acl', None)
            if acl:
                return self.username in [
                    a['id'] for a in acl['users']
                    if a['role'] == 'owner']

        return False