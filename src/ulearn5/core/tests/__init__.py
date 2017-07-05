import unittest2 as unittest
from plone import api


class uLearnTestBase(unittest.TestCase):

    def create_test_community(self, id='community-test', name=u'community-test', community_type='Closed'):
        """ Creates the community, it assumes the current logged in user """
        if api.user.is_anonymous():
            self.assertTrue(False, msg='Tried to create a community but no user logged in.')

        if 'WebMaster' not in api.user.get_roles():
            self.assertTrue(False, msg='Tried to create a community but the user has not enough permissions to do so.')

        self.portal.invokeFactory('ulearn.community', id,
                                  title=name,
                                  community_type=community_type,)

        return self.portal[id]

    def max_headers(self, username):
        token = api.user.get(username).getProperty('oauth_token')
        return {'X-Oauth-Username': username,
                'X-Oauth-Token': token,
                'X-Oauth-Scope': 'widgetcli'}

    def get_max_context_info(self, community):
        return self.maxclient.contexts[community.absolute_url()].get()
