# -*- coding: utf-8 -*-
from five import grok
from plone.dexterity.content import Item
from plone.directives import form
from plone.namedfile.field import NamedBlobImage
from zope import schema
from zope.interface import implements

from ulearn5.core import _

grok.templatedir("templates")


class IBanner(form.Schema):

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


class Banner(Item):
    implements(IBanner)


class BannerView(grok.View):
    grok.context(IBanner)
    grok.name('view')
    grok.template('banner')
