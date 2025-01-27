# -*- coding: utf-8 -*-
from Products.CMFPlone.utils import safe_unicode
from Products.CMFPlone.interfaces import IPloneSiteRoot

from five import grok
from hashlib import sha1
from plone import api
from zope.component import queryUtility
from zope.component import getUtility
from plone.i18n.normalizer.interfaces import IIDNormalizer
from repoze.catalog.query import Eq
from souper.soup import get_soup
from plone.namedfile.file import NamedBlobImage
from mimetypes import MimeTypes

from mrs5.max.utilities import IMAXClient
from ulearn5.core.api import ApiResponse
from ulearn5.core.api import BadParameters
from ulearn5.core.api import REST
from ulearn5.core.api import api_resource
from ulearn5.core.api import logger
from ulearn5.core.api.root import APIRoot
from ulearn5.core.content.community import ICommunityACL
from base5.core.adapters.notnotifypush import INotNotifyPush

from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.MIMEImage import MIMEImage
from email.utils import formatdate

import ast
import requests
from base64 import b64encode


from plone.restapi.services import Service


class CommunityMixin(object):
    pass


class SaveEditACL(Service):
    """
    - Endpoint: /api/saveeditacl
    - Method: GET

    Simulate save on any communities on the Site.
    Used to update the LDAP groups users membership.
    Refresh users removed from LDAP in the soup catalog.
    """

    def reply(self):
        results = []
        communities_ok = []
        communities_error = []
        communities = self.get_communities()

        for item in communities:

            try:
                unrestricted_obj = item._unrestrictedGetObject()
                payload = ICommunityACL(unrestricted_obj).__getattribute__('acl', '')

                logger.info(
                    f'---- Community: {str(unrestricted_obj.absolute_url())} ----')
                logger.info(f'---- Payload: {str(payload)} ----')

                adapter = unrestricted_obj.adapted(request=self.request)
                adapter.update_acl(payload)

                users = payload.get('users', [])
                users_checked = self.check_users(adapter, users)


                obj = item.getObject()
                self.make_adapter_operations(adapter, obj)

                updated = f'Updated community subscriptions on: {str(unrestricted_obj.absolute_url())}'
                logger.info(updated)
                communities_ok.append(dict(url=unrestricted_obj.absolute_url(),
                                           users_checked=users_checked))

            except Exception as e:
                logger.error(
                    f'Error updating community subscriptions on: {unrestricted_obj.absolute_url()}')
                communities_error.append(unrestricted_obj.absolute_url())

        results.append(dict(successfully_updated_communities=communities_ok,
                            error_updating_communities=communities_error))

        return results

    def get_communities(self):
        """ Get all communities """
        pc = api.portal.get_tool('portal_catalog')
        communities = pc.unrestrictedSearchResults(portal_type='ulearn.community')

        return communities
    
    def check_users(self, adapter, users):
        """ Check users and update their roles """
        users_checked = []
        for user in users:

            try:
                adapter.update_acl_atomic(user['id'], user['role'])
                users_checked.append(f'{user["id"]} as role {user["role"]}')
            except Exception as e:
                raise BadParameters(user)
            
        return users_checked
    
    def make_adapter_operations(self, adapter, obj):
        """ Make the adapter operations """
        acl = adapter.get_acl()
        adapter.set_plone_permissions(acl)
        adapter.update_hub_subscriptions()
        if ((obj.notify_activity_via_mail == True) and (obj.type_notify == 'Automatic')):
            adapter.update_mails_users(obj, acl)
        return acl


