# -*- coding: utf-8 -*-
from plone import api
from plone.app.contenttypes.interfaces import IEvent
from plone.autoform.interfaces import IFormFieldProvider
from plone.indexer import indexer
from plone.supermodel import model
from ulearn5.core import _
from zope import schema
from zope.component import adapts
from zope.interface import implementer, provider


def timezone_user_or_default():
    current_user = api.user.get_current()
    if current_user.getProperty('timezone') == '':
        return api.portal.get_registry_record('plone.portal_timezone')
    else:
        return current_user.getProperty('timezone')

@provider(IFormFieldProvider)
class ITimezone(model.Schema):
    """ Add timezone to Events
    """
    timezone = schema.Choice(
        title=_('label_event_timezone', default='Timezone'),
        description=_('help_event_timezone', default='Select the Timezone, where this event happens.'),
        required=True,
        vocabulary="plone.app.vocabularies.AvailableTimezones",
        defaultFactory=timezone_user_or_default,
    )


@implementer(ITimezone)
class Timezone(object):
    adapts(IEvent)

    def __init__(self, context):
        self.context = context

    def _set_timezone(self, value):
        self.context.timezone = value

    def _get_timezone(self):
        return getattr(self.context, 'timezone', None)

    timezone = property(_get_timezone, _set_timezone)


@indexer(IEvent)
def timezone(obj):
    return obj.timezone
