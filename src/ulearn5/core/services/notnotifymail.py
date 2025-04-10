# -*- coding: utf-8 -*-
import ast
import logging

from plone import api
from plone.restapi.services import Service
from ulearn5.core.services import (UnknownEndpoint, check_methods,
                                   check_required_params, check_roles)
from ulearn5.core.services.utils import lookup_community

logger = logging.getLogger(__name__)


class Notnotifymail(Service):
    """
    - Endpoint: @api/notnotifymail
    - Method: POST
        Required params:
            - username: (str) The username of the user.
            - community_id: (str) The ID of the community.
        Description:
            Makes the user not receive email notifications. If the user is already in the blacklist,
            they will be removed from it (reactivating notifications). Otherwise, the user will be
            added to the blacklist (disabling notifications).

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
    @check_required_params(params=['username', 'community_id'])
    @check_methods(methods=['POST'])
    def reply(self):
        user_id = self.request.form.get('username', None)
        community_id = self.request.form.get('community_id', None)

        community = lookup_community(community_id)
        user = api.user.get(username=user_id)

        if community.mails_users_community_black_lists is None:
            community.mails_users_community_black_lists = {}
        elif not isinstance(community.mails_users_community_black_lists, dict):
            community.mails_users_community_black_lists = ast.literal_eval(
                community.mails_users_community_black_lists)

        if user_id in community.mails_users_community_black_lists:
            community.mails_users_community_black_lists.pop(user_id)
            community.reindexObject()
            response = f'Active notify push user "{user_id}" community "{community_id}"'
        else:
            mail = user.getProperty('email')
            if mail is not None and mail != '':
                community.mails_users_community_black_lists.update({user_id: mail})
                community.reindexObject()
                response = f'Desactive notify push user "{user_id}" community "{community_id}"'
            else:
                response = f'Bad request. User "{user_id}" does not have an email.'
                return {"message": response, "code": 400}

        logger.info(response)
        return {"message": response, "code": 200}
