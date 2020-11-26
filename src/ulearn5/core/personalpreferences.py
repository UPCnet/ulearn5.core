# -*- coding: utf-8 -*-
from Products.CMFPlone import PloneMessageFactory as _PMF

from plone import api
from plone.app.users.browser.account import AccountPanelForm
from plone.app.users.browser.account import AccountPanelSchemaAdapter
from zope import schema
from zope.interface import Interface
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

from ulearn5.core import _

format_timepicker = SimpleVocabulary([
    SimpleTerm(value=u'hh:i A', title=_(u'hh:i A')),
    SimpleTerm(value=u'HH:i', title=_(u'HH:i')),
])


class IUlearnPersonalPreferences(Interface):
    language = schema.Choice(
        title=_(u'label_language', default=u'Language'),
        description=_(u'help_language',
                      default=u"Enter your language"),
        required=False,
        vocabulary=u"plone.app.vocabularies.SupportedContentLanguages",
    )

    wysiwyg_editor = schema.Choice(
        title=_PMF(u'label_wysiwyg_editor', default=u'Wysiwyg editor'),
        description=_PMF(
            u'help_wysiwyg_editor',
            default=u'Wysiwyg editor to use.'
        ),
        vocabulary="plone.app.vocabularies.AvailableEditors",
        required=False,
    )

    visible_userprofile_portlet = schema.Bool(
        title=_(u'label_userprofile', default=u'See portlet user profile'),
        description=_(u'help_userprofile', default=u'Show or hide the portlet that shows your profile picture and badges.'),
        required=False,
        default=True,
    )

    timezone = schema.Choice(
        title=_(u'label_event_timezone', default=u'Timezone'),
        description=_(u'help_event_timezone', default=u'Select the Timezone, where this event happens.'),
        required=True,
        vocabulary="plone.app.vocabularies.AvailableTimezones"
    )

    format_time = schema.Choice(
        title=_(u'label_event_format_time', default=u'Format Time'),
        description=_(u'help_event_format_time', default=u'Select the format to display the time in events.'),
        required=False,
        source=format_timepicker,
    )


class UlearnPersonalPreferencesPanelAdapter(AccountPanelSchemaAdapter):
    schema = IUlearnPersonalPreferences


class UlearnPersonalPreferencesPanel(AccountPanelForm):
    """Implementation of personalize form that uses z3c.form."""

    form_name = _PMF(u'legend_personal_details', u'Personal Details')
    schema = IUlearnPersonalPreferences

    @property
    def description(self):
        userid = self.request.form.get('userid')
        mt = api.portal.get_tool(name='portal_membership')
        if userid and (userid != mt.getAuthenticatedMember().getId()):
            # editing someone else's profile
            return _PMF(
                u'description_preferences_form_otheruser',
                default='Personal settings for $name',
                mapping={'name': userid}
            )
        else:
            # editing my own profile
            return _PMF(
                u'description_my_preferences',
                default='Your personal settings.'
            )

    def updateWidgets(self):
        super(UlearnPersonalPreferencesPanel, self).updateWidgets()

        self.widgets['language'].noValueMessage = _PMF(
            u"vocabulary-missing-single-value-for-edit",
            u"Language neutral (site default)"
        )
        self.widgets['wysiwyg_editor'].noValueMessage = _(
            u"vocabulary-available-editor-novalue",
            u"Use site default"
        )

    def __call__(self):
        self.request.set('disable_border', 1)
        return super(UlearnPersonalPreferencesPanel, self).__call__()