class CommunitiesGET(Service):
    """
    - Endpoint: /api/communities
    - Method: GET

    Returns a dict containing information about the communities.
    """

    def reply(self):
        """ Returns all the user communities and the open ones. """

        communities = self.get_communities_by_type()

        is_manager = False
        username = api.user.get_current().id
        global_roles = api.user.get_roles()
        if 'Manager' in global_roles:
            is_manager = True

        result = []
        favorites = self.get_favorites(username)
        notnotifypush = self.get_notnotifypush(username)

        for brain in communities:
            community = self.build_community_info(brain, favorites, notnotifypush, is_manager)
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
    
    def is_community_manager(self, community, is_manager):
        # The user has role Manager
        if is_manager:
            return True

        gwuuid = community.gwuuid
        portal = api.portal.get()
        soup = get_soup('communities_acl', portal)

        records = [r for r in soup.query(Eq('gwuuid', gwuuid))]
        if records:
            return self.username in [
                a['id'] for a in records[0].attrs['acl']['users']
                if a['role'] == 'owner']
        
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
    
    def build_community_info(self, brain, favorites, notnotifypush, is_manager):
        portal_url = api.portal.get().absolute_url()

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

        return dict(
            id=brain.id, title=brain.Title, description=brain.Description,
            url=brain.getURL(),
            url_tab_view=url, gwuuid=brain.gwuuid,
            hash=sha1(brain.getURL()).hexdigest(),
            type=brain.community_type, image=brain.image_filename
            if brain.image_filename else False, image_community=brain.getURL() +
            '/thumbnail-image'
            if brain.image_filename else portal_url
            + '/++theme++ulearn5/assets/images/avatar_default.png',
            favorited=brain.id in favorites,
            activate_notify_push=brainObj.
            notify_activity_via_push
            or brainObj.notify_activity_via_push_comments_too,
            activate_notify_mail=brainObj.
            notify_activity_via_mail and brainObj.type_notify == 'Automatic',
            not_notify_push=brain.id in notnotifypush,
            not_notify_mail=self.
            username in brainObj.mails_users_community_black_lists,
            can_manage=self.is_community_manager(brain, is_manager),
            show_events_tab=brainObj.show_events, show_news_tab=brainObj.show_news)
    


class CommunitiesPOST(Service):
    """
    - Endpoint: /api/communities
    - Method: POST

    Create a new community.
    """

    def reply(self):
        """ Create a new community """
    
        # GET PARAMS
        params = self.build_params(self.request.form)

        util = queryUtility(IIDNormalizer)
        id_normalized = util.normalize(params['nom'], max_length=500)

        # SEARCH COMMUNITY
        result = self.does_community_exist(id_normalized)
        if result:
            success_response = 'community already exists.'
            status = 200
            logger.info(success_response)
            return ApiResponse.from_string(success_response, code=status)

        # CREATE IMG OBJECT TO USE AS COMMUNITY IMAGE
        imageObj = ''
        if params['image']:
            imageObj = self.build_image_object(params['image'])

        # ELSE CREATE COMMUNITY
        new_community_id = self.create_community_object(id_normalized, imageObj, params)        
        new_community = self.context[new_community_id]

        success_response = 'Created community "{}" with hash "{}".'.format(
            new_community.absolute_url(), sha1(new_community.absolute_url()).hexdigest())
                
        status = 201
        logger.info(success_response)
        return ApiResponse.from_string(success_response, code=status)
    
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
    
    def does_community_exist(self, id_normalized):
        """ Check if the community exists """
        pc = api.portal.get_tool('portal_catalog')
        result = pc.unrestrictedSearchResults(portal_type='ulearn.community',
                                              id=id_normalized)
        return result
    
    def build_image_object(self, image):
        """ Build the image object """
        mime = MimeTypes()
        mime_type = mime.guess_type(image)
        imgName = (image.split('/')[-1]).decode('utf-8')
        imgData = requests.get(image).content
        return NamedBlobImage(data=imgData,
                              filename=imgName,
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
    

class CommunityGET(Service):
    """
    - Endpoint: /api/communities/{community}
    - Method: GET

    Returns a dict containing information about a community.
    """

    def reply(self):
        """ Returns the information about a community. """
        """ TODO: ADD validate_params """
        communities = self.get_communities()
        username = api.user.get_current().id
        communities_subscriptions = self.get_communities_subscriptions(username)

        result = []
        for brain in communities:
            community = self.build_community_info(brain, communities_subscriptions)
            result.append(community)

        return self.build_community_info(communities)

    
    def validate_params(self):
        """ Validate the parameters """
        """ TODO: Splittear URL y validar aquí el tercer param (community) """
        if 'id' not in self.request.form:
            raise BadParameters('id')
        
    def get_communities(self, community):
        """ Get the community """
        pc = api.portal.get_tool('portal_catalog')
        communities = pc.unrestrictedSearchResults(
            portal_type='ulearn.community', id=community)
        return communities
        
    def get_communities_subscriptions(self, username):
        maxclient, settings = getUtility(IMAXClient)()
        maxclient.setActor(settings.max_restricted_username)
        maxclient.setToken(settings.max_restricted_token)
        return maxclient.people[username].subscriptions.get()
        
    def build_community_info(self, brain, communities_subscriptions):
        """ Build the community information """
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
                            hash=sha1(brain.getURL()).hexdigest(),
                            type=brain.community_type,
                            show_events_tab=brainObj.show_events,
                            show_news_tab=brainObj.show_news)
    


