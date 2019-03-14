# -*- coding: utf-8 -*-
from five import grok
from plone.dexterity.content import Item
from plone.directives import form
from plone.namedfile.field import NamedBlobImage
from zope import schema
from zope.interface import implements

from ulearn5.core import _

grok.templatedir("templates")


class ICommunityTag(form.Schema):

    title = schema.TextLine(
        title=_(u'Title'),
        description=_(u'Name of community tag'),
        required=True
    )

    description = schema.Text(
        title=_(u'Description'),
        description=_(u'Description of community tag.'),
        required=False
    )

    image = NamedBlobImage(
        title=_(u'Image'),
        description=_(u'To obtain a good performance, it is recommended to use an image with a maximum width of 80px.'),
        required=False,
    )

    awicon = schema.TextLine(
        title=u'Font Awesome',
        description=_(u'If you do not assign an image, this value will be used. By default: fa-filter'),
        required=False
    )


class CommunityTag(Item):
    implements(ICommunityTag)


class CommunityTagView(grok.View):
    grok.context(ICommunityTag)
    grok.name('view')
    grok.template('community_tag')

    def awicon(self):
        return self.context.awicon if self.context.awicon else 'fa-filter'
