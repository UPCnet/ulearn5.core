# -*- coding: utf-8 -*-
import logging
from io import StringIO

import requests
from Acquisition import aq_inner
from mrs5.max.utilities import IMAXClient
from plone import api
from plone.restapi.services import Service
from souper.interfaces import ICatalogFactory
from base5.core.patches import changeMemberPortrait
from base5.core.utils import (add_user_to_catalog, get_all_user_properties,
                             remove_user_from_catalog)
from ulearn5.core.services import (Forbidden, MethodNotAllowed, ObjectNotFound,
                                   UnknownEndpoint, check_methods,
                                   check_required_params)
from ulearn5.core.services.all import All
from ulearn5.core.services.user_subscriptions import UserSubscriptions
from ulearn5.core.services.ushare import Ushare
from ulearn5.core.services.utils import lookup_community, lookup_user
from ulearn5.core.services.visualizations import Visualizations
from ulearn5.core.utils import get_or_initialize_annotation
from ulearn5.core.browser.security import execute_under_special_role
from ulearn5.core.gwuuid import IGWUUID
from zope.component import getUtilitiesFor, getUtility
from souper.soup import get_soup
from souper.soup import Record
from repoze.catalog.query import Eq

logger = logging.getLogger(__name__)


class Person(Service):
    """
    - Endpoint: @api/people/{username}
    - Method: GET
        Required params:
            - username (str)
        Returns the user profile values

    - Method: POST
        Required params:
            - username (str)
            - fullname (str)
            - email (str)
            - password (str)
        Creates a user

    - Method: PUT
        Required params:
            - username (str)
        Updates the displayName

    - Method: DELETE
        Deletes a user from the plone & max & communities subscribe

    - Subpaths allowed: YES
    """

    PATH_DICT = {
        "all": All,
        "ushare": Ushare,
        "subscriptions": UserSubscriptions,
        "visualizations": Visualizations
    }

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request
        self.username = kwargs.get('username', None)
        self.username = self.username.lower() if self.username else None

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if not subpath:
            return self.reply()

        next_segment = subpath[0]
        handler_class = self.PATH_DICT.get(next_segment)

        if handler_class:
            kwargs = {'username': self.username}
            handler = handler_class(self.context, self.request, **kwargs)
            return handler.handle_subpath(subpath[1:])

        raise UnknownEndpoint(f"Unknown sub-endpoint: {next_segment}")

    @check_methods(methods=['GET', 'POST', 'PUT', 'DELETE'])
    def reply(self):
        method = self.request.get('method')
        if method == 'GET':
            return self.reply_get()
        elif method == 'POST':
            return self.reply_post()
        elif method == 'PUT':
            return self.reply_put()
        elif method == 'DELETE':
            return self.reply_delete()

        raise MethodNotAllowed(f"Unknown method: {method}")

    def reply_get(self):
        try:
            user = lookup_user(self.username, raisable=True)
            user_properties_utility = getUtility(
                ICatalogFactory, name='user_properties')
            extender_name = api.portal.get_registry_record(
                'base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender')

            rendered_properties = []
            if extender_name in [a[0] for a in getUtilitiesFor(ICatalogFactory)]:
                extended_user_properties_utility = getUtility(
                    ICatalogFactory, name=extender_name)
                rendered_properties = self.extract_properties(
                    extended_user_properties_utility, user)
            else:
                rendered_properties = self.extract_properties(
                    user_properties_utility, user)

            return {"data": rendered_properties, "code": 200}
        except Exception as e:
            return {"error": f'User with ID {id} not found', "code": 404}

    def extract_properties(self, utility, user):
        if '@' in self.username:
            return []

        directory_properties = getattr(utility, 'directory_properties', [])
        public_properties = getattr(utility, 'public_properties', [])
        rendered_properties = []

        for property in directory_properties:
            if public_properties and property not in public_properties:
                continue

            user_prop = user.getProperty(property, '')
            if user_prop:
                check = user.getProperty('check_' + property, '')
                if check is False:
                    continue

                rendered_properties.append({
                    'name': property,
                    'value': user_prop,
                    'icon': getattr(utility, 'directory_icons', {}).get(property, None)
                })

        return rendered_properties

    @check_required_params(params=['fullname', 'email', 'password'])
    def reply_post(self):
        maxclient, settings = getUtility(IMAXClient)()
        maxclient.setActor(settings.max_restricted_username)
        maxclient.setToken(settings.max_restricted_token)
        avatar = self.params.pop('avatar', None)

        user = lookup_user(self.username, raisable=False)
        if user:
            response = self.update_user(user, avatar, maxclient)
            code = 200
        else:
            response = self.create_user(avatar, maxclient)
            code = 201
        return {"message": response, "code": code}

    def create_user(self, avatar, maxclient):
        username = self.username.lower()
        email = self.params.pop('email')
        password = self.params.pop('password', None)

        user_args = dict(
            email=email,
            username=username,
            password=password,
            properties=self.params
        )

        response = api.user.create(**user_args)

        maxclient.people[self.username].put(
            displayName=self.params.get('fullname'))

        if avatar:
            self.manage_avatar(avatar)

        return f'User {self.username} created'

    def update_user(self, user, avatar, maxclient):
        user.setMemberProperties(mapping=self.params)
        maxclient.people[self.username].post()
        maxclient.people[self.username].put(
            displayName=self.params.get('fullname'))

        if avatar:
            self.manage_avatar(avatar)

        return f'User {self.username} updated'

    def manage_avatar(self, avatar):
        portal = api.portal.get()
        membership_tool = api.portal.get_tool(name='portal_membership')
        img_name = (avatar.split('/')[-1]).decode('utf-8')
        try:
            img_data = requests.get(avatar).content
            image = StringIO(img_data)
            image.filename = img_name
            execute_under_special_role(portal,
                                       "Manager",
                                       changeMemberPortrait,
                                       membership_tool,
                                       image,
                                       self.username)
        except Exception:
            raise ObjectNotFound(f'Image data {img_name} not found')

    @check_required_params(params=['username'])
    def reply_put(self):
        try:
            user = lookup_user(self.username, raisable=True)
            maxclient = self.manage_maxclient()
            user.setMemberProperties({'fullname': self.params.get('displayName')})
            properties = get_all_user_properties(user)
            add_user_to_catalog(user, properties, overwrite=True)
            maxclient.people[self.username].put(displayName=properties['fullname'])
            status = maxclient.last_response_code
            return {"message": f'User {self.username} updated', "code": status}
        except Exception as e:
            return {"error": f'User with ID {self.username} not found', "code": 404}

    def reply_delete(self):
        try:
            self.delete_member()
            remove_user_from_catalog(self.username)

            maxclient = self.manage_maxclient()
            communities_subscription = maxclient.people[self.username].subscriptions.get()

            for num, community_subscription in enumerate(communities_subscription):
                community = lookup_community(community_subscription['hash'])
                try:
                    logger.info('Processant {} de {}. Comunitat {}'.format(
                        num, len(communities_subscription), community))
                    gwuuid = IGWUUID(community).get()
                    portal = api.portal.get()
                    soup = get_soup('communities_acl', portal)

                    records = [r for r in soup.query(Eq('gwuuid', gwuuid))]

                    # Save ACL into the communities_acl soup
                    if records:
                        acl_record = records[0]
                        acl = acl_record.attrs['acl']
                        exist = next((user for user in acl.get('users', []) if user['id'] == str(self.username)), None)

                        if exist:
                            acl['users'].remove(exist[0])
                            acl_record.attrs['acl'] = acl
                            soup.reindex(records=[acl_record])
                            adapter = community.adapted()
                            adapter.set_plone_permissions(adapter.get_acl())

                except:
                    continue

            maxclient.people[self.username].delete()
            return {"data": f'Delete user: {self.username}', "code": 204}
        except Exception as e:
            return {"error": f'User with ID {self.username} not found', "code": 404}

    def delete_member(self):
        context = aq_inner(self.context)
        membership_tool = api.portal.get_tool('portal_membership')

        acl_users = getattr(context, 'acl_users')
        member = membership_tool.getMemberById(self.username)
        if not member:
            raise ObjectNotFound(f'User with ID {self.username} not found')
        if not member.canDelete() or ('Manager' in member.getRoles() and not self.is_zope_manager()):
            raise Forbidden(
                f'Insufficient permissions to delete user with ID {self.username}')

        try:
            acl_users.userFolderDelUsers(list(self.username))
        except Exception as e:
            raise NotImplementedError("The underlying user folder doesn't support deleting members")

        self.delete_memberdata()

    def delete_memberdata(self):
        memberdata_tool = api.portal.get_tool('portal_memberdata')
        if memberdata_tool:
            memberdata_tool.deleteMemberData(self.username)

            # Guardamos el username en el soup para borrar el usuario del local roles
            portal = api.portal.get()
            soup_users_delete = get_soup('users_delete_local_roles', portal)
            exist = [r for r in soup_users_delete.query(
                Eq('id_username', self.username))]

            if not exist:
                record = Record()
                record.attrs['id_username'] = self.username
                soup_users_delete.add(record)
                soup_users_delete.reindex()

    def manage_maxclient(self):
        maxclient, settings = getUtility(IMAXClient)()
        maxclient.setActor(settings.max_restricted_username)
        maxclient.setToken(settings.max_restricted_token)

        return maxclient
