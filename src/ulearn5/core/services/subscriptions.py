# -*- coding: utf-8 -*-
import logging

from plone.restapi.services import Service
from ulearn5.core.services import (BadParameters, MethodNotAllowed,
                                   UnknownEndpoint, check_methods,
                                   check_required_params, check_roles)

from ulearn5.core.content.community import ICommunityACL


logger = logging.getLogger(__name__)


class Subscriptions(Service):
    """
    - Endpoint: @api/communities/{community}/subscriptions
    - Method: GET
        Get the subscriptions for the community
    - Method: POST
        Subscribes a bunch of users to a community
    - Method: PUT
        Subscribes a bunch of users to a community
    - Method: DELETE
        Unsubscribes users from a community

    - Subpaths allowed: NO
    """

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request
        self.obj = kwargs.get('obj', None)

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if subpath:
            return UnknownEndpoint(f'Unknown sub-endpoint: {"/".join(subpath)}')

        return self.reply()

    @check_methods(methods=['GET', 'POST', 'PUT', 'DELETE'])
    @check_roles(roles=['Owner', 'Manager', 'Api'])
    def reply(self):
        method = self.request.get('method')
        if method == 'GET':
            return self.reply_get()
        elif method == 'POST':
            return self.reply_post()
        elif method == 'PUT':
            return self.reply_put()
        elif method == 'DELETE':
            return self.reply_delete()
        raise MethodNotAllowed(f"Unknown method: {method}")

    def reply_get(self):
        """ Get the subscriptions for the community. """
        result = ICommunityACL(self.obj)().attrs.get('acl', '')

        return result

    @check_required_params(params=['users'])
    def reply_post(self):
        """ Subscribes a bunch of users to a community """
        self.set_subscriptions(self.params)

        # Response successful
        success_response = f'Updated community "{self.obj.absolute_url()}" subscriptions'
        logger.info(success_response)
        return {"message": success_response, "code": 200}

    @check_required_params(params=['users'])
    def reply_put(self):
        """ Subscribes a bunch of users to a community """
        self.update_subscriptions()

        # Response successful
        success_response = f'Updated community "{self.target.absolute_url()}" subscriptions'
        logger.info(success_response)
        return {"message": success_response, "code": 200}

    @check_required_params(params=['users'])
    def reply_delete(self):
        """ Remove subscriptions from a bunch of users to a community """
        self.remove_subscriptions()

        # Response successful
        success_response = 'Unsubscription to the requested community done.'
        logger.info(success_response)
        return {"message": success_response, "code": 200}

    def set_subscriptions(self, payload):
        adapter = self.obj.adapted(request=self.request)
        adapter.update_acl(payload)
        acl = adapter.get_acl()
        adapter.set_plone_permissions(acl)

        # Communicate the change in the community subscription to the uLearnHub
        # XXX: Until we do not have a proper Hub online
        adapter.update_hub_subscriptions()

        if ((self.obj.notify_activity_via_mail == True) and (self.obj.type_notify == 'Automatic')):
            adapter.update_mails_users(self.obj, acl)

    def update_subscriptions(self):
        self._modify_subscriptions()

    def remove_subscriptions(self):
        self._modify_subscriptions(action='remove')

    def _modify_subscriptions(self, action='update'):
        """ Either remove or update a subscription """
        adapter = self.obj.adapted(request=self.request)

        users = self.request.form.pop('users')
        for user in users:
            try:
                if action == 'remove':
                    adapter.remove_acl_atomic(user['id'])
                    continue

                adapter.update_acl_atomic(user['id'], user['role'])
            except:
                raise BadParameters(user)

        acl = adapter.get_acl()
        adapter.set_plone_permissions(acl)
        adapter.update_hub_subscriptions()
