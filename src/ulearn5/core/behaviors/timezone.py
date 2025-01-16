# -*- coding: utf-8 -*-
from five import grok
from plone import api
from plone.app.contenttypes.interfaces import IEvent
from plone.autoform import directives
from plone.autoform.interfaces import IFormFieldProvider
from plone.directives import form
from plone.indexer import indexer
from plone.namedfile import field as namedfile
from plone.supermodel import model
from zope import schema
from zope.component import adapts
from zope.interface import alsoProvides
from zope.interface import implements
from zope.interface import provider
from plone.app.event.base import default_timezone

from ulearn5.core import _

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


class Timezone(object):
    implements(ITimezone)
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


grok.global_adapter(timezone, name="timezone")
