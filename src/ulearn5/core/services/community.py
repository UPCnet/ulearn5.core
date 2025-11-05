# -*- coding: utf-8 -*-
import logging
from mrs5.max.utilities import IMAXClient
from hashlib import sha1
from mimetypes import MimeTypes

import requests
from plone import api
from plone.namedfile.file import NamedBlobImage
from plone.restapi.services import Service
from ulearn5.core.services import MethodNotAllowed, check_methods, check_roles
from ulearn5.core.services.documents import Documents
from ulearn5.core.services.search import Search
from ulearn5.core.services.subscriptions import Subscriptions
from ulearn5.core.services.utils import lookup_community
from zope.component import getUtility
from urllib.parse import parse_qs

logger = logging.getLogger(__name__)


class Community(Service):
    """
    - Endpoint: @api/communities/{community}

    - Method: GET
        Returns the community information.

    - Method: PUT
        Updates the community.

    - Method: DELETE
        Deletes the community.

    - Subpaths allowed: YES
    """

    PATH_DICT = {
        "subscriptions": Subscriptions,
        "documents": Documents,
        "search": Search,
    }

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request
        self.obj = kwargs.get('obj', None) # The community object

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if not subpath:
            return self.reply()

        next_segment = subpath[0]
        handler_class = self.PATH_DICT.get(next_segment)

        if handler_class:
            kwargs = {'obj': self.obj}

            handler = handler_class(self.context, self.request, **kwargs)
            return handler.handle_subpath(subpath[1:])

        return {"error": f"Unknown sub-endpoint: {'/'.join(subpath)}"}

    @check_methods(methods=['GET', 'PUT', 'DELETE'])
    def reply(self):
        method = self.request.get('method')
        if method == 'GET':
            return self.reply_get()
        elif method == 'PUT':
            return self.reply_put()
        elif method == 'DELETE':
            return self.reply_delete()
        raise MethodNotAllowed(f"Unknown method: {method}")


    """ GET """
    @check_roles(roles=['Member', 'Manager', 'Api'])
    def reply_get(self):
        pc = api.portal.get_tool('portal_catalog')
        communities = pc.unrestrictedSearchResults(
            portal_type='ulearn.community', id=self.obj.id)
        username = api.user.get_current().id
        communities_subscriptions = self.get_communities_subscriptions(username)

        result = []
        community = self.build_community_info(self.obj, communities, communities_subscriptions)
        result.append(community)

        return result

    def get_communities_subscriptions(self, username):
        maxclient, settings = getUtility(IMAXClient)()
        maxclient.setActor(settings.max_restricted_username)
        maxclient.setToken(settings.max_restricted_token)
        return maxclient.people[username].subscriptions.get()

    def build_community_info(self, obj, communities, communities_subscriptions):
        """ Build the community information """
        for brain in communities:
            can_write = False
            user_permission = [
                i for i in communities_subscriptions
                if i['hash'] == brain.community_hash]
            if user_permission != [] and 'write' in user_permission[0]['permissions']:
                can_write = True

            brainObj = self.context.unrestrictedTraverse(brain.getPath())
            return dict(id=brain.id,
                        can_write=can_write,
                        title=brain.Title,
                        description=brain.Description,
                        url=brain.getURL(),
                        gwuuid=brain.gwuuid,
                        hash=sha1(brain.getURL().encode('utf-8')).hexdigest(),
                        type=brain.community_type,
                        show_events_tab=brainObj.show_events,
                        show_news_tab=brainObj.show_news)


    """ PUT """
    @check_roles(roles=['Owner', 'Manager', 'Api'])
    def reply_put(self):
        """ Updates the community """
        params = self.build_params()

        if params['community_type']:
            # We are changing the type of the community
            # Check if it's a legit change
            if params['community_type'] in ['Open', 'Closed', 'Organizative']:
                adapter = self.target.adapted(name=params['community_type'])
            else:
                return {"error": "Bad request, wrong community type", "code": 400}

            if params['community_type'] == self.target.community_type:
                return {"error": "Bad request, already that community type", "code": 400}

            # Everything is ok, proceed
            adapter.update_community_type()

        community = self.obj
        modified = self.update_community(community, params)
        if modified:
            success_response = 'Updated community "{}"'.format(
                self.obj.absolute_url())
        else:
            success_response = 'Error with change values "{}".'.format(
                self.obj.absolute_url())

        logger.info(success_response)
        return {"message": success_response, "code": 200}

    def build_params(self):
        query_params = parse_qs(self.request.QUERY_STRING)
        params = {}
        params['title'] = query_params.get('title', [None])[0]
        params['community_type'] = query_params.get('community_type', [None])[0]
        params['description'] = query_params.get('description', [None])[0]
        params['image'] = query_params.get('image', [None])[0]
        params['activity_view'] = query_params.get('activity_view', [None])[0]
        params['tab_view'] = query_params.get('tab_view', [None])[0]
        params['twitter_hashtag'] = query_params.get('twitter_hashtag', [None])[0]
        params['notify_activity_via_push'] = query_params.get(
            'notify_activity_via_push', [None])[0]
        params['notify_activity_via_push_comments_too'] = query_params.get(
            'notify_activity_via_push_comments_too', [None])[0]

        return params

    def update_community(self, community, properties):
        property_map = {
            'title': 'title',
            'description': 'description',
            'activity_view': 'activity_view',
            'tab_view': 'tab_view',
            'twitter_hashtag': 'twitter_hashtag',
            'notify_activity_via_push': lambda x: True if x == 'True' else None,
            'notify_activity_via_push_comments_too': lambda x: True if x == 'True' else None
        }

        if community:
            for prop, attr in property_map.items():
                if properties.get(prop) is not None:
                    value = properties[prop]
                    if callable(attr):
                        value = attr(value)
                        attr = prop
                    setattr(community, attr, value)

            if properties.get('image'):
                community.image = self.build_image_object(properties['image'])

            community.reindexObject()
            return True

        return False

    def build_image_object(self, image):
        mime = MimeTypes()
        mime_type = mime.guess_type(image)
        imgName = (image.split('/')[-1]).decode('utf-8')
        imgData = requests.get(image).content
        return NamedBlobImage(data=imgData,
                                    filename=imgName,
                                    contentType=mime_type[0])


    """ DELETE """
    @check_roles(roles=['Owner', 'Manager', 'Api'])
    def reply_delete(self):
        community_id = self.obj.id
        community = lookup_community(community_id)
        self.delete_community(community)

        success_response = 'Deleted community "{}"'.format(community_id)
        return {"message": success_response, "code": 204}

    def delete_community(self, community):
            api.content.delete(community)