class CommunityPUT(Service):
    """
    - Endpoint: /api/communities/{community}
    - Method: PUT

    Returns a dict containing information about a community.
    """

    def reply(self):
        """ Returns the information about a community. """
        """ TODO: ADD validate_params """
        params = self.build_params()


        """ TODO: Separar esto y ver que hacemos con el decoador @api_response """
        if params['community_type']:
            # We are changing the type of the community
            # Check if it's a legit change
            if params['community_type'] in ['Open', 'Closed', 'Organizative']:
                adapter = self.target.adapted(name=params['community_type'])
            else:
                return ApiResponse.from_string(
                    {"error": "Bad request, wrong community type"},
                    code=400)

            if params['community_type'] == self.target.community_type:
                return ApiResponse.from_string(
                    {"error": "Bad request, already that community type"},
                    code=400)

            # Everything is ok, proceed
            adapter.update_community_type()


        modified = self.update_community(params)
        if modified:
            success_response = 'Updated community "{}"'.format(
                self.target.absolute_url())
        else:
            success_response = 'Error with change values "{}".'.format(
                self.target.absolute_url())

        logger.info(success_response)
        return ApiResponse.from_string(success_response)

    def validate_params(self):
        """ Validate the parameters """
        """ TODO: Splittear URL y validar aquí el tercer param (community) """
        if 'id' not in self.request.form:
            raise BadParameters('id')

    def build_params(self):
        params = {}
        params['title'] = self.request.form.pop('title', None)
        params['community_type'] = self.request.form.pop('community_type', None)
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

    def update_community(self, properties):

        property_map = {
            'title': 'title',
            'description': 'description',
            'activity_view': 'activity_view',
            'tab_view': 'tab_view',
            'twitter_hashtag': 'twitter_hashtag',
            'notify_activity_via_push': lambda x: True if x == 'True' else None,
            'notify_activity_via_push_comments_too': lambda x: True if x == 'True' else None
        }

        brain = self.get_community_brain(properties['community'])
        
        if brain:
            community = brain[0].getObject()
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
        
    def get_community_brain(self, community_id):
        brain = None
        pc = api.portal.get_tool('portal_catalog')
        brain = pc.unrestrictedSearchResults(portal_type='ulearn.community',
                                             community_hash=community_id)
        if not brain:
            brain = pc.unrestrictedSearchResults(portal_type='ulearn.community',
                                                 gwuuid=community_id)
            
        return brain
    
    def build_image_object(self, image):
        mime = MimeTypes()
        mime_type = mime.guess_type(image)
        imgName = (image.split('/')[-1]).decode('utf-8')
        imgData = requests.get(image).content
        return NamedBlobImage(data=imgData,
                                    filename=imgName,
                                    contentType=mime_type[0])
    


class CommunityDELETE(Service):
    """
    - Endpoint: /api/communities/{community}
    - Method: DELETE

    Delete a community.
    """

    def reply(self):
        """ Delete a community """
        """ TODO: Coger el ID del path no del form """
        community_id = self.request.form.pop('id')
        community = self.get_community(community_id)
        self.delete_community(community)

        success_response = 'Deleted community "{}"'.format(community_id)
        code = 204
        return ApiResponse(success_response, code=code)

    
    def get_community(self, community_id):
        """ Get the community """
        pc = api.portal.get_tool('portal_catalog')
        community = pc.unrestrictedSearchResults(portal_type='ulearn.community',
                                                   id=community_id)
        return community

        
    def delete_community(self, community):
        api.content.delete(community)