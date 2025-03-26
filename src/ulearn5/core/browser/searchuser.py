# -*- encoding: utf-8 -*-
import unicodedata
from operator import itemgetter

from mrs5.max.utilities import IMAXClient
from plone import api
from Products.CMFPlone.interfaces import IPloneSiteRoot
from souper.interfaces import ICatalogFactory
from ulearn5.core.content.community import ICommunity
from ulearn5.core.utils import get_or_initialize_annotation
from zope.component import getUtilitiesFor, getUtility
from zope.component.hooks import getSite


def searchUsersFunction(context, request, search_string):  # noqa
    portal = getSite()
    current_user = api.user.get_current()
    oauth_token = current_user.getProperty("oauth_token", "")

    maxclient, settings = getUtility(IMAXClient)()
    maxclient.setActor(current_user.getId())
    maxclient.setToken(oauth_token)

    soup = get_soup('user_properties', portal)
    users = []

    if IPloneSiteRoot.providedBy(context):
        if search_string:
            normalized_query = unicodedata.normalize("NFKD", search_string).encode(
                "ascii", errors="ignore"
            ).replace(".", " ") + "*"

            users = [r for r in soup.query(Eq('searchable_text', normalized_query))]
        else:
            too_many_users = api.portal.get_registry_record('plone.many_users')
            if too_many_users:
                users = []
            else:
                # Query for all users in the user_properties, showing only the legit ones
                users = [r for r in soup.query(Eq('notlegit', False))]

    elif ICommunity.providedBy(context):
        maxclientrestricted, settings = getUtility(IMAXClient)()
        maxclientrestricted.setActor(settings.max_restricted_username)
        maxclientrestricted.setToken(settings.max_restricted_token)

        if search_string:
            max_users = maxclientrestricted.contexts[context.absolute_url()].subscriptions.get(
                qs={"username": search_string, "limit": 0}
            )

            normalized_query = unicodedata.normalize("NFKD", search_string).encode(
                "ascii", errors="ignore"
            ).replace(".", " ") + "*"

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

    # solución provisional para que no pete cuando estas en la biblioteca o en cualquier carpeta dentro de una comunidad
    # pendiente decidir cual sera el funcionamiento
    else:
        if search_string:
            normalized_query = unicodedata.normalize("NFKD", search_string).encode(
                "ascii", errors="ignore"
            ).replace(".", " ") + "*"

            users = [r for r in soup.query(Eq('searchable_text', normalized_query))]
        else:
            too_many_users = api.portal.get_registry_record('plone.many_users')
            if too_many_users:
                users = []
            else:
                # Query for all users in the user_properties, showing only the legit ones
                users = [r for r in soup.query(Eq('notlegit', False))]

    has_extended_properties = False
    extender_name = api.portal.get_registry_record(
        "base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender"
    )
    if extender_name in [a[0] for a in getUtilitiesFor(ICatalogFactory)]:
        has_extended_properties = True
        extended_user_properties_utility = getUtility(ICatalogFactory, name=extender_name)

    user_properties_utility = getUtility(ICatalogFactory, name="user_properties")

    users_profile = []
    nonvisibles = api.portal.get_registry_record(
        name="ulearn5.core.controlpanel.IUlearnControlPanelSettings.nonvisibles"
    ) or []

    for user in users:
        if user and user.get("username") != "admin":
            can_view_properties = (
                current_user.id == "admin"
                or "WebMaster" in api.user.get_roles(username=current_user.id, obj=portal)
                or "Manager" in api.user.get_roles(username=current_user.id, obj=portal)
            )

            if user.get("username") in nonvisibles:
                continue

            user_info = api.user.get(user.get("username"))
            if user_info:
                user_dict = {
                    prop: user.get(prop, "")
                    for prop in user_properties_utility.properties
                    if "check_" not in prop and (can_view_properties or user_info.getProperty("check_" + prop, ""))
                }

                if has_extended_properties:
                    user_dict.update({
                        prop: user.get(prop, "")
                        for prop in extended_user_properties_utility.properties
                        if "check_" not in prop and (can_view_properties or user_info.getProperty("check_" + prop, ""))
                    })

                user_dict.update({"id": user.get("username")})
                user_image = (
                    f'<img src="{settings.max_server}/people/{user["username"]}/avatar/large" '
                    f'alt="{user["username"]}" title="{user["username"]}" height="105" width="105">'
                )

                user_dict["foto"] = str(user_image)
                user_dict["url"] = f'{portal.absolute_url()}/profile/{user["username"]}'
                users_profile.append(user_dict)

    users_profile.sort(key=lambda x: x["id"])
    return {"content": users_profile, "length": len(users_profile), "big": False}
