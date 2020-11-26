# -*- coding: utf-8 -*-
from plone.app.event.base import localized_now
from ulearn5.theme.portlets import calendar as portlet_calendar
from ulearn5.core.testing import ULEARN5_CORE_INTEGRATION_TESTING

from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import TEST_USER_ID
from plone.app.testing import setRoles
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletRenderer
from zope.component import getUtility
from zope.component import getMultiAdapter
from zope.component.hooks import setHooks
from zope.component.hooks import setSite
from ulearn5.core.tests import uLearnTestBase
from mrs5.max.utilities import IMAXClient

from datetime import timedelta
from plone.dexterity.utils import createContentInContainer

TZNAME = 'Europe/Vienna'


class RendererTest(uLearnTestBase):
    layer = ULEARN5_CORE_INTEGRATION_TESTING

    def setUp(self):
        portal = self.layer['portal']
        self.portal = portal
        self.request = self.layer['request']
        self.wft = api.portal.get_tool(name='portal_workflow')
        setRoles(portal, TEST_USER_ID, ['Manager'])
        setHooks()
        setSite(portal)

        self.maxclient, settings = getUtility(IMAXClient)()
        self.username = settings.max_restricted_username
        self.token = settings.max_restricted_token

        self.maxclient.setActor(settings.max_restricted_username)
        self.maxclient.setToken(settings.max_restricted_token)
        # Make sure Events use simple_publication_workflow
        # self.portal.portal_workflow.setChainForPortalTypes(
        #     ['Event'], ['simple_publication_workflow']
        # )

    def tearDown(self):
        self.maxclient.contexts['http://nohost/plone/community-test'].delete()

    def create_event(self, context, id='e1', title='New event', days=(1, 1), start=0, end=1, whole_day=False, open_end=False):
        """ Creates an event with delta days tuple (start, end) beggining from
            now. The start and end arguments are also treated as delta hours.
        """
        delta_start = timedelta(hours=start, days=days[0])
        delta_end = timedelta(hours=end, days=days[1])

        start = localized_now() + delta_start
        end = localized_now() + delta_end

        acc = createContentInContainer(
            context, 'Event', id=id, title=title, start=start, end=end, timezone=TZNAME, whole_day=whole_day, open_end=open_end
        )

        # EventAccessor.event_type = 'Event'
        # acc = EventAccessor.create(
        #     container=context,
        #     content_id=id,
        #     title=title,
        #     start=start,
        #     end=end,
        #     timezone=TZNAME,
        #     whole_day=whole_day,
        #     open_end=open_end
        # )
        acc.location = u'Graz, Austria'

        return context[id]

    def renderer(self, context=None, request=None, view=None, manager=None,
                 assignment=None):
        context = context or self.portal
        request = request or self.request
        view = view or context.restrictedTraverse('@@plone')
        manager = manager or getUtility(
            IPortletManager,
            name='plone.rightcolumn',
            context=self.portal
        )
        assignment = assignment or portlet_calendar.Assignment()

        return getMultiAdapter(
            (context, request, view, manager, assignment), IPortletRenderer
        )

    def test_dayname(self):
        login(self.portal, 'ulearn.testuser1')
        portlet = self.renderer(context=self.portal, assignment=portlet_calendar.Assignment())

        portlet.update()
        portlet.render()

        portlet.today()

        # self.assertTrue(near_event)
        # self.assertTrue('e1' in rd)
        logout()
