# -*- coding: utf-8 -*-
from plone.directives import form
from ulearn5.core import _
from zope import schema
from zope.interface import alsoProvides, implementer


class IAwIcon(form.Schema):
    """Add icon to object
    """
    form.fieldset(
        'awsome_icon',
        label=_('Icon'),
        fields=('awicon',),
    )

    awicon = schema.TextLine(
        title=_("Icon"),
        description=_("Name of the Font Awesome class to use as an icon. It is only visible in the menu."),
        required=False,
    )

alsoProvides(IAwIcon, form.IFormFieldProvider)


@implementer(IAwIcon)
class AwesomeIcon(object):

    def __init__(self, context):
        self.context = context

    def _set_awicon(self, value):
        self.context.awicon = value

    def _get_awicon(self):
        return getattr(self.context, 'awicon', None)

    awicon = property(_get_awicon, _set_awicon)
