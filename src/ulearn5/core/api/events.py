# -*- coding: utf-8 -*-
from Acquisition import aq_inner
import calendar
from datetime import datetime
from five import grok

from plone import api
from plone.app.contenttypes.behaviors.richtext import IRichText
from plone.app.layout.navigation.root import getNavigationRootObject
from plone.app.event.base import localized_now
from plone.dexterity.utils import createContentInContainer
from Products.CMFPlone.interfaces import IPloneSiteRoot
from ulearn5.core.api import ApiResponse
from ulearn5.core.api import REST
from ulearn5.core.api import api_resource
from ulearn5.core.api.root import APIRoot
from ulearn5.core.content.community import ICommunity


def getCommunityNameFromObj(self, value):
    portal_state = self.context.unrestrictedTraverse('@@plone_portal_state')
    root = getNavigationRootObject(self.context, portal_state.portal())
    physical_path = value.getPhysicalPath()
    relative = physical_path[len(root.getPhysicalPath()):]
    for i in range(len(relative)):
        now = relative[:i + 1]
        obj = aq_inner(root.unrestrictedTraverse(now))
        if (ICommunity.providedBy(obj)):
            return obj.title
    return ''

class Events(REST):
    """
        /api/events
        
        :param page
        :param path: community_name
        :param start: start_date(timestamp)
        :param end: end_date(timestamp)
    """

    placeholder_type = 'event'
    placeholder_id = 'eventid'

    grok.adapts(APIRoot, IPloneSiteRoot)
    grok.require('base.authenticated')

    @api_resource(required=[])
    def GET(self):
        portal = api.portal.get()
        results = []
        events_per_page = 10  # Default items per page
        pagination_page = self.params.pop('page', None)
        start = self.params.pop('start', None)
        end = self.params.pop('end', None)
        more_items = False
        total_events = 0
        # TODO: No hemos revisado la recurrencia
        if start and end:
            date_range = {
                'query': (
                    datetime.fromtimestamp(float(start)),
                    datetime.fromtimestamp(float(end)),
                    #datetime(now.year, now.month, 1, 00, 00, 00),
                    #datetime(now.year, now.month, last_day_of_month, 23, 59, 59),
                ),
                'range': 'min:max',
            }
        else:
            date_range = {}
        query = {
            'portal_type': 'Event',
            'review_state': ['intranet', 'published'],
            'sort_on': 'start',
            'sort_order': 'descending',
            'start': date_range
        }
        for k in self.params.keys():
            if k == 'path':
                query[k] = ('/').join(portal.getPhysicalPath()) + '/' + self.params.pop(k, None)
            else:
                query[k] = self.params.pop(k, None)
        
        events = api.content.find(**query)
        total_events = len(events)
        print(query)
        print(total_events)
        if pagination_page:
            # Si page = 0, devolvemos la ?page=1 (que es lo mismo)
            if pagination_page == '0':
                pagination_page = 1
            start = int(events_per_page) * (int(pagination_page) - 1)
            end = int(events_per_page) * int(pagination_page)
            # Devolvemos paginando
            events = events[start:end]
            if end < total_events:
                more_items = True
        else:
            # No paginammos, solo devolvemos 10 primeras => ?page=1
            events = events[0:events_per_page]
            if events_per_page < total_events:
                more_items = True

        for item in events:
            value = item.getObject()
            communityName = getCommunityNameFromObj(self, value)
            
            event = dict(
                title=value.title.encode('utf-8'),
                start=value.start.strftime('%Y-%m-%dT%H:%M:%S'),
                end=value.end.strftime('%Y-%m-%dT%H:%M:%S') if value.end else None,
                community=communityName,
                id=value.id
            )
            results.append(event)
        values = dict(items=results,
                      more_items=more_items,
                      total_events=total_events)
        return ApiResponse(values)


class Event(REST):
    """
        /api/events/{eventid}
    """
    grok.adapts(Events, IPloneSiteRoot)
    grok.require('base.authenticated')

    def __init__(self, context, request):
        super(Event, self).__init__(context, request)
        
    @api_resource(required=['eventid'])
    def GET(self):
        eventid = self.params.pop('eventid')
        portal = api.portal.get()
        local_url = portal.absolute_url()
        results = []
        

    @api_resource(required=['eventid', 'title', 'description', 'body', 'start', 'end'])
    def POST(self):
        eventid = self.params.pop('eventid')
        title = self.params.pop('title')
        desc = self.params.pop('description')
        body = self.params.pop('body')
        date_start = self.params.pop('start')
        date_end = self.params.pop('end')

        response = self.create_event(
            eventid,
            title,
            desc,
            body,
            date_start,
            date_end
        )

        return response

    def create_event(self, eventid, title, desc, body, date_start, date_end):
        date_start = date_start.split('/')
        time_start = date_start[3].split(':')
        date_end = date_end.split('/')
        time_end = date_end[3].split(':')
        portal_url = api.portal.get()
        news_url = portal_url['events']
        pc = api.portal.get_tool('portal_catalog')
        brains = pc.unrestrictedSearchResults(portal_type='Event', id=eventid)
        if not brains:
            new_event = createContentInContainer(news_url,
                                                 'Event',
                                                 title=eventid,
                                                 start=datetime(int(date_start[2]),
                                                                int(date_start[1]),
                                                                int(date_start[0]),
                                                                int(time_start[0]),
                                                                int(time_start[1])
                                                                ),
                                                 end=datetime(int(date_end[2]),
                                                              int(date_end[1]),
                                                              int(date_end[0]),
                                                              int(time_end[0]),
                                                              int(time_end[1])
                                                              ),
                                                 timezone="Europe/Madrid",
                                                 checkConstraints=False)
            new_event.title = title
            new_event.description = desc
            new_event.text = IRichText['text'].fromUnicode(body)
            new_event.reindexObject()
            resp = ApiResponse.from_string('Event {} created'.format(eventid), code=201)
        else:
            event = brains[0].getObject()
            event.title = title
            event.text = IRichText['text'].fromUnicode(body)
            event.reindexObject()
            resp = ApiResponse.from_string('Event {} updated'.format(eventid))

        return resp
