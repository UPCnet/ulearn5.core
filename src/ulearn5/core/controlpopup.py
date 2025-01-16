# -*- coding: utf-8 -*-
from Products.statusmessages.interfaces import IStatusMessage

from plone.app.registry.browser import controlpanel
from plone.autoform import directives
# from plone.registry.interfaces import IRegistry
from plone.supermodel import model
from z3c.form import button
from zope import schema
# from zope.component import queryUtility
from zope.interface import Invalid

from ulearn5.core import _
from ulearn5.core.utils import isBirthdayInProfile


def checkActivateBirthday(value):
    if value and not isBirthdayInProfile():
        raise Invalid(_('The profile not have birthday field, contact to implement this functionality, uncheck field and save to continue.'))
    return True


class IPopupSettings(model.Schema):

    model.fieldset('Notify',
                   _('Notify'),
                   fields=['activate_notify', 'message_notify', 'reload_notify'])

    model.fieldset('Birthday',
                   _('Birthday'),
                   fields=['warning_birthday', 'activate_birthday', 'message_birthday'])

    activate_notify = schema.Bool(
        title=_("Activate notify"),
        required=True,
        default=False,
    )

    directives.mode(message_notify="display")
    message_notify = schema.Text(
        title=_("Message notify"),
        description=_("message_notify_description"),
        required=False,
        default='',
    )

    directives.mode(reload_notify="display")
    reload_notify = schema.Text(
        title=_("Reset notify"),
        description=_('To reset the notify access the following <a href=\"@@reset_notify">link</a>.'),
        required=False,
    )

    directives.mode(warning_birthday="display")
    warning_birthday = schema.Text(
        title=_("Warning birthday"),
        description=_('To activate this functionality you have to request the addition of the birthday field in the profile.'),
        required=False,
    )

    activate_birthday = schema.Bool(
        title=_("Activate birthday"),
        required=True,
        default=False,
        constraint=checkActivateBirthday,
    )

    directives.mode(message_birthday="display")
    message_birthday = schema.Text(
        title=_("Message birthday"),
        description=_("message_birthday_description"),
        required=False,
        default='',
    )


class PopupSettingsForm(controlpanel.RegistryEditForm):
    """ Ulearn popup form """

    schema = IPopupSettings
    id = 'PopupSettingsForm'
    label = _('Ulearn Popup settings')

    def updateFields(self):
        super(PopupSettingsForm, self).updateFields()

    def updateWidgets(self):
        super(PopupSettingsForm, self).updateWidgets()

    @button.buttonAndHandler(_('Save'), name=None)
    def handleSave(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self.applyChanges(data)

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        IStatusMessage(self.request).addStatusMessage(_('Edit cancelled'), 'info')
        self.request.response.redirect('%s/%s' % (self.context.absolute_url(),
                                                  self.control_panel_view))


class PopupControlPanel(controlpanel.ControlPanelFormWrapper):
    """ Ulearn popup control panel """
    form = PopupSettingsForm
