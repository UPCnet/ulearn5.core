# -*- coding: utf-8 -*-
import re

from plone.dexterity.content import Item
from plone.supermodel import model
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from ulearn5.core import _
from zope import schema
from zope.interface import implementer

YOUTUBE_REGEX = re.compile(r'youtube.*?(?:v=|embed\/)([\w\d-]+)', re.IGNORECASE)


class IVideoEmbed(model.Schema):
    """ The video embed schema """

    video_url = schema.TextLine(
        title=_('video_url'),
        description=_('video_url_description'),
        required=True
    )


@implementer(IVideoEmbed)
class VideoEmbed(Item):
    pass


class VideoEmbedView(BrowserView):
    # grok.context(IVideoEmbed)
    # grok.name('view')

    def __call__(self):
        embed_type, code = self.getEmbed()
        try:
            self.template = ViewPageTemplateFile('videoembed_templates/{}.pt'.format(embed_type))
        except ValueError:
            self.template = ViewPageTemplateFile('videoembed_templates/view.pt')

        return self.template(self, code=code)

    def getVideo(self):
        embed_type, code = self.getEmbed()
        return code

    def getEmbed(self):
        is_youtube_video = YOUTUBE_REGEX.search(self.context.video_url)
        if is_youtube_video:
            return ('youtube', is_youtube_video.groups()[0])

        return (None, None)
