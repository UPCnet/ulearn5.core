# -*- coding: utf-8 -*-
from five import grok

from Products.CMFPlone.interfaces import IPloneSiteRoot
from plone import api

from repoze.catalog.query import Eq
from souper.soup import get_soup

from ulearn5.core.api import REST
from ulearn5.core.api import api_resource
from ulearn5.core.api import ApiResponse

from ulearn5.core.api.root import APIRoot


class Groups(REST):
    """
        /api/groups
    """

    placeholder_type = 'group'
    placeholder_id = 'group'

    grok.adapts(APIRoot, IPloneSiteRoot)
    # grok.require('genweb.authenticated')


class Group(REST):
    """
        /api/groups/{group}
    """

    grok.adapts(Groups, IPloneSiteRoot)
    # grok.require('genweb.authenticated')


class Communities(REST):
    """
        /api/groups/{group}/communities

        Returns

        {
            'url': context['url'],
            'groups': [],
            'users': ['testuser1.creator']
        }

    """

    grok.adapts(Group, IPloneSiteRoot)
    # grok.require('ulearn.APIAccess')

    @api_resource()
    def GET(self):
        """

        """
        portal = api.portal.get()
        soup = get_soup('communities_acl', portal)
        records = [r for r in soup.query(Eq('groups', self.params['group']))]

        result = []
        for record in records:
            users = [user['id'] for user in record.attrs['acl']['users']]
            result.append(dict(
                url=record.attrs['hash'],
                groups=record.attrs['groups'],
                users=users,
            ))

        return ApiResponse(result)
