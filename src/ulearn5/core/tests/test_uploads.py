# -*- coding: utf-8 -*-
from zope.component import getUtility
from plone.app.testing import login

from ulearn5.core.tests import uLearnTestBase
from ulearn5.core.testing import ULEARN5_CORE_FUNCTIONAL_TESTING
from ulearn5.core.interfaces import IAppImage
from mrs5.max.utilities import IMAXClient

import requests
import os
import transaction


class TestUploads(uLearnTestBase):

    layer = ULEARN5_CORE_FUNCTIONAL_TESTING

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']

        maxclient, settings = getUtility(IMAXClient)()
        self.username = settings.max_restricted_username
        self.token = settings.max_restricted_token

    def oauth2Header(self, username, token, scope='widgetcli'):
        return {
            'X-Oauth-Token': token,
            'X-Oauth-Username': username,
            'X-Oauth-Scope': scope}

    def test_upload_file_to_community(self):
        login(self.portal, 'ulearn.testuser1')
        community = self.create_test_community()
        transaction.commit()

        avatar_file = open(os.path.join(os.path.dirname(__file__), 'avatar.png'), 'rb')
        files = {'file': ('avatar.png', avatar_file)}

        res = requests.post('{}/{}/upload'.format(self.portal.absolute_url(), community.id), headers=self.oauth2Header(self.username, self.token), files=files)

        transaction.commit()

        self.assertEqual(res.status_code, 201)
        self.assertTrue('thumbURL' in res.json())
        self.assertTrue('uploadURL' in res.json())
        self.assertTrue('avatar.png' in community['documents']['media'].objectIds())
        IAppImage.providedBy(community['documents']['media']['avatar.png'])

    def test_upload_file_to_community_corner_mimetipes(self):
        login(self.portal, 'ulearn.testuser1')
        community = self.create_test_community()
        transaction.commit()

        avatar_file = open(os.path.join(os.path.dirname(__file__), 'avatar.png'), 'rb')
        files = {'file': ('avatar', avatar_file)}

        res = requests.post('{}/{}/upload'.format(self.portal.absolute_url(), community.id), headers=self.oauth2Header(self.username, self.token), files=files)

        transaction.commit()

        self.assertEqual(res.status_code, 201)
        self.assertTrue('avatar' in community['documents'].objectIds())

        avatar_file = open(os.path.join(os.path.dirname(__file__), 'avatar.png'), 'rb')
        files = {'file': ('avatar.pdf', avatar_file)}

        res = requests.post('{}/{}/upload'.format(self.portal.absolute_url(), community.id), headers=self.oauth2Header(self.username, self.token), files=files)

        transaction.commit()

        self.assertEqual(res.status_code, 201)
        self.assertTrue('avatar.pdf' in community['documents'].objectIds())

        avatar_file = open(os.path.join(os.path.dirname(__file__), 'avatar.png'), 'rb')
        files = {'file': ('avatar.odt', avatar_file)}

        res = requests.post('{}/{}/upload'.format(self.portal.absolute_url(), community.id), headers=self.oauth2Header(self.username, self.token), files=files)

        transaction.commit()

        self.assertEqual(res.status_code, 201)
        self.assertTrue('avatar.odt' in community['documents'].objectIds())

    def test_upload_file_to_community_corner_cases(self):
        login(self.portal, 'ulearn.testuser1')
        community = self.create_test_community()
        transaction.commit()

        avatar_file = open(os.path.join(os.path.dirname(__file__), 'avatar.png'), 'rb')
        files = {'file': ('avatar amb espais', avatar_file)}

        res = requests.post('{}/{}/upload'.format(self.portal.absolute_url(), community.id), headers=self.oauth2Header(self.username, self.token), files=files)

        transaction.commit()

        self.assertEqual(res.status_code, 201)
        self.assertTrue('avatar-amb-espais' in community['documents'].objectIds())

    def test_upload_file_to_community_with_parameters(self):
        login(self.portal, 'ulearn.testuser1')
        community = self.create_test_community()
        transaction.commit()

        activity_data = {'activity': 'This is my fancy file'}
        avatar_file = open(os.path.join(os.path.dirname(__file__), 'avatar.png'), 'rb')
        files = {'file': ('avatar.png', avatar_file)}

        res = requests.post('{}/{}/upload'.format(self.portal.absolute_url(), community.id), headers=self.oauth2Header(self.username, self.token), files=files, data=activity_data)

        transaction.commit()

        self.assertEqual(res.status_code, 201)
        self.assertTrue('this-is-my-fancy-file' in community['documents']['media'].objectIds())
        self.assertTrue(community['documents']['media']['this-is-my-fancy-file'].title, activity_data)

    def test_upload_file_to_community_with_parameters_with_strange_chars(self):
        login(self.portal, 'ulearn.testuser1')
        community = self.create_test_community()
        transaction.commit()

        activity_data = {'activity': 'This is my fancy file ç à'}
        avatar_file = open(os.path.join(os.path.dirname(__file__), 'avatar.png'), 'rb')
        files = {'file': ('avatar.png', avatar_file)}

        res = requests.post('{}/{}/upload'.format(self.portal.absolute_url(), community.id), headers=self.oauth2Header(self.username, self.token), files=files, data=activity_data)

        transaction.commit()

        self.assertEqual(res.status_code, 201)
        self.assertTrue('this-is-my-fancy-file-c-a' in community['documents']['media'].objectIds())
        self.assertEqual(community['documents']['media']['this-is-my-fancy-file-c-a'].title, activity_data['activity'])
