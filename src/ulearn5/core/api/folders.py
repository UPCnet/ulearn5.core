# -*- coding: utf-8 -*-
from Products.CMFPlone.interfaces import IPloneSiteRoot

from five import grok
from plone import api

from ulearn5.core.api import ApiResponse
from ulearn5.core.api import REST
from ulearn5.core.api import api_resource
from ulearn5.core.api.root import APIRoot


class Folders(REST):
    """
        /api/folders/
        :param path: object_path_in_documents_folder
    """

    placeholder_type = 'folders'
    placeholder_id = 'folders'

    grok.adapts(APIRoot, IPloneSiteRoot)
    grok.require('base.authenticated')

    @api_resource(required_roles=['Member', 'Manager', 'Api'])
    def GET(self):
        """ Returns navigation for required context. """
        portal = api.portal.get()
        folder_path = '/'.join(portal.getPhysicalPath())
        for k in self.params.keys():
            if k == 'path':
                folder_path = self.params.pop(k, None)
        query = {
            'path': {'query': folder_path, 'depth': 1},
            'review_state': ['private', 'intranet', 'published'],
            'sort_order': 'ascending',
            'sort_on': 'sortable_title',
        }
        brains = api.content.find(**query)
        results = []
        for brain in brains:
            obj = brain.getObject()
            obj_url = brain.getURL()
            internal = True
            type_next_obj = None
            if obj.portal_type == u'Link':
                internal = True if 'resolveuid' in obj.remoteUrl else False
                if internal:
                    uid = obj.remoteUrl.split('/resolveuid/')[1]
                    next_obj = api.content.get(UID=uid.encode('utf-8'))
                    type_next_obj = next_obj.Type()
                    obj_url = next_obj.absolute_url()
                else:
                    obj_url = obj.remoteUrl
            elif obj.portal_type == u'External Content':
                obj_url = obj.absolute_url() + '/@@download/' + obj.filename
            folder = dict(absolute_url=obj_url,
                          description=obj.Description(),
                          id=obj.id,
                          external_url=not internal,
                          path='/'.join(obj.getPhysicalPath()),
                          portal_type=obj.portal_type,
                          state=brain.review_state,
                          title=obj.title,
                          type_when_follow_url=type_next_obj,
                          uid=obj.UID(),
                          )
            results.append(folder)
        return ApiResponse(results)
