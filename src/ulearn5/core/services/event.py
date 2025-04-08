# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from plone import api
from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer
from plone.restapi.services import Service
from ulearn5.core.services import (MethodNotAllowed, ObjectNotFound,
                                   UnknownEndpoint, check_methods,
                                   check_required_params, check_roles)

from ulearn5.core.html_parser import replaceImagePathByURL
from ulearn5.core.html_parser import HTMLParser
from ulearn5.core.html_parser import getCommunityNameFromObj
import pytz


logger = logging.getLogger(__name__)


class Event(Service):
    """
    - Endpoint: @api/events/eventuid
    - Method: GET
        Required params:
            - eventuid (str): UID of the event
        Returns navigation for the required context

    -Method: POST
        Required params:
            - eventid
            - title
            - description
            - body
            - start
            - end

    - Subpaths allowed: NO
    """

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if subpath:
            return UnknownEndpoint(f'Unknown sub-endpoint: {"/".join(subpath)}')

        return self.reply()

    @check_methods(methods=['GET', 'POST'])
    def reply(self):
        method = self.request.get('method')
        if method == 'GET':
            return self.reply_get()
        elif method == 'POST':
            return self.reply_post()
        raise MethodNotAllowed(f"Unknown method: {method}")

    @check_roles(roles=['Member', 'Manager', 'Api'])
    @check_required_params(params=['eventuid'])
    def reply_get(self):
        brain = self.get_brain({'UID': self.request.form.get('eventuid')})
        results = []
        if brain:
            community_name = getCommunityNameFromObj(self.context, brain)
            text = self.manage_event_text(brain)

            results.append({
                'attendees': brain.attendees,
                'community': community_name,
                'contact_email': brain.contact_email,
                'contact_name': brain.contact_name,
                'contact_phone': brain.contact_phone,
                'description': brain.description,
                'start': brain.start.strftime('%Y-%m-%dT%H:%M:%S') if brain.end else None,
                'end': brain.end.strftime('%Y-%m-%dT%H:%M:%S') if brain.end else None,
                'event_url': brain.event_url,
                'id': brain.id,
                'location': brain.location,
                'open_end': brain.open_end,
                'portal_type': brain.portal_type,
                'text': text,
                'timezone': brain.timezone,
                'title': brain.title,
                'whole_day': brain.whole_day
            })
        else:
            raise ObjectNotFound(f"Event item with uid {self.request.form.get('eventuid', None)} not found.")
        return {"data": results, "code": 200}

    @check_roles(roles=['Manager', 'Api'])
    @check_required_params(params=['eventid', 'title', 'description', 'body', 'start', 'end'])
    def reply_post(self):
        response = self.create_event()
        return {"data": response, "code": 201}

    def get_brain(self, params):
        content = api.content.get(**params)
        return content

    def manage_event_text(self, brain):
        text = None
        if brain.text:
            text = replaceImagePathByURL(brain.text.raw)
            text = HTMLParser(text)

        return text

    def create_event(self):
        start = self.parse_datetime(self.request.form.get('start'))
        end = self.parse_datetime(self.request.form.get('end'))
        event_id = self.request.form.get('eventid')
        title = self.request.form.get('title')
        body = self.request.form.get('body')
        description = self.request.form.get('description')
        community_id = self.request.form.get('community')
        pc = api.portal.get_tool('portal_catalog')
        if community_id:
            community = pc.unrestrictedSearchResults(portal_type='ulearn.community', id=community_id)
            events_url = community[0].getObject()['events']
        else:
            portal_url = api.portal.get()
            events_url = portal_url['events']

        brains = pc.unrestrictedSearchResults(portal_type='Event', id=event_id)

        if not brains:
            new_event = createContentInContainer(
                events_url,
                'Event',
                title=title,
                id=event_id,
                start=start,
                end=end,
                timezone="Europe/Madrid",
                checkConstraints=False,
                description=description,
                text=RichTextValue(body)
            )
            new_event.reindexObject()
            return f'Event {event_id} created'

        event = brains[0].getObject()
        event.title = title
        event.text = RichTextValue(body)
        event.reindexObject()
        return f'Event {event_id} updated'

    def parse_datetime(self, datetime_str):
        try:
            # Si es un timestamp, conviértelo a datetime
            if datetime_str.isdigit():
                return datetime.fromtimestamp(float(datetime_str), pytz.timezone("Europe/Madrid"))
            # Si es una fecha en formato '%d/%m/%Y/%H:%M', conviértela
            return datetime.strptime(datetime_str, '%d/%m/%Y/%H:%M').replace(tzinfo=pytz.timezone("Europe/Madrid"))
        except (ValueError, TypeError, AttributeError):
            return None
