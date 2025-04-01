# -*- coding: utf-8 -*-
import ast
import logging
from hashlib import sha1
from mimetypes import MimeTypes

import requests
from plone import api
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.namedfile.file import NamedBlobImage
from plone.restapi.services import Service
from ulearn5.core.services import (MethodNotAllowed, UnknownEndpoint,
                                   check_methods, check_required_params,
                                   check_roles)
from ulearn5.core.services.community import Community
from ulearn5.core.services.count import Count
from ulearn5.core.services.utils import lookup_community
from zope.component import queryUtility

logger = logging.getLogger(__name__)


class Communities(Service):
    """
    - Endpoint: @api/communities

    - Method: GET
        Returns all the user communities.

    - Method: POST
        Required params:
            - title: (str) Title of the community.
            - community_type: (str) Type of the community.
        Creates a new community.

    - Subpaths allowed: YES
    """

    PATH_DICT = {
        "count": Count,
    }

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if not subpath:
            return self.reply()

        next_segment = subpath[0]
        handler_class = self.PATH_DICT.get(next_segment)

        if handler_class:
            handler = handler_class(self.context, self.request)
            return handler.handle_subpath(subpath[1:])

        # There's a subpath, but there's no handler for it
        # May be a community? -> Delegate to Community
        community = lookup_community(next_segment)
        if community:
            kwargs = {'obj': community}
            community_handler = Community(self.context, self.request, **kwargs)
            return community_handler.handle_subpath(subpath[1:])

        raise UnknownEndpoint(f"Unknown sub-endpoint: {next_segment}")

    @check_methods(methods=['GET', 'POST'])
    def reply(self):
        method = self.request.get('method')
        if method == 'GET':
            return self.reply_get()
        elif method == 'POST':
            return self.reply_post()
        raise MethodNotAllowed(f"Unknown method: {method}")

    @check_roles(roles=['Member', 'Manager', 'Api'])
    def reply_get(self):
        """ Returns all the user communities and the open ones. """

        communities = self.get_communities_by_type()
        username = api.user.get_current().id

        result = []
        favorites = self.get_favorites(username)
        notnotifypush = self.get_notnotifypush(username)

        for brain in communities:
            community = self.build_community_info(
                brain, favorites, notnotifypush)
            result.append(community)

        return result

    def get_communities_by_type(self):
        """ Get all communities """
        pc = api.portal.get_tool('portal_catalog')
        r_results_organizative = pc.searchResults(
            portal_type="ulearn.community", community_type="Organizative",
            sort_on="sortable_title")
        r_results_closed = pc.searchResults(
            portal_type="ulearn.community", community_type="Closed",
            sort_on="sortable_title")
        ur_results_open = pc.unrestrictedSearchResults(
            portal_type="ulearn.community", community_type="Open",
            sort_on="sortable_title")
        communities = r_results_organizative + r_results_closed + ur_results_open

        return communities

    def get_favorites(self, username):
        """ Get the favorites fiven a username """
        pc = api.portal.get_tool('portal_catalog')
        results = pc.unrestrictedSearchResults(favoritedBy=username)
        return [r.id for r in results]

    def get_notnotifypush(self, username):
        """ Get the favorites fiven a username """
        pc = api.portal.get_tool('portal_catalog')
        results = pc.unrestrictedSearchResults(notNotifyPushBy=username)
        return [r.id for r in results]

    def build_community_info(self, brain, favorites, notnotifypush):
        portal_url = api.portal.get().absolute_url()
        self.username = api.user.get_current().id

        if brain.tab_view == 'Documents':
            url = brain.getURL() + '/documents'
        else:
            url = brain.getURL()
        brainObj = self.context.unrestrictedTraverse(brain.getPath())

        if brainObj.mails_users_community_black_lists is None:
            brainObj.mails_users_community_black_lists = {}
        elif not isinstance(brainObj.mails_users_community_black_lists, dict):
            brainObj.mails_users_community_black_lists = ast.literal_eval(
                brainObj.mails_users_community_black_lists)

        return {
            'id': brain.id,
            'title': brain.Title,
            'description': brain.Description,
            'url': brain.getURL(),
            'url_tab_view': url,
            'gwuuid': brain.gwuuid,
            'hash': sha1(brain.getURL().encode('utf-8')).hexdigest(),
            'type': brain.community_type,
            'image': brain.image_filename if brain.image_filename else False,
            'image_community': brain.getURL() + '/thumbnail-image' if brain.image_filename else portal_url + '/++theme++ulearn5/assets/images/avatar_default.png',
            'favorited': brain.id in favorites,
            'activate_notify_push': brainObj.notify_activity_via_push or brainObj.notify_activity_via_push_comments_too,
            'activate_notify_mail': brainObj.notify_activity_via_mail and brainObj.type_notify == 'Automatic',
            'not_notify_push': brain.id in notnotifypush,
            'not_notify_mail': self.username in brainObj.mails_users_community_black_lists,
            'can_manage': self.is_community_manager(brain),
            'show_events_tab': brainObj.show_events,
            'show_news_tab': brainObj.show_news
        }

    def is_community_manager(self, community):
        """ Check if user has role 'Manager' """
        global_roles = api.user.get_roles()
        if 'Manager' in global_roles:
            return True

        gwuuid = community.gwuuid
        catalog = api.portal.get_tool(name='portal_catalog')
        results = catalog.unrestrictedSearchResults({'gwuuid': gwuuid})

        if results:
            community_brain = results[0]
            community_obj = community_brain.getObject()
            acl = getattr(community_obj, 'acl', None)
            if acl:
                return self.username in [
                    a['id'] for a in acl['users']
                    if a['role'] == 'owner']

        return False

    @check_required_params(params=['title', 'community_type'])
    def reply_post(self):
        """ Create a new community """

        # GET PARAMS
        params = self.build_params(self.request.form)

        util = queryUtility(IIDNormalizer)
        id_normalized = util.normalize(params['nom'], max_length=500)

        # SEARCH COMMUNITY
        result = lookup_community(id_normalized)
        if result:
            success_response = 'community already exists.'
            status = 200
            logger.info(success_response)
            return {"message": success_response, "code": status}

        # CREATE IMG OBJECT TO USE AS COMMUNITY IMAGE
        imageObj = ''
        if params['image']:
            imageObj = self.build_image_object(params['image'])

        # ELSE CREATE COMMUNITY
        new_community_id = self.create_community_object(id_normalized, imageObj, params)
        new_community = self.context[new_community_id]

        success_response = 'Created community "{}" with hash "{}".'.format(
            new_community.absolute_url(), sha1(new_community.absolute_url().encode('utf-8')).hexdigest())

        status = 201
        logger.info(success_response)
        return {"message": success_response, "code": status}

    def build_params(self, params):
        """ Build the params """
        params = {}
        params['nom'] = self.request.form.pop('title')
        params['community_type'] = self.request.form.pop('community_type')
        params['description'] = self.request.form.pop('description', None)
        params['image'] = self.request.form.pop('image', None)
        params['activity_view'] = self.request.form.pop('activity_view', None)
        params['tab_view'] = self.request.form.pop('tab_view', None)
        params['twitter_hashtag'] = self.request.form.pop('twitter_hashtag', None)
        params['notify_activity_via_push'] = self.request.form.pop(
            'notify_activity_via_push', None)
        params['notify_activity_via_push_comments_too'] = self.request.form.pop(
            'notify_activity_via_push_comments_too', None)
        return params

    def build_image_object(self, image):
        """ Build the image object """
        mime = MimeTypes()
        mime_type = mime.guess_type(image)
        img_name = (image.split('/')[-1]).decode('utf-8')
        img_data = requests.get(image).content
        return NamedBlobImage(data=img_data,
                              filename=img_name,
                              contentType=mime_type[0])

    def create_community_object(self, id_normalized, imageObj, params):
        """ Create the community object """
        new_community_id = self.context.invokeFactory(
            'ulearn.community', id_normalized, title=params['nom'],
            description=params['description'],
            image=imageObj, community_type=params['community_type'],
            activity_view=params['activity_view'],
            tab_view=params['tab_view'],
            twitter_hashtag=params['twitter_hashtag'],
            notify_activity_via_push=True
            if params['notify_activity_via_push'] == 'True' else None,
            notify_activity_via_push_comments_too=True
            if params['notify_activity_via_push_comments_too'] == 'True' else None,
            checkConstraints=False)
        return new_community_id
