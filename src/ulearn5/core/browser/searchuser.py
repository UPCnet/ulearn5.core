# -*- encoding: utf-8 -*-
from plone import api
from zope.component.hooks import getSite
from zope.component import getUtility
from zope.component import getUtilitiesFor

from Products.CMFPlone.interfaces import IPloneSiteRoot

from souper.soup import Record
from souper.interfaces import ICatalogFactory
from repoze.catalog.query import Eq
from souper.soup import get_soup

from operator import itemgetter

from mrs5.max.utilities import IMAXClient
from ulearn5.core.content.community import ICommunity

import random
import unicodedata


def searchUsersFunction(context, request, search_string):  # noqa
    portal = getSite()
    # pm = api.portal.get_tool(name='portal_membership')
    nonvisibles = api.portal.get_registry_record(name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.nonvisibles')

    current_user = api.user.get_current()
    oauth_token = current_user.getProperty('oauth_token', '')

    maxclient, settings = getUtility(IMAXClient)()
    maxclient.setActor(current_user.getId())
    maxclient.setToken(oauth_token)

    # plugins = portal.acl_users.plugins.listPlugins(IPropertiesPlugin)
    # # We use the most preferent plugin
    # pplugin = plugins[0][1]
    # users = pplugin.enumerateUsers()

    soup = get_soup('user_properties', portal)
    users = []

    if IPloneSiteRoot.providedBy(context):
        # Search by string (partial) and return a list of Records from the user
        # catalog
        if search_string:
            if isinstance(search_string, str):
                search_string = search_string.decode('utf-8')

            normalized_query = unicodedata.normalize('NFKD', search_string).encode('ascii', errors='ignore')
            normalized_query = normalized_query.replace('.', ' ') + '*'
            users = [r for r in soup.query(Eq('searchable_text', normalized_query))]
        else:
            too_many_users = api.portal.get_registry_record('plone.many_users')
            if too_many_users:
                users = []
            else:
                # Query for all users in the user_properties, showing only the legit ones
                users = [r for r in soup.query(Eq('notlegit', False))]
                if nonvisibles:
                    filtered = []
                    for user in users:
                        if user is not None:
                            if user.attrs['username'] not in nonvisibles:
                                filtered.append(user)
                    users = filtered

    elif ICommunity.providedBy(context):
        if search_string:
            maxclientrestricted, settings = getUtility(IMAXClient)()
            maxclientrestricted.setActor(settings.max_restricted_username)
            maxclientrestricted.setToken(settings.max_restricted_token)
            max_users = maxclientrestricted.contexts[context.absolute_url()].subscriptions.get(qs={'username': search_string, 'limit': 0})

            if isinstance(search_string, str):
                search_string = search_string.decode('utf-8')

            normalized_query = unicodedata.normalize('NFKD', search_string).encode('ascii', errors='ignore')
            normalized_query = normalized_query.replace('.', ' ') + '*'
            plone_results = [r for r in soup.query(Eq('searchable_text', normalized_query))]
            if max_users:
                merged_results = list(set([plone_user.attrs['username'] for plone_user in plone_results]) &
                                      set([max_user['username'] for max_user in max_users]))
                users = []
                for user in merged_results:
                    users.append([r for r in soup.query(Eq('id', user))][0])
            else:
                merged_results = []
                users = []
                for plone_user in plone_results:
                    max_results = maxclientrestricted.contexts[context.absolute_url()].subscriptions.get(qs={'username': plone_user.attrs['username'], 'limit': 0})
                    merged_results_user = list(set([plone_user.attrs['username']]) &
                                               set([max_user['username'] for max_user in max_results]))
                    if merged_results_user != []:
                        merged_results.append(merged_results_user[0])

                if merged_results:
                    for user in merged_results:
                        record = [r for r in soup.query(Eq('id', user))]
                        if record:
                            users.append(record[0])
                        else:
                            # User subscribed, but no local profile found, append empty profile for display
                            pass

        else:
            maxclientrestricted, settings = getUtility(IMAXClient)()
            maxclientrestricted.setActor(settings.max_restricted_username)
            maxclientrestricted.setToken(settings.max_restricted_token)
            max_users = maxclientrestricted.contexts[context.absolute_url()].subscriptions.get(qs={'limit': 0})
            max_users = [user.get('username') for user in max_users]

            users = []
            for user in max_users:
                record = [r for r in soup.query(Eq('id', user))]
                if record:
                    users.append(record[0])
                else:
                    # User subscribed, but no local profile found, append empty profile for display
                    pass

            if nonvisibles:
                filtered = []
                for user in users:
                    if user is not None:
                        if user.attrs['username'] not in nonvisibles:
                            filtered.append(user)
                users = filtered

    # solución provisional para que no pete cuando estas en la biblioteca o en cualquier carpeta dentro de una comunidad
    # pendiente decidir cual sera el funcionamiento
    else:
        if search_string:
            if isinstance(search_string, str):
                search_string = search_string.decode('utf-8')

            normalized_query = unicodedata.normalize('NFKD', search_string).encode('ascii', errors='ignore')
            normalized_query = normalized_query.replace('.', ' ') + '*'
            users = [r for r in soup.query(Eq('searchable_text', normalized_query))]
        else:
            too_many_users = api.portal.get_registry_record('plone.many_users')
            if too_many_users:
                users = []
            else:
                # Query for all users in the user_properties, showing only the legit ones
                users = [r for r in soup.query(Eq('notlegit', False))]
                if nonvisibles:
                    filtered = []
                    for user in users:
                        if user is not None:
                            if user.attrs['username'] not in nonvisibles:
                                filtered.append(user)
                    users = filtered

    has_extended_properties = False
    extender_name = api.portal.get_registry_record('base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender')
    if extender_name in [a[0] for a in getUtilitiesFor(ICatalogFactory)]:
        has_extended_properties = True
        extended_user_properties_utility = getUtility(ICatalogFactory, name=extender_name)

    user_properties_utility = getUtility(ICatalogFactory, name='user_properties')

    users_profile = []
    for user in users:
        if user is not None and user.attrs['username'] != 'admin':
            if current_user.id == 'admin':
                can_view_properties = True
            else:
                roles = api.user.get_roles(username=current_user.id, obj=portal)
                can_view_properties = current_user == user.attrs['username'] or 'WebMaster' in roles or 'Manager' in roles
            if isinstance(user, Record):
                user_dict = {}
                user_info = api.user.get(user.attrs['username'])
                for user_property in user_properties_utility.properties:
                    if 'check_' not in user_property:
                        check = user_info.getProperty('check_' + user_property, '')
                        if can_view_properties or check == '' or check:
                            user_dict.update({user_property: user.attrs.get(user_property, '')})

                if has_extended_properties:
                    for user_property in extended_user_properties_utility.properties:
                        if 'check_' not in user_property:
                            check = user_info.getProperty('check_' + user_property, '')
                            if can_view_properties or check == '' or check:
                                user_dict.update({user_property: user.attrs.get(user_property, '')})

                user_dict.update(dict(id=user.attrs['username']))
                userImage = '<img src="' + settings.max_server + '/people/' + user.attrs['username'] + '/avatar/large" alt="' + user.attrs['username'] + '" title="' + user.attrs['username'] + '" height="105" width="105" >'
                # userImage = pm.getPersonalPortrait(user.attrs['username'])
                # userImage.alt = user.attrs['username']
                # userImage.title = user.attrs['username']
                # userImage.height = 105
                # userImage.width = 105

                user_dict.update(dict(foto=str(userImage)))
                user_dict.update(dict(url=portal.absolute_url() + '/profile/' + user.attrs['username']))
                users_profile.append(user_dict)

            else:
                # User is NOT an standard Plone user!! is a dict provided by the patched enumerateUsers
                user_dict = {}
                for user_property in user_properties_utility.properties:
                    user_dict.update({user_property: user.get(user_property, '')})

                if has_extended_properties:
                    for user_property in extended_user_properties_utility.properties:
                        user_dict.update({user_property: user.get(user_property, '')})

                user_dict.update(dict(id=user.get('id', '')))
                userImage = '<img src="' + settings.max_server + '/people/' + user.attrs['username'] + '/avatar/large" alt="' + user.attrs['username'] + '" title="' + user.attrs['username'] + '" height="105" width="105" >'
                # userImage = pm.getPersonalPortrait(user.attrs['username'])
                # userImage.alt = user.attrs['username']
                # userImage.title = user.attrs['username']
                # userImage.height = 105
                # userImage.width = 105

                user_dict.update(dict(foto=str(userImage)))
                user_dict.update(dict(url=portal.absolute_url() + '/profile/' + user.get('id', '')))
                users_profile.append(user_dict)

    len_usuaris = len(users_profile)
    if len_usuaris > 100:
        escollits = random.sample(range(len(users_profile)), 100)
        llista = []
        for escollit in escollits:
            llista.append(users_profile[escollit])
        return {'content': llista, 'length': len_usuaris, 'big': True}
    else:
        users_profile.sort(key=itemgetter('username'))
        return {'content': users_profile, 'length': len_usuaris, 'big': False}
