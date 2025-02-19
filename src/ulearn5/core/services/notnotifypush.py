# -*- coding: utf-8 -*-
import logging

from minimal.core.services import (UnknownEndpoint, check_methods,
                                   check_required_params)
from minimal.core.services.utils import lookup_community
from plone.restapi.services import Service

# from base5.core.adapters.notnotifypush import INotNotifyPush


logger = logging.getLogger(__name__)


class Notnotifypush(Service):
    """
    - Endpoint: @api/notnotifypush
    - Method: POST
        Makes the user not receive push notifications.

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

    @check_required_params(params=['username', 'community'])
    @check_methods(methods=['POST'])
    def reply(self):
        user_id = self.request.form.get('user_id', None)
        community_id = self.request.form('community_id', None)
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
