import time

import requests
from plone import api
from plone.protect.interfaces import IDisableCSRFProtection
from plone.uuid.interfaces import IUUID
from Products.Five import BrowserView
from zope.interface import alsoProvides
from zope.security import checkPermission
from plone.app.contenttypes.behaviors.richtext import IRichText


class API(object):

    def __init__(self):
        self.url = api.portal.get_registry_record('ulearn5.core.controlpanel.IUlearnControlPanelSettings.etherpad_url').rstrip('/')
        self.key = api.portal.get_registry_record('ulearn5.core.controlpanel.IUlearnControlPanelSettings.etherpad_api_key')

    @property
    def valid(self):
        return self.url and self.key

    def __call__(self, method, **kwargs):
        url = self.url + '/api/1/' + method
        kwargs['apikey'] = self.key
        resp = requests.get(url, params=kwargs)
        return resp.json()


class EtherpadView(BrowserView):
    contribute_url = None
    text = None

    def get_iframe_url(self, eapi):
        """
        things to do here:
            1. make sure user is created
            2. create group for pad. One group for every pad
            3. create pad for group
            4. create session for user

            Para revisar lo que tiene creado un usuario en etherpad
            user_obj1 = api.user.get('ulearn.user1')
            user_id_1 = getattr(user_obj1, '_etherpad_id', None)
            pads1 = eapi('listPadsOfAuthor', authorID=user_id_1)
        """       
        user = api.user.get_current()
        user_id = getattr(user, '_etherpad_id', None)
        writing = False
        if user_id is None:
            result = eapi('createAuthorIfNotExistsFor',
                          authorMapper=user.getId(),
                          name=user.getProperty('fullname') or user.getId())
            user._etherpad_id = user_id = result['data']['authorID']
            writing = True

        group_id = getattr(self.context, '_etherpad_group_id', None)
        if group_id is None:
            pad_uid = IUUID(self.context)
            result = eapi('createGroupIfNotExistsFor',
                          groupMapper=pad_uid)

            self.context._etherpad_group_id = group_id = result['data']['groupID']
            writing = True

        pad_id = getattr(self.context, '_etherpad_pad_id', None)
        if pad_id is None:
            result = eapi('createGroupPad',
                          groupID=group_id,
                          padName=self.context.title)

            if result.get('code') == 1 and result['data'] is None:
                result = eapi('listPads',
                              groupID=group_id)
                self.context._etherpad_pad_id = pad_id = result['data']['padIDs'][0]
            else:
                self.context._etherpad_pad_id = pad_id = result['data']['padID']
            writing = True

        if writing:
            alsoProvides(self.request, IDisableCSRFProtection)

        result = eapi('createSession',
                      groupID=group_id,
                      authorID=user_id,
                      validUntil=str(int(time.time() + 24 * 60 * 60)))

        session_id = result['data']['sessionID']
        self.request.response.setCookie(
            'sessionID',
            session_id,
            quoted=False,
            path='/'
        )
        return '%s/p/%s' % (
            eapi.url,
            pad_id
        )

    def get_text(self, eapi):
        pad_id = getattr(self.context, '_etherpad_pad_id', None)
        if pad_id is None:
            return 'No pad found to render'
        result = eapi('getHTML', padID=pad_id)
        if result['code'] == 0:
            return result['data']['html']
        else:
            return 'Pad text can not be found'

    # Comentado se hace en la vista etherpad_searchabletext del cron
    # def get_searchabletext(self, eapi):
    #     pad_id = getattr(self.context, '_etherpad_pad_id', None)
    #     if pad_id is None:
    #         return 'No pad found to render'
    #     result = eapi('getText', padID=pad_id)
    #     if result['code'] == 0:
    #         self.context.text = result['data']['text']
    #         #self.context.textetherpad = IRichText['textetherpad'].fromUnicode(result['data']['text'])
    #         self.context.reindexObject()

    def __call__(self):
        eapi = API()

        if eapi.valid:
            self.valid = True
            #self.get_searchabletext(eapi)
            if checkPermission('cmf.ModifyPortalContent', self.context):
                self.contribute_url = self.get_iframe_url(eapi)
            else:
                self.text = self.get_text(eapi)
        else:
            self.valid = False

        return self.index()
