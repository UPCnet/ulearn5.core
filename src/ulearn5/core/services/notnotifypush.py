# -*- coding: utf-8 -*-
import logging

from plone.restapi.services import Service
from ulearn5.core.services import (UnknownEndpoint, check_methods,
                                   check_required_params, check_roles)
from ulearn5.core.services.utils import lookup_community

from base5.core.adapters.notnotifypush import INotNotifyPush


logger = logging.getLogger(__name__)


class Notnotifypush(Service):
    """
    - Endpoint: @api/notnotifypush
    - Method: POST
        Required params:
            - username: (str) The username of the user.
            - community: (str) The ID of the community.
        Description:
            Makes the user not receive push notifications. If the user is already in the blacklist,
            they will be removed from it (reactivating push notifications). Otherwise, the user will
            be added to the blacklist (disabling push notifications).

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

    @check_roles(roles=['Member', 'Manager', 'Api'])
    @check_required_params(params=['username', 'community'])
    @check_methods(methods=['POST'])
    def reply(self):
        user_id = self.request.form.get('username', None)
        community_id = self.request.form.get('community', None)
        community = lookup_community(community_id)

        adapter = community.adapted()
        if user_id in INotNotifyPush(community).get():
            INotNotifyPush(community).remove(user_id)
            adapter.subscribe_user_push(user_id)
            response = f'Active notify push user "{user_id}" community "{community_id}"'
        else:
            INotNotifyPush(community).add(user_id)
            adapter.unsubscribe_user_push(user_id)
            response = f'Desactive notify push user "{user_id}" community "{community_id}"'

        logger.info(response)
        return {"message": response, "code": 200}
