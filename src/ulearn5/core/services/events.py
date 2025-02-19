# -*- coding: utf-8 -*-
import logging
from datetime import datetime

import pytz
from minimal.core.services import UnknownEndpoint, check_methods
from minimal.core.services.event import Event
from plone import api
from plone.restapi.services import Service

#from ulearn5.core.html_parser import getCommunityNameFromObj

logger = logging.getLogger(__name__)


class Events(Service):
    """
    - Endpoint: @api/events
    - Method: GET
        Optional params:
            - page: (str) The page number to retrieve.
            - path: (str) Community name
            - start: (timestamp) The start date of the events to retrieve.
            - end: (timestamp) The end date of the events to retrieve.
        
        Returns a list of events.

    - Subpaths allowed: YES
    """

    PATH_DICT = {
        "eventuid": Event
    }

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request
        self.page = kwargs.get('page', None)
        self.path = kwargs.get('path', None)
        self.start = kwargs.get('start', None)
        self.end = kwargs.get('end', None)
        

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if not subpath:
            return self.reply()

        next_segment = subpath[0]
        handler_class = self.PATH_DICT.get(next_segment)

        if handler_class:
            handler = handler_class(self.context, self.request)
            return handler.handle_subpath(subpath[1:]) 

        raise UnknownEndpoint(f"Unknown sub-endpoint: {next_segment}")

    @check_methods(methods=['GET'])
    def reply(self):
        more_items = False
        total_events = 0
        date_range = self.get_date_range()
        results = []

        events = self.get_brains(date_range, self.request.form)
        total_events= len(events)
        events, more_items = self.paginate_events(events, total_events)

        for event in events:
            obj = event.getObject()
            community_name = getCommunityNameFromObj(self.context, obj)
            results.append({
                'community': community_name,
                'end': obj.end.strftime('%Y-%m-%dT%H:%M:%S') if obj.end else None,
                'id': obj.id,
                'open_end': obj.open_end,
                'portal_type': obj.portal_type,
                'recurrence': obj.recurrence,
                'start': obj.start.strftime('%Y-%m-%dT%H:%M:%S'),
                'title': obj.title.encode('utf-8'),
                'uid': event.UID,
                'whole_day': obj.whole_day
            })
        
        response = {
            'items': results,
            'more_items': more_items,
            'total_events': total_events
        }
        return {"data": response, "code": 200}

    def get_date_range(self):
        if self.start and self.end:
            return {
                'query': (
                    datetime.fromtimestamp(
                        float(self.start)).replace(
                        tzinfo=pytz.timezone("Europe/Madrid")),
                    datetime.fromtimestamp(
                        float(self.end)).replace(
                        tzinfo=pytz.timezone("Europe/Madrid")),
                ),
                'range': 'min:max',
            }
        
        return {}

    def get_brains(self, date_range, params):
        portal = api.portal.get()
        query = {
            'portal_type': 'Event',
            'review_state': ['intranet', 'published'],
            'sort_on': 'start',
            'sort_order': 'descending',
            'start': date_range
        }

        query.update({
            k: '/'.join(portal.getPhysicalPath()) + '/' + params.pop(k, None) if k == 'path' else params.pop(k, None)
            for k in list(params.keys())
        })
        

        return api.content.find(**query)

    def paginate_events(self, events, total_events):
        """ Paginate the events list """
        events_per_page = 10
        more_items = False
        pagination_page = self.request.form.get('page', None)

        if pagination_page:
            if pagination_page == '0':
                pagination_page = 1
            start = events_per_page * (int(pagination_page) - 1)
            end = events_per_page * int(pagination_page)
            events = events[start:end]
            if end < total_events:
                more_items = True
        else:
            events = events[:events_per_page]
            if events_per_page < total_events:
                more_items = True

        return events, more_items
