# -*- coding: utf-8 -*-
from plone.dexterity.content import Item
from plone.namedfile.field import NamedBlobImage
from plone.supermodel import model
from Products.Five.browser import BrowserView
from ulearn5.core import _
from zope import schema
from zope.interface import implementer

# grok.templatedir("templates")


class IBanner(model.Schema):

    image = NamedBlobImage(
        title=_('Banner'),
        description=_('If you do not add an image, a default banner will be created using the title.'),
        required=False,
    )

    url = schema.TextLine(
        title=_('Url'),
        description=_('For external links use https:// or http://'),
        required=True
    )

    open_external = schema.Bool(
        title=_('Open in new tab'),
        required=False,
    )

@implementer(IBanner)
class Banner(Item):
    pass


class BannerView(BrowserView):
    pass