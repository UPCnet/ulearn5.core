# -*- coding: utf-8 -*-
import logging

from mrs5.max.utilities import IMAXClient
from plone import api
from plone.restapi.services import Service
from base5.core.utils import add_user_to_catalog, get_all_user_properties
from ulearn5.core.services import (UnknownEndpoint, check_methods,
                                   check_required_params)
from zope.component import getUtility

logger = logging.getLogger(__name__)


class Sync(Service):
    """
    - Endpoint: @api/people/sync
    - Method: POST
        Syncs user local registry with remote ldap attributes
    - Subpaths allowed: NO
    """

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if subpath:
            return UnknownEndpoint(f'Unknown sub-endpoint: {"/".join(subpath)}')

        return self.reply()

    @check_methods(methods=['POST'])
    @check_required_params(params=['users'])
    def reply(self):
        maxclient = self.manage_max_client()
        users = self.params.get('users', [])
        notfound_errors = []
        properties_errors = []
        max_errors = []
        users_sync = []

        for userid in users:
            username = userid.lower()
            logger.info(
                f'- API REQUEST /api/people/sync: Synchronize user {username}')

            plone_user = self.find_user(username, ldap=False)
            if not plone_user:
                notfound_errors.append(username)
                continue

            self.delete_user_cache_in_ldap(plone_user)

            # Check user again after cache invalidation
            plone_user = self.find_user(username, ldap=True)
            if not plone_user:
                notfound_errors.append(username)
                continue

            properties = get_all_user_properties(plone_user)

            if not self.manage_add_user_to_catalog(plone_user, properties):
                properties_errors.append(username)

            if not self.sync_user_in_max(plone_user, properties, maxclient):
                max_errors.append(username)
                continue

            users_sync.append(username)

        response = {
            'not_found': notfound_errors,
            'properties_errors': properties_errors,
            'max_errors': max_errors,
            'synced_users': users_sync
        }

        return {"data": response, "code": 200}

    def manage_max_client(self):
        maxclient, settings = getUtility(IMAXClient)()
        maxclient.setActor(settings.max_restricted_username)
        maxclient.setToken(settings.max_restricted_token)

        return maxclient

    def delete_user_cache_in_ldap(self, user):
        """ Invalidate cache of user in ldap """
        username = user.getId()
        for prop in user.getOrderedPropertySheets():
            if 'ldap' in prop.getId():
                ldap = prop
                ldap._invalidateCache(user)
                user._getPAS().ZCacheable_invalidate(view_name='_findUser-' + username)
                ldap._getLDAPUserFolder(user)._expireUser(username)
                return
            else:
                continue

    def manage_add_user_to_catalog(self, user, properties):
        """ Will return False if it fails """
        username = user.getId()
        try:
            add_user_to_catalog(user, properties, overwrite=True)
            return True
        except Exception as e:
            logger.error(
                'Cannot update properties catalog for user {}'.format(username))

        return False

    def sync_user_in_max(self, user, properties, maxclient):
        username = user.getId()
        try:
            fullname = properties.get('fullname', '')
            maxclient.people.post(username=username, displayName=fullname)

            # If user hasn't been created right now, update displayName
            if maxclient.last_response_code == 200:
                maxclient.people[username].put(displayName=fullname)

            logger.info(
                f'- API REQUEST /api/people/sync: OK sync user {username}')
            return True
        except Exception as e:
            logger.error(
                f'User {username} couldn\'t be created or updated on max')

        return False

    def find_user(self, username, ldap=False):
        message = f'- API REQUEST /api/people/sync: ERROR sync user {username}'
        if ldap:
            message = f'User {username} cannot be found in LDAP repository'

        user_memberdata = api.user.get(username=username)
        if not user_memberdata:
            logger.error(message)
            return None

        return user_memberdata.getUser()
