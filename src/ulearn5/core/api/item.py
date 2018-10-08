# -*- coding: utf-8 -*-
from five import grok
import requests
from Products.CMFPlone.interfaces import IPloneSiteRoot
from ulearn5.core.api import ApiResponse
from ulearn5.core.api import REST
from ulearn5.core.api import api_resource
from ulearn5.core.api.root import APIRoot
from plone import api
from base64 import b64encode


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
        if 'came_from' in resp.url:
            expanded = resp.url.split('came_from=')[1].replace('%3A', ':')
        else:
            expanded = resp.url

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
                item_found = api.content.find(path=item_path)[0]
            except:
                item_found = False

            if item_found:
                value = item_found
                item = value.getObject()
                text = image = image_caption = ''
                raw_image = content_type = ''

                external_url = False
                if value.portal_type == 'News Item':
                    text = item.text.output
                    image_caption = item.image_caption
                    image = item.image.filename
                elif value.portal_type == 'Image':
                    image = item.image.filename
                    raw_image = b64encode(item.image.data),
                    content_type = item.image.contentType
                elif value.portal_type == 'Document':
                    text = item.text.output
                elif value.portal_type == 'Link':
                    text = item.remoteUrl
                    external_url = True
                elif value.portal_type == 'Event':
                    text = item.text.output
                    external_url = True
                elif value.portal_type == 'File':
                    text = ''
                    external_url = True
                else:
                    text = ''
                    external_url = True

                new = dict(title=value.Title,
                           id=value.id,
                           description=value.Description,
                           portal_type=value.portal_type,
                           external_url=external_url,
                           absolute_url=expanded,
                           text=text,
                           item_not_found=False,
                           image_caption=image_caption,
                           image=image,
                           raw_image=raw_image,
                           content_type=content_type
                           )
                results.append(new)
        else:
            # Bit.ly object linked is from outside this Community
            # Only reports url
            value = api.content.find(path=local_url)
            new = dict(title='',
                       id='',
                       description='',
                       portal_type='',
                       external_url=True,
                       absolute_url=expanded,
                       text='',
                       item_not_found=False,
                       image_caption='',
                       image='',
                       raw_image='',
                       content_type=''
                       )
            results.append(new)

        return ApiResponse(results)
