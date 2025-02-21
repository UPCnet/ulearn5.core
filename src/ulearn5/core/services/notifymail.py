# -*- coding: utf-8 -*-
import ast
import logging
from email.header import Header
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

import requests
from plone import api
from plone.restapi.services import Service
from ulearn5.core.services import (MissingParameters, UnknownEndpoint,
                                   check_methods, check_required_params)
from ulearn5.core.services.utils import lookup_community
from zope.component import getUtility

# from mrs5.max.utilities import IMAXClient


logger = logging.getLogger(__name__)


class Notifymail(Service):
    """
    - Endpoint: @api/notifymail
    - Method: POST
        Subscribe a bunch of users to a community

    - Subpaths allowed: NO
    """

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if subpath:
            return UnknownEndpoint(f'Unknown sub-endpoint: {"/".join(subpath)}')

        return self.reply()

    @check_methods(methods=['POST'])
    @check_required_params(params=[
        'community_url',
        'community_name',
        'actor_displayName',
        'activity_content',
        'content_type',
        'thumbURL',
        'filename',
        'objectType'
    ])
    def reply(self):
        """ Subscribe a bunch of users to a community """
        community_url = self.request.form.get('community_url', None)
        if not community_url:
            raise MissingParameters('Community URL not provided')

        community_id = community_url.split('/')[-1]
        community = lookup_community(community_id)

        if not getattr(community, 'notify_activity_via_mail', False):
            return {"message": "Not notifymail", "code": 200}

        if not self.check_notify_email():
            return {"message": "Not notifymail", "code": 200}

        if community.type_notify == "Automatic" and not community.mails_users_community_lists:
            return {"message": "'Not notifymail Automatic by not mails users", "code": 200}

        if community.type_notify == "Manual" and not community.distribution_lists:
            return {"message": "Not notifymail Manual by not mails users", "code": 200}

        mails_users_to_notify = self.get_mails_users_to_notify(community)

        if mails_users_to_notify:
            subject_template, message_template = self.manage_email_template()
            mailhost = api.portal.get_tool(name='MailHost')
            msg = self.build_email_msg(
                subject_template, message_template, mails_users_to_notify)
            mailhost.send(msg)

        success_response = 'OK notifymail'
        logger.info(success_response)
        return {"message": success_response, "code": 200}

    def check_notify_email(self):
        """ Check if there's email notification active """
        types_notify_mail = api.portal.get_registry_record(
            name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.types_notify_mail')
        if self.request.form['content_type'] == 'activity' and 'Activity' in types_notify_mail:
            return True
        elif self.request.form['content_type'] == 'comment' and 'Comment' in types_notify_mail:
            return True

        return False

    def get_mails_users_to_notify(self, community):
        """ Retrieve a list containing the mails of users """
        if community.type_notify == "Manual":
            return community.distribution_lists

        if not community.mails_users_community_lists:
            return None

        if not community.mails_users_community_black_lists:
            community.mails_users_community_black_lists = {}
        elif not isinstance(community.mails_users_community_black_lists, dict):
            community.mails_users_community_black_lists = ast.literal_eval(
                community.mails_users_community_black_lists)

        black_list_mails_users_to_notify = set(
            community.mails_users_community_black_lists.values())

        if isinstance(community.mails_users_community_lists, list):
            list_to_send = [
                email for email in community.mails_users_community_lists
                if email not in black_list_mails_users_to_notify]
        else:
            list_to_send = [
                email
                for email in ast.literal_eval(community.mails_users_community_lists)
                if email not in black_list_mails_users_to_notify]

        return ','.join(list_to_send)

    def build_email_msg(self, subject, message, mails_users_to_notify):
        """ Build email message """
        msg = MIMEMultipart()

        # Handle image (if there's one)
        if self.request.form['objectType'] == 'image':
            msgImage = self.build_image()
            msgImage.add_header('Content-ID', '<image1>')
            msg.attach(msgImage)
            html_activity_content = "<p>" + self.request.form['activity_content'].replace(
                "\n", "<br>") + "</p>" + "<p><img src=cid:image1><br></p>"
        else:
            html_activity_content = "<p>" + \
                self.request.form['activity_content'].replace("\n", "<br>") + "</p>"

        # Templates mapping
        map = {
            'community': self.request.form['community_name'].encode('utf-8'),
            'link': self.request.form['community_url'],
            'title': self.request.form['community_name'].encode('utf-8'),
            'description': html_activity_content,
            'type': '',
            'author': self.request.form['actor_displayName'],
        }
        subject = subject % map
        message = message % map

        # Email building
        msg['From'] = api.portal.get_registry_record(
            'plone.email_from_address')
        msg['Bcc'] = mails_users_to_notify
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = Header(subject, 'utf-8')
        msg.attach(MIMEText(message, 'html', 'utf-8'))

        return msg

    def build_image(self):
        """ Build image object """
        maxclient, settings = getUtility(IMAXClient)()
        maxclient.setActor(
            settings.max_restricted_username)
        maxclient.setToken(settings.max_restricted_token)

        headers = {
            'X-Oauth-Username': settings.max_restricted_username,
            'X-Oauth-Token': settings.max_restricted_token,
            'X-Oauth-Scope': 'widgetcli'}

        image = requests.get(
            maxclient.url + self.request.form['thumbURL'],
            headers=headers, verify=False)

        return MIMEImage(image.content)

    def manage_email_template(self):
        """ Select the corresponding subject / body template """

        TEMPLATES = {
            'ca': {
                'subject': 'Nou contingut %(community)s',
                'message': """\
                T’informem que l'usuari %(author)s ha publicat: <br>
                %(description)s
                <br>
                a la teva comunitat <br><br>
                ✓ <a target="_blank" href="%(link)s">%(title)s</a><br>
                <br>
                Cordialment,<br>
                """
            },
            'es': {
                'subject': 'Nuevo contenido %(community)s ',
                'message': """\
                Te informamos que el usuario %(author)s ha publicado: <br>
                %(description)s
                <br>
                en tu comunidad <br><br>
                ✓ <a target="_blank" href="%(link)s">%(title)s</a><br>
                <br>
                Cordialmente,<br>
                """
            },
            'en': {
                'subject': 'New content %(community)s ',
                'message': """\
                We inform you that the user %(author)s has published: <br>
                %(description)s
                <br>
                in your community <br><br>
                ✓ <a target="_blank" href="%(link)s">%(title)s</a><br>
                <br>
                Cordially,<br>
                """
            }
        }

        subject_template = api.portal.get_registry_record(
            name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.subject_template')
        message_template = api.portal.get_registry_record(
            name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.message_template_activity_comment')
        lang = api.portal.get_default_language()

        if not subject_template:
            subject_template = TEMPLATES[lang]['subject']

        if not message_template:
            message_template = TEMPLATES[lang]['message']

        return subject_template, message_template
