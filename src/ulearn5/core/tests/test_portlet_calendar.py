# -*- coding: utf-8 -*-
from plone.app.event.base import localized_now
from Products.CMFCore.utils import getToolByName
from ulearn5.theme.portlets import calendar as portlet_calendar
from ulearn5.core.testing import ULEARN5_CORE_INTEGRATION_TESTING
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
from plone.app.event.dx.behaviors import EventAccessor

TZNAME = 'Europe/Vienna'


class RendererTest(uLearnTestBase):
    layer = ULEARN5_CORE_INTEGRATION_TESTING

    def setUp(self):
        portal = self.layer['portal']
        self.portal = portal
        self.request = self.layer['request']
        self.wft = getToolByName(self.portal, 'portal_workflow')
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

        EventAccessor.event_type = 'Event'
        acc = EventAccessor.create(
            container=context,
            content_id=id,
            title=title,
            start=start,
            end=end,
            timezone=TZNAME,
            whole_day=whole_day,
            open_end=open_end
        )
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

    def test_nearest_event_today_only(self):
        login(self.portal, 'ulearn.testuser1')

        test_community = self.create_test_community()
        self.create_event(test_community['events'], days=(0, 0), start=2, end=3)

        portlet = self.renderer(context=test_community, assignment=portlet_calendar.Assignment())
        portlet.update()
        rd = portlet.render()

        near_event = portlet.get_nearest_today_event()

        self.assertTrue(near_event)
        self.assertTrue('e1' in rd)
        logout()

    def test_nearest_event_today_tomorrow(self):
        login(self.portal, 'ulearn.testuser1')
        test_community = self.create_test_community()
        self.create_event(test_community['events'], start=2, end=3)

        portlet = self.renderer(context=test_community, assignment=portlet_calendar.Assignment())

        portlet.update()
        rd = portlet.render()

        near_event = portlet.get_nearest_today_event()

        self.assertTrue(not near_event)
        self.assertTrue('e1' in rd)
        logout()

    def test_nearest_event_today_two_events(self):
        login(self.portal, 'ulearn.testuser1')
        test_community = self.create_test_community()
        event = self.create_event(test_community['events'], days=(0, 0), start=2, end=3)
        self.create_event(test_community['events'], days=(0, 0), start=4, end=5, id='e2')

        portlet = self.renderer(context=test_community, assignment=portlet_calendar.Assignment())

        portlet.update()
        rd = portlet.render()

        near_event = portlet.get_nearest_today_event()

        self.assertTrue(near_event.id == event.id)
        self.assertTrue('e1' in rd and 'e2' in rd)
        logout()

    def test_next_three_events_today_two_events(self):
        login(self.portal, 'ulearn.testuser1')
        test_community = self.create_test_community()
        self.create_event(test_community['events'], days=(0, 0), start=2, end=3)
        event_must_show = self.create_event(test_community['events'], days=(0, 0), start=4, end=5, id='e2')

        portlet = self.renderer(context=test_community, assignment=portlet_calendar.Assignment())

        portlet.update()
        rd = portlet.render()

        next_three_events = portlet.get_next_three_events()

        self.assertTrue(next_three_events[0].id == event_must_show.id)
        self.assertTrue('e1' in rd and 'e2' in rd)
        logout()

    def test_dayname(self):
        login(self.portal, 'ulearn.testuser1')
        portlet = self.renderer(context=self.portal, assignment=portlet_calendar.Assignment())

        portlet.update()
        portlet.render()

        portlet.today()

        # self.assertTrue(near_event)
        # self.assertTrue('e1' in rd)
        logout()
