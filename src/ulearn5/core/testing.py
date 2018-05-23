# -*- coding: utf-8 -*-
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2

import ulearn5.core

from plone import api
from zope.component import getUtility
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import login
from plone.app.testing import logout

from plone.testing import z2

from zope.configuration import xmlconfig
from zope.interface import alsoProvides

from mrs5.max.utilities import IMAXClient
from mrs5.max.utilities import set_user_oauth_token

from ulearn5.theme.interfaces import IUlearn5ThemeLayer
from ulearn5.core.interfaces import IUlearn5CoreLayer
from plone.dexterity.utils import createContentInContainer

import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()


def setup_max(restricted, password):
    maxclient, settings = getUtility(IMAXClient)()
    token = maxclient.getToken(restricted, password)
    settings.max_restricted_username = restricted
    settings.max_restricted_token = token

    set_user_oauth_token(restricted, token)


def setup_user_max(username, password):
    maxclient, settings = getUtility(IMAXClient)()
    token = maxclient.getToken(username, password)
    api.user.get(username).setMemberProperties(mapping={'oauth_token': token})


# def set_browserlayer(request):
#     """Set the BrowserLayer for the request.

#     We have to set the browserlayer manually, since importing the profile alone
#     doesn't do it in tests.
#     """
#     alsoProvides(request, IUlearn5CoreLayer)


class Ulearn5CoreLayer(PloneSandboxLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE, PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load ZCML
        import ulearn5.core
        xmlconfig.file(
            'configure.zcml',
            ulearn5.core,
            context=configurationContext
        )

        # Needed to make p.a.iterate permissions available as g.core needs them
        import plone.app.iterate.permissions  # noqa

    def setUpPloneSite(self, portal):
        # Needed for PAC not complain about not having one... T_T
        portal.portal_workflow.setDefaultChain("simple_publication_workflow")
        frontpage = createContentInContainer(portal, 'Document', title=u'front-page', checkConstraints=False)
        news = createContentInContainer(portal, 'Folder', title='news', checkConstraints=False)

        applyProfile(portal, 'ulearn5.core:default')

        portal.acl_users.userFolderAddUser('admin', 'secret', ['Manager'], [])
        portal.acl_users.userFolderAddUser('manager', 'secret', ['Manager'], [])
        # portal.acl_users.userFolderAddUser('user', 'secret', ['Member'], [])
        # portal.acl_users.userFolderAddUser('poweruser', 'secret', ['Member', 'WebMaster'], [])
        portal.acl_users.userFolderAddUser('victor.fernandez', 'secret', ['Member'], [])
        portal.acl_users.userFolderAddUser('janet.dura', 'secret', ['Member'], [])
        # portal.acl_users.userFolderAddUser('usuari.iescude', 'secret', ['Member', 'WebMaster'], [])
        portal.acl_users.userFolderAddUser('ulearn.testuser1', 'secret', ['Member', 'WebMaster'], [])
        portal.acl_users.userFolderAddUser('ulearn.testuser2', 'secret', ['Member', ], [])

        api.user.get('ulearn.testuser1').setMemberProperties(mapping={'location': u'Test', 'telefon': u'123456'})
        api.user.get('janet.dura').setMemberProperties(mapping={'fullname': u'Janet Durà', 'location': u'Barcelona', 'telefon': u'654321 123 123'})

        login(portal, 'admin')
        setup_max(u'ulearn.testuser1', '99994183a')
        setup_user_max('ulearn.testuser2', '99994184a')
        portal.portal_workflow.setDefaultChain('genweb_intranet')
        logout()
        # setRoles(portal, TEST_USER_ID, ['Manager'])

ULEARN5_CORE_FIXTURE = Ulearn5CoreLayer()


ULEARN5_CORE_INTEGRATION_TESTING = IntegrationTesting(
    bases=(ULEARN5_CORE_FIXTURE,),
    name='Ulearn5CoreLayer:IntegrationTesting'
)


ULEARN5_CORE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(ULEARN5_CORE_FIXTURE, z2.ZSERVER_FIXTURE),
    name='Ulearn5CoreLayer:FunctionalTesting'
)


ULEARN5_CORE_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        ULEARN5_CORE_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE
    ),
    name='Ulearn5CoreLayer:AcceptanceTesting'
)
