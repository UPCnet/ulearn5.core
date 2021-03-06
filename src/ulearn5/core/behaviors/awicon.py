# -*- coding: utf-8 -*-
from zope.interface import alsoProvides
from zope import schema
from plone.directives import form
from zope.interface import implements

from ulearn5.core import _


class IAwIcon(form.Schema):
    """Add icon to object
    """
    form.fieldset(
        'awsome_icon',
        label=_(u'Icon'),
        fields=('awicon',),
    )

    awicon = schema.TextLine(
        title=_(u"Icon"),
        description=_(u"Name of the Font Awesome class to use as an icon. It is only visible in the menu."),
        required=False,
    )

alsoProvides(IAwIcon, form.IFormFieldProvider)


class AwesomeIcon(object):
    implements(IAwIcon)

    def __init__(self, context):
        self.context = context

    def _set_awicon(self, value):
        self.context.awicon = value

    def _get_awicon(self):
        return getattr(self.context, 'awicon', None)

    awicon = property(_get_awicon, _set_awicon)
