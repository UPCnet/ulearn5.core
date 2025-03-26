# -*- coding: utf-8 -*-
import logging

from DateTime.DateTime import DateTime
from plone.restapi.services import Service
from ulearn5.core.services import (UnknownEndpoint, check_methods,
                                   check_required_params)
from ulearn5.core.utils import get_or_initialize_annotation
from repoze.catalog.query import Eq
from souper.soup import Record
from souper.soup import get_soup
# from ulearn5.core.controlpanel import IUlearnControlPanelSettings
# from ulearn5.core.utils import calculatePortalTypeOfInternalPath


logger = logging.getLogger(__name__)


class Visualizations(Service):
    """
    - Endpoint: @api/people/{username}/visualizations
    - Method: PUT
        Updates pending visualizations for a community
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

    @check_methods(methods=['PUT'])
    @check_required_params(params=['community'])
    def reply(self):
        portal = api.portal.get()
        user_community = self.username + '_' + self.request.form.get('community')
        user_community_access = get_soup('user_community_access', portal)

        record = self.get_or_create_record(user_community_access, user_community)

        return {"success": "Visualitzacions pendents actualitzades", "code": 200}

    def get_or_create_record(self, user_community_access, user_community):
        exist = [r for r in user_community_access.query(Eq('user_community', user_community))]

        if not exist:
            record = Record()
            record.attrs['user_community'] = user_community
            record.attrs['data_access'] = DateTime()
            user_community_access.add(record)
        else:
            exist[0].attrs['data_access'] = DateTime()
            record = exist[0]
        user_community_access.reindex()

        return record
