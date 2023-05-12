# -*- coding: utf-8 -*-
from five import grok
import requests
from Products.CMFPlone.interfaces import IPloneSiteRoot
from ulearn5.core.api import ApiResponse
from ulearn5.core.api import REST
from ulearn5.core.api import api_resource
from ulearn5.core.api.root import APIRoot
from ulearn5.core.utils import replaceImagePathByURL
from plone import api
from base64 import b64encode
import re


class Item(REST):
    """
        /api/item

        http://localhost:8090/Plone/api/item/?url=BITLY_URL

          Return item properties ald fields
          Valid for Document / News Items / Image and maybe all other defautl types...
          If bitly linked object is from other place then returns defaults empty values

    """

    grok.adapts(APIRoot, IPloneSiteRoot)
    grok.require('base.authenticated')

    @api_resource(required=['url'])
    def GET(self):
        """ Expanded bitly links """
        url = self.params['url']
        session = requests.Session()
        resp = session.head(url, allow_redirects=True)
        expanded = resp.url.split('came_from=')[1].replace(
            '%3A', ':') if 'came_from' in resp.url else resp.url

        portal = api.portal.get()
        local_url = portal.absolute_url()
        results = []
        if local_url in expanded:
            item_id = expanded.split(local_url)[1][1:]
            mountpoint_id = self.context.getPhysicalPath()[1]
            if mountpoint_id == self.context.id:
                item_path = '/'.join(api.portal.get().getPhysicalPath()) + '/' + item_id
            else:
                item_path = '/' + mountpoint_id + '/' + api.portal.get().id + '/' + item_id
            if item_path[-5:] == '/view':
                item_path = item_path.replace('/view', '')

            try:
                # Check if value deleted / moved --> NOT FOUND!
                item = api.content.get(path=item_path.encode('utf-8'))
            except:
                item = False

            if item:
                text = image = image_caption = raw_image = raw_file = content_type = type_when_follow_url = ''
                external_url = False
                if item.portal_type == 'News Item':
                    text = replaceImagePathByURL(
                        item.text.raw) if item.text else None
                    image = item.image.filename if item.image else None
                    image_caption = item.image_caption
                    raw_image = b64encode(item.image.data) if item.image.data else None
                elif item.portal_type == 'Image':
                    image = item.image.filename
                    raw_image = b64encode(item.image.data) if item.image.data else None
                    content_type = item.image.contentType
                elif item.portal_type == 'Document':
                    text = replaceImagePathByURL(
                        item.text.raw) if item.text else None
                elif item.portal_type == 'Link':
                    if 'resolveuid' in item.remoteUrl:
                        # Intern
                        uid = item.remoteUrl.encode('utf-8').split('/')[-1]
                        next_obj = api.content.get(UID=uid)
                        text = next_obj.absolute_url()
                        type_when_follow_url = next_obj.Type()
                    else:
                        # Extern
                        text = item.remoteUrl
                        external_url = True
                elif item.portal_type == 'Event':
                    text = replaceImagePathByURL(
                        item.text.raw) if item.text else None
                    external_url = True  # To delete, mantain compatibility with uTalk
                elif item.portal_type == 'File' or item.portal_type == 'ulearn.video':
                    raw_file = b64encode(item.file.data) if item.file.data else None
                    content_type = item.file.contentType
                    external_url = True  # To delete, mantain compatibility with uTalk
                elif item.portal_type == 'ExternalContent':
                    expanded = item.absolute_url() + '/@@download/' + item.filename
                    external_url = True
                    # error = 'Este tipo de documento solo se puede descargar via web'
                    # results.append(dict(error=error))
                    # return ApiResponse(results)

                new = dict(absolute_url=expanded,
                           content_type=content_type,
                           description=item.Description(),
                           external_url=external_url,
                           id=item.id,
                           image=image,
                           image_caption=image_caption,
                           portal_type=item.portal_type,
                           raw_file=raw_file,
                           raw_image=raw_image,
                           title=item.Title(),
                           text=text,
                           type_when_follow_url=type_when_follow_url,
                           uid=item.UID(),  # per accedir al detall de l'event a l'app
                           )
                results.append(new)
        else:
            # Bit.ly object linked is from outside this Community
            # Only reports url
            new = dict(absolute_url=expanded,
                       content_type='',
                       description='',
                       external_url=True,
                       id='',
                       image='',
                       image_caption='',
                       portal_type='',
                       raw_file='',
                       raw_image='',
                       title='',
                       text='',
                       uid='',
                       )
            results.append(new)

        return ApiResponse(results)
