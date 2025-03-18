# -*- coding: utf-8 -*-
import ast
import logging
from hashlib import sha1

from DateTime.DateTime import DateTime
# from mrs5.max.utilities import IMAXClient
from plone import api
from plone.restapi.services import Service
from ulearn5.core.services import UnknownEndpoint, check_methods, check_roles
from ulearn5.core.services.utils import lookup_community
from ulearn5.core.utils import get_or_initialize_annotation
from zope.component import getUtility

# from ulearn5.core.controlpanel import IUlearnControlPanelSettings
# from ulearn5.core.utils import calculatePortalTypeOfInternalPath


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

        for obj in communities_subscription:
            community = lookup_community(obj['hash'])
            if not community:
                continue

            can_write = 'write' in obj['permissions']
            if community.mails_users_community_black_lists is None:
                community.mails_users_community_black_lists = {}
            elif not isinstance(community.mails_users_community_black_lists, dict):
                community.mails_users_community_black_lists = ast.literal_eval(
                    community.mails_users_community_black_lists)

            portal_url = api.portal.get().absolute_url()

            result.append({
                'id': community.getId(),
                'title': community.Title(),
                'description': community.Description(),
                'url': community.absolute_url(),
                'gwuuid': community.gwuuid,
                'hash': sha1(community.absolute_url().encode('utf-8')).hexdigest(),
                'type': community.community_type,
                'image': community.image_filename if community.image_filename else False,
                'image_url': community.getURL() + '/thumbnail-image' if community.image_filename else portal_url + '/++theme++ulearn5/assets/images/avatar_default.png',
                'favorited': community.id in favorites,
                'pending': self.get_pending_community_user(community, self.username),
                'activate_notify_push': community.notify_activity_via_push or community.notify_activity_via_push_comments_too,
                'activate_notify_mail': community.notify_activity_via_mail and community.type_notify == 'Automatic',
                'not_notify_push': community.id in notnotifypush,
                'not_notify_mail': self.username in community.mails_users_community_black_lists,
                'can_manage': self.is_community_manager(community),
                'can_write': can_write
            })

        return {"data": result, "code": 200}

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
        user_community = user + '_' + community.id
        user_community_access = get_or_initialize_annotation('user_community_access')

        record = next((r for r in user_community_access.values()
                       if r.get('user_community') == user_community), None)

        return record.get('data_access', DateTime()) if record else DateTime()
