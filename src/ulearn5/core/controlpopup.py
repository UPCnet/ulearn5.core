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
from ulearn5.core.utils import getAnnotationNotifyPopup
from ulearn5.core.utils import isBirthdayInProfile

import transaction


def checkActivateBirthday(value):
    if value and not isBirthdayInProfile():
        raise Invalid(_(u'The profile not have birthday field, contact to implement this functionality, uncheck field and save to continue.'))
    return True


class IPopupSettings(model.Schema):

    model.fieldset('Notify',
                   _(u'Notify'),
                   fields=['activate_notify', 'message_notify', 'reload_notify'])

    model.fieldset('Birthday',
                   _(u'Birthday'),
                   fields=['warning_birthday', 'activate_birthday', 'message_birthday'])

    activate_notify = schema.Bool(
        title=_(u"Activate notify"),
        required=True,
        default=False,
    )

    directives.mode(message_notify="display")
    message_notify = schema.Text(
        title=_(u"Message notify"),
        description=_(u"message_notify_description"),
        required=False,
        default=u'',
    )

    directives.mode(reload_notify="display")
    reload_notify = schema.Text(
        title=_(u"Reset notify"),
        description=_(u'To reset the notify access the following <a href=\"@@reset_notify">link</a>.'),
        required=False,
    )

    directives.mode(warning_birthday="display")
    warning_birthday = schema.Text(
        title=_(u"Warning birthday"),
        description=_(u'To activate this functionality you have to request the addition of the birthday field in the profile, it has a cost.'),
        required=False,
    )

    activate_birthday = schema.Bool(
        title=_(u"Activate birthday"),
        required=True,
        default=False,
        constraint=checkActivateBirthday,
    )

    directives.mode(message_birthday="display")
    message_birthday = schema.Text(
        title=_(u"Message birthday"),
        description=_(u"message_birthday_description"),
        required=False,
        default=u'',
    )


class PopupSettingsForm(controlpanel.RegistryEditForm):
    """ Ulearn popup form """

    schema = IPopupSettings
    id = 'PopupSettingsForm'
    label = _(u'Ulearn Popup settings')

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

        aNotify = getAnnotationNotifyPopup()

        aNotify['activate_notify'] = data['activate_notify']
        aNotify['activate_birthday'] = data['activate_birthday']

        transaction.commit()

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        IStatusMessage(self.request).addStatusMessage(_(u'Edit cancelled'), 'info')
        self.request.response.redirect('%s/%s' % (self.context.absolute_url(),
                                                  self.control_panel_view))


class PopupControlPanel(controlpanel.ControlPanelFormWrapper):
    """ Ulearn popup control panel """
    form = PopupSettingsForm
