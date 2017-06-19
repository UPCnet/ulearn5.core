# -*- coding: utf-8 -*-
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2

import ulearn5.core


class Ulearn5CoreLayer(PloneSandboxLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        self.loadZCML(package=ulearn5.core)

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'ulearn5.core:default')


ULEARN5_CORE_FIXTURE = Ulearn5CoreLayer()


ULEARN5_CORE_INTEGRATION_TESTING = IntegrationTesting(
    bases=(ULEARN5_CORE_FIXTURE,),
    name='Ulearn5CoreLayer:IntegrationTesting'
)


ULEARN5_CORE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(ULEARN5_CORE_FIXTURE,),
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
