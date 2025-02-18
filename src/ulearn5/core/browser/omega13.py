# -*- coding: utf-8 -*-
import json
import re
import unicodedata
import uuid

from mrs5.max.utilities import IMAXClient
from plone import api
from Products.Five.browser import BrowserView
from ulearn5.core.utils import get_or_initialize_annotation
from zope.component import getUtility


class Omega13UserSearch(BrowserView):

    def __call__(self, result_threshold=100):
        query = self.request.form.get("q", "")
        last_query = self.request.form.get("last_query", "")
        last_query_count = self.request.form.get("last_query_count", 0)

        if query:
            self.request.response.setHeader("Content-type", "application/json")
            user_properties = get_or_initialize_annotation("user_properties")

            searching_surname = len(
                re.match(r"^[^\ \.]+(?: |\.)*(.*?)$", query).groups()[0]
            )

            if isinstance(query, str):
                query = query.decode("utf-8")

            normalized_query = unicodedata.normalize("NFKD", query).encode(
                "ascii", errors="ignore"
            )
            normalized_query = normalized_query.replace(".", " ") + "*"

            def user_entry(record):
                return {
                    "id": record.get("username"),
                    "displayName": record.get("fullname") or record.get("username"),
                }

            def searchable_text():
                return [
                    r for r in user_properties.values() 
                    if r.get("searchable_text") == normalized_query
                ]

            def not_legit_users():
                return [
                    r for r in user_properties.values()
                    if (r.get("username") == normalized_query or r.get("fullname") == normalized_query)
                    and r.get("notlegit") is True
                ]

            users_in_soup = [user_entry(r) for r in searchable_text()] + [
                user_entry(r) for r in not_legit_users()
            ]

            too_much_results = len(users_in_soup) > result_threshold

            is_useless_request = query.startswith(last_query) and len(users_in_soup) == int(last_query_count)

            if is_useless_request and (not too_much_results or searching_surname):
                current_user = api.user.get_current()
                oauth_token = current_user.getProperty("oauth_token", "")

                maxclient, settings = getUtility(IMAXClient)()
                maxclient.setActor(current_user.getId())
                maxclient.setToken(oauth_token)

                max_users = maxclient.people.get(qs={"limit": 0, "username": query})
                users_in_max = [
                    {"id": user.get("username"), "displayName": user.get("displayName")}
                    for user in max_users
                ]

                for user in users_in_max:
                    unique_key = str(uuid.uuid4())
                    user_properties[unique_key] = {
                        "username": user["id"],
                        "fullname": user["displayName"],
                        "notlegit": True,
                    }

                return json.dumps(
                    {
                        "results": users_in_max,
                        "last_query": query,
                        "last_query_count": len(users_in_max),
                    }
                )
            else:
                return json.dumps(
                    {
                        "results": users_in_soup,
                        "last_query": query,
                        "last_query_count": len(users_in_soup),
                    }
                )

        else:
            return json.dumps(
                {"error": "No query found", "last_query": "", "last_query_count": 0}
            )


class Omega13GroupSearch(BrowserView):

    def __call__(self):
        query = self.request.form.get("q", "")
        if query:
            ldap_groups = get_or_initialize_annotation("ldap_groups")
            normalized_query = query.replace(".", " ") + "*"

            results = [
                {"id": r.get("id")}
                for r in ldap_groups.values()
                if r.get("searchable_id") == normalized_query
            ]

            return json.dumps({"results": results})
        else:
            return json.dumps({"id": "No results yet."})

