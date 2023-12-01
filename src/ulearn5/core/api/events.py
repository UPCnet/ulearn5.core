# -*- coding: utf-8 -*-
from datetime import datetime
from five import grok

from Products.CMFPlone.interfaces import IPloneSiteRoot

from plone import api
from plone.app.contenttypes.behaviors.richtext import IRichText
from plone.dexterity.utils import createContentInContainer

from ulearn5.core.api import ApiResponse
from ulearn5.core.api import REST
from ulearn5.core.api import api_resource
from ulearn5.core.api import ObjectNotFound
from ulearn5.core.api.root import APIRoot
from ulearn5.core.utils import getCommunityNameFromObj
from ulearn5.core.utils import HTMLParser
from ulearn5.core.utils import replaceImagePathByURL


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
                    # datetime(now.year, now.month, 1, 00, 00, 00),
                    # datetime(now.year, now.month, last_day_of_month, 23, 59, 59),
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
                query[k] = '/'.join(portal.getPhysicalPath()
                                    ) + '/' + self.params.pop(k, None)
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
                community=communityName,
                end=value.end.strftime('%Y-%m-%dT%H:%M:%S') if value.end else None,
                id=value.id,
                open_end=value.open_end,
                portal_type=value.portal_type,
                start=value.start.strftime('%Y-%m-%dT%H:%M:%S'),
                title=value.title.encode('utf-8'),
                uid=item.UID,
                whole_day=value.whole_day
            )
            results.append(event)
        values = dict(items=results,
                      more_items=more_items,
                      total_events=total_events)
        return ApiResponse(values)


class Event(REST):
    """
        /api/events/eventuid?eventuid={uuid}

        :param eventuid: uuid
    """

    placeholder_type = 'event'
    placeholder_id = 'eventuid'

    grok.adapts(Events, IPloneSiteRoot)
    grok.require('base.authenticated')

    @api_resource(required=['eventuid'])
    def GET(self):
        results = []
        eventuid = self.params.pop('eventuid')
        content = api.content.get(UID=eventuid)
        if content:
            communityName = getCommunityNameFromObj(self, content)
            attendees = [a.encode('utf-8') for a in content.attendees]
            if content.text:
                text = replaceImagePathByURL(content.text.raw)
                text = HTMLParser(text)
            else:
                text = None
            event = dict(
                attendees=attendees, community=communityName.encode('utf-8'),
                contact_email=content.contact_email,
                contact_name=content.contact_name.encode('utf-8')
                if content.contact_name else None, contact_phone=content.contact_phone,
                description=content.description.encode('utf-8')
                if content.description else None, end=content.end.strftime(
                    '%Y-%m-%dT%H:%M:%S') if content.end else None,
                event_url=content.event_url, id=content.id, location=content.location,
                open_end=content.open_end, portal_type=content.portal_type,
                start=content.start.strftime('%Y-%m-%dT%H:%M:%S'),
                text=text, timezone=content.timezone, title=content.title.encode(
                    'utf-8'),
                whole_day=content.whole_day)
        else:
            raise ObjectNotFound('Event Item with uid {0} not found'.format(eventuid))
        results.append(event)
        return ApiResponse(results)

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
