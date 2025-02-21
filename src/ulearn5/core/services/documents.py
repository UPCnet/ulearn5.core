# -*- coding: utf-8 -*-
import logging

from plone import api
from plone.restapi.services import Service
from ulearn5.core.services import UnknownEndpoint, check_methods, check_roles
from ulearn5.core.services.utils import check_include_cloudfile

logger = logging.getLogger(__name__)


class Documents(Service):
    """
    - Endpoint: @api/communities/{community}/documents
    - Method: GET
        Optional params:
            - community: (str) ID of the community. Can be sent in the url.
            - path: (str) Object path in documents folder
        Returns navigation for the required context

    - Subpaths allowed: NO
    """

    ORDER_BY_TYPE = {"Folder": 1, "Document": 2, "File": 3, "Link": 4, "Image": 5}

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request
        self.obj = kwargs.get('obj', None)

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if subpath:
            return UnknownEndpoint(f'Unknown sub-endpoint: {"/".join(subpath)}')

        return self.reply()

    @check_methods(methods=['GET'])
    @check_roles(roles=['Member', 'Manager', 'Api'])
    def reply(self):
        doc_path = self.construct_doc_path()
        if self.request.form.get('path'):
            doc_path = self.request.form.get('path')

        items_favorites = self.get_favorites(doc_path)
        items_nofavorites = self.exclude_favorites(doc_path)
        items = self.sort_results(items_favorites, items_nofavorites)

        result = [
            self.get_community_from_object(item)
            for item_list in items.values() for item in item_list]
        return {"data": result, "code": 200}

    def construct_doc_path(self):
        portal = api.portal.get()
        community = self.request.form.get('community')
        if community:
            return f"{'/'.join(portal.getPhysicalPath())}/{community}/documents"
        return f"{'/'.join(portal.getPhysicalPath())}/{self.obj.getId()}/documents"

    def get_favorites(self, doc_path):
        """ Return all user favorites """
        current_user = api.user.get_current().id
        brains = self.get_brains(doc_path, {'favoritedBy': current_user})

        return [{'obj': brain, 'tipus': self.ORDER_BY_TYPE.get(brain.portal_type, 6)} for brain in brains]

    def exclude_favorites(self, doc_path):
        """ Return all user non favorites """
        current_user = api.user.get_current().id
        brains = self.get_brains(doc_path)
        no_favorites = []

        for brain in brains:
            if current_user not in brain.favoritedBy or (
                    brain.portal_type == 'CloudFile' and check_include_cloudfile(brain)):
                tipus = self.ORDER_BY_TYPE.get(brain.portal_type, 6)
                no_favorites.append({'obj': brain, 'tipus': tipus})

        return no_favorites

    def sort_results(self, favorites, no_favorites):
        """ Sort results based on their content type """
        favorites_by_tipus = sorted(favorites, key=lambda item: item['tipus'])
        nofavorites_by_tipus = sorted(no_favorites, key=lambda item: item['tipus'])

        return {
            'favorites': favorites_by_tipus,
            'no_favorites': nofavorites_by_tipus
        }

    def get_brains(self, doc_path, **kwargs):
        query = {
            'path': {'query': doc_path, 'depth': 1},
            'review_state': ['intranet', 'published'],
            'sort_order': 'ascending',
            'sort_on': 'sortable_title',
        }

        if kwargs:
            query.update(kwargs)

        return api.content.find(**query)

    def get_community_from_object(self, sortedBrain):
        obj = sortedBrain['obj'].getObject()
        obj_url = sortedBrain['obj'].getURL()

        internal = False
        type_next_obj = None

        if obj.portal_type == 'Link':
            if 'resolveuid' in obj.remoteUrl:
                internal = True
                uid = obj.remoteUrl.split('/resolveuid')[1]
                next_obj = api.content.get(UID=uid)
                type_next_obj = next_obj.Type()
                obj_url = next_obj.absolute_url()
            else:
                obj_url = obj.remoteUrl

        elif obj.portal_type == 'External Content':
            obj_url = obj.absolute_url() + '/@@download/' + obj.filename

        return {
            'asbolute_url': obj_url,
            'descrpition': obj.Description(),
            'id': obj.id,
            'external_url': not internal,
            'internal': internal,
            'path': '/'.join(obj.getPhysicalPath()),
            'portal_type': obj.portal_type,
            'state': obj.review_state,
            'title': obj.Title(),
            'type': obj.portal_type,  # To DELETE
            'type_when_follow_url': type_next_obj,
            'uid': obj.UID(),
            'url': obj_url  # To DELETE
        }
