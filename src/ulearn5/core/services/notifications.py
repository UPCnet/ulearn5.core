# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from plone import api
from plone.restapi.services import Service
from ulearn5.core.services import (MethodNotAllowed, ObjectNotFound,
                                   UnknownEndpoint, check_methods,
                                   check_required_params)
from ulearn5.core.services.utils import replace_image_path_by_url
from ulearn5.core.utils import get_or_initialize_annotation

logger = logging.getLogger(__name__)


class Notifications(Service):
    """
    - Endpoint: @api/notitifications
    - Method: GET
        Required params:
            - username: (str) The username of the user.
        Returns the notifications of the user.

    - Method: POST
        Required params:
            - username: (str) The username of the user.
        Dismisses the notifications of the user.

    - Subpaths allowed: NO
    """

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request
        self.username = kwargs.get('username', None)

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if subpath:
            return UnknownEndpoint(f'Unknown sub-endpoint: {"/".join(subpath)}')

        return self.reply()

    @check_required_params(params=['username'])
    @check_methods(methods=['GET', 'POST'])
    def reply(self):
        method = self.request.get('method')
        if method == 'GET':
            self.reply_get()
        elif method == 'POST':
            self.reply_post()

        raise MethodNotAllowed(f"Unknown method: {method}")

    def reply_get(self):
        portal = api.portal.get()
        user = self.get_user()
        result = {}

        result['general'] = self.get_general_information_notification(portal, user)
        result['birthday'] = self.get_birthday_information_notification(portal, user)

        return {"data": result, "code": 200}

    def get_user(self):
        user = api.user.get(username=self.request.form.get('username'))
        if not user:
            raise ObjectNotFound(f"User with ID {self.request.form.get('username')} not found")

        return user

    def get_general_information_notification(self, portal, user):
        if not self.check_notify_is_active():
            return {"is_active": False}

        fullname = user.getProperty('fullname', user.id)
        raw_msg = getattr(portal.get('gestion', {}).get(
            'popup', {}).get('notify', {}), 'text', None)

        if raw_msg and hasattr(raw_msg, 'raw'):
            msg = raw_msg.raw.format(fullname=fullname)
            msg = replace_image_path_by_url(msg)
        else:
            msg = ""

        notify_popup = get_or_initialize_annotation('notify_popup')
        user_soup = [record for record in notify_popup.values() if record.get('id') == user.id]

        return {
            "is_active": True,
            "is_dismissed": bool(user_soup),
            "message": msg
        }

    def check_notify_is_active(self):
        return api.portal.get_registry_record(
            'ulearn5.core.controlpopup.IPopupSettings.activate_notify')

    def get_birthday_information_notification(self, portal, user):
        if not self.check_notify_is_active():
            return {"is_active": False}

        current_year, user_year = self.get_years(user)
        fullname = user.getProperty('fullname', user.id)
        years = current_year - user_year

        raw_msg = getattr(portal.get('gestion', {}).get(
            'popup', {}).get('birthday', {}), 'text', None)

        if raw_msg and hasattr(raw_msg, 'raw'):
            msg = raw_msg.raw.format(fullname=fullname, years=years)
            msg = replace_image_path_by_url(msg)
        else:
            msg = ""

        return {
            "is_active": True,
            "is_dismissed": False,
            "message": msg
        }

    def get_years(self, user):
        birthday = user.getProperty('birthday')
        if "/" in birthday:
            birthday = datetime.strptime(birthday, '%d/%m/%Y')
        elif "-" in birthday:
            birthday = datetime.strptime(birthday, '%d-%m-%Y')
        current_year = int(datetime.now().strftime('%Y'))
        user_year = int(birthday.strftime('%Y'))

        return current_year, user_year

    def reply_post(self):
        """Dismiss notification."""
        user = self.get_user()
        notify_popup = get_or_initialize_annotation('notify_popup')

        if user.id not in notify_popup:
            record = {"id": user.id}
            notify_popup[user.id] = record

        return {"success": "Notificació general tancada amb èxit", "code": 200}
