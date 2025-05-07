# -*- coding: utf-8 -*-
import logging

from plone import api
from plone.restapi.services import Service
from ulearn5.core.services import (BadParameters, UnknownEndpoint,
                                   check_methods, check_roles)

from ulearn5.core.content.community import ICommunityACL

logger = logging.getLogger(__name__)


class SaveEditACL(Service):
    """
    - Endpoint: @api/saveeditacl
    - Method: GET
        Launch an editacl Save process on all communities.

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

    @check_roles(roles=['Api'])
    @check_methods(methods=['GET'])
    def reply(self):
        results = []
        communities_ok = []
        communities_error = []
        communities = self.get_communities()

        for item in communities:

            try:
                unrestricted_obj = item._unrestrictedGetObject()
                payload = ICommunityACL(unrestricted_obj)().attrs.get('acl', '')

                logger.info(
                    f'---- Community: {str(unrestricted_obj.absolute_url())} ----')
                logger.info(f'---- Payload: {str(payload)} ----')

                adapter = unrestricted_obj.adapted(request=self.request)
                adapter.update_acl(payload)

                users = payload.get('users', [])
                users_checked = self.check_users(adapter, users)

                self.make_adapter_operations(adapter, unrestricted_obj)

                updated = f'Updated community subscriptions on: {str(unrestricted_obj.absolute_url())}'
                logger.info(updated)
                communities_ok.append(dict(url=unrestricted_obj.absolute_url(),
                                           users_checked=users_checked))

            except Exception as e:
                logger.error(
                    f'Error updating community subscriptions on: {unrestricted_obj.absolute_url()}')
                communities_error.append(unrestricted_obj.absolute_url())

        results.append({
            'successfully_updated_communities': communities_ok,
            'error_updating_communities': communities_error
        })

        return results

    def get_communities(self):
        """ Get all communities """
        pc = api.portal.get_tool('portal_catalog')
        communities = pc.unrestrictedSearchResults(portal_type='ulearn.community')

        return communities

    def check_users(self, adapter, users):
        """ Check users and update their roles """
        users_checked = []
        for user in users:

            try:
                adapter.update_acl_atomic(user['id'], user['role'])
                users_checked.append(f'{user["id"]} as role {user["role"]}')
            except Exception as e:
                raise BadParameters(user)

        return users_checked

    def make_adapter_operations(self, adapter, unrestricted_obj):
        """ Make the adapter operations """
        acl = adapter.get_acl()
        adapter.set_plone_permissions(acl)
        adapter.update_hub_subscriptions()

        if ((unrestricted_obj.notify_activity_via_mail == True) and (unrestricted_obj.type_notify == 'Automatic')):
            adapter.update_mails_users(unrestricted_obj, acl)

        return acl
