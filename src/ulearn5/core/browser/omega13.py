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
from repoze.catalog.query import Eq
from repoze.catalog.query import Or
from repoze.catalog.query import And
from souper.soup import get_soup


class Omega13UserSearch(BrowserView):

    def __call__(self, result_threshold=100):
        query = self.request.form.get('q', '')
        last_query = self.request.form.get('last_query', '')
        last_query_count = self.request.form.get('last_query_count', 0)
        if query:
            portal = api.portal.get()
            self.request.response.setHeader('Content-type', 'application/json')
            soup = get_soup('user_properties', portal)
            searching_surname = len(re.match(r'^[^\ \.]+(?: |\.)*(.*?)$', query).groups()[0])

            # En Python 3, las cadenas son Unicode por defecto
            # if isinstance(query, str):
            #     query = query.decode('utf-8')

            # normalized_query = unicodedata.normalize('NFKD', query).encode('ascii', errors='ignore')
            normalized_query = unicodedata.normalize('NFKD', query).encode('ascii', errors='ignore').decode('ascii')
            normalized_query = normalized_query.replace('.', ' ') + '*'

            def user_entry(record):
                username = record.attrs.get('username')
                fullname = record.attrs.get('fullname')
                return dict(
                    id=username,
                    displayName=fullname if fullname else username
                )

            def searchable_text():
                return soup.query(Eq('searchable_text', normalized_query))

            def not_legit_users():
                return soup.query(And(
                    Or(
                        Eq('username', normalized_query),
                        Eq('fullname', normalized_query)
                    ),
                    Eq('notlegit', True)
                ))

            users_in_soup = [user_entry(r) for r in searchable_text()] + \
                            [user_entry(r) for r in not_legit_users()]

            too_much_results = len(users_in_soup) > result_threshold

            is_useless_request = query.startswith(last_query) and len(users_in_soup) == int(last_query_count)

            if is_useless_request and (not too_much_results or searching_surname):
                current_user = api.user.get_current()
                oauth_token = current_user.getProperty('oauth_token', '')

                maxclient, settings = getUtility(IMAXClient)()
                maxclient.setActor(current_user.getId())
                maxclient.setToken(oauth_token)

                max_users = maxclient.people.get(qs={'limit': 0, 'username': query})
                users_in_max = [dict(id=user.get('username'), displayName=user.get('displayName')) for user in max_users]

                for user in users_in_max:
                    add_user_to_catalog(user['id'], dict(displayName=user['displayName']), notlegit=True)

                return json.dumps(dict(results=users_in_max,
                                       last_query=query,
                                       last_query_count=len(users_in_max)))
            else:
                return json.dumps(dict(results=users_in_soup,
                                       last_query=query,
                                       last_query_count=len(users_in_soup)))

        else:
            return json.dumps(dict(error='No query found',
                                   last_query='',
                                   last_query_count=0))


class Omega13GroupSearch(BrowserView):

    def __call__(self):
        query = self.request.form.get('q', '')
        if query:
            portal = api.portal.get()
            soup = get_soup('ldap_groups', portal)
            normalized_query = query.replace('.', ' ') + '*'

            results = [dict(id=r.attrs.get('id')) for r in soup.query(Eq('searchable_id', normalized_query))]
            return json.dumps(dict(results=results))
        else:
            return json.dumps(dict(id='No results yet.'))
