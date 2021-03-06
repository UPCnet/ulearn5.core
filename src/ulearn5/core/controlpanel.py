# -*- coding: utf-8 -*-
from Products.statusmessages.interfaces import IStatusMessage

from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow
from plone import api
from plone.app.registry.browser import controlpanel
from plone.directives import dexterity, form
from plone.supermodel import model
from z3c.form import button
from zope import schema
from zope.component import getUtility
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from mrs5.max.utilities import IMAXClient

from ulearn5.core import _
from ulearn5.core.widgets.select2_maxuser_widget import Select2MAXUserInputFieldWidget

import transaction


communityActivityView = SimpleVocabulary(
    [SimpleTerm(value=u'Darreres activitats', title=_(u'Darreres activitats')),
     SimpleTerm(value=u'Activitats mes valorades', title=_(u'Activitats mes valorades')),
     SimpleTerm(value=u'Activitats destacades', title=_(u'Activitats destacades'))]
)

buttonbarView = SimpleVocabulary(
    [SimpleTerm(value=u'stream', title=_(u'Stream')),
     SimpleTerm(value=u'mycommunities', title=_(u'My Communities')),
     SimpleTerm(value=u'news', title=_(u'News')),
     SimpleTerm(value=u'sharedwithme', title=_(u'Shared With Me'))]
)

cronTasksVocabulary = SimpleVocabulary(
    [SimpleTerm(value=u'syncldapgroups', title=_(u'syncldapgroups')),
     SimpleTerm(value=u'rebuild_user_catalog', title=_(u'rebuild_user_catalog')),
     SimpleTerm(value=u'delete_user_catalog', title=_(u'delete_user_catalog')),
     SimpleTerm(value=u'delete_local_roles', title=_(u'delete_local_roles')),
     SimpleTerm(value=u'api/saveeditacl', title=_(u'api/saveeditacl')),
     SimpleTerm(value=u'etherpad_searchabletext', title=_(u'etherpad_searchabletext')),
     SimpleTerm(value=u'rebuild_users_portrait', title=_(u'rebuild_users_portrait')),
     SimpleTerm(value=u'export_users_communities', title=_(u'export_users_communities')),
     ]
)

typesNotifyMailVocabulary = SimpleVocabulary(
    [SimpleTerm(value=u'Document', title=_(u'Document')),
     SimpleTerm(value=u'Link', title=_(u'Link')),
     SimpleTerm(value=u'File', title=_(u'File')),
     SimpleTerm(value=u'Event', title=_(u'Event')),
     SimpleTerm(value=u'News Item', title=_(u'News Item')),
     SimpleTerm(value=u'ExternalContent', title=_(u'ExternalContent')),
     SimpleTerm(value=u'Activity', title=_(u'Activity')),
     SimpleTerm(value=u'Comment', title=_(u'Comment')),
     ]
)


class ILiteralQuickLinks(form.Schema):
    language = schema.Choice(
        title=_(u'Language'),
        required=True,
        vocabulary=u'plone.app.vocabularies.SupportedContentLanguages'
    )
    text = schema.TextLine(title=_(u'Text'), required=False)


class ITableQuickLinks(form.Schema):
    language = schema.Choice(
        title=_(u'Language'),
        required=True,
        vocabulary=u'plone.app.vocabularies.SupportedContentLanguages'
    )
    text = schema.TextLine(title=_(u'Text'), required=False)
    link = schema.TextLine(title=_(u'Link'), required=False)
    icon = schema.TextLine(title=_(u'Font Awesome Icon'), required=False)
    new_window = schema.Bool(title=_(u'New window'), required=False, default=True)


class IUlearnControlPanelSettings(model.Schema):
    """ Global Ulearn settings. This describes records stored in the
    configuration registry and obtainable via plone.registry.
    """

    model.fieldset(
        'General',
        _(u'General'),
        fields=['html_title_ca', 'html_title_es', 'html_title_en', 'language', 'url_forget_password', 'campus_url', 'library_url', 'people_literal',
                'threshold_winwin1', 'threshold_winwin2', 'threshold_winwin3', 'stats_button',
                'info_servei', 'activate_news', 'show_news_in_app', 'activate_sharedwithme',
                'buttonbar_selected', 'cron_tasks', 'url_private_policy', 'url_site'])

    model.fieldset(
        'Design',
        _(u'Design'),
        fields=['main_color', 'secondary_color', 'background_property',
                'background_color',
                'buttons_color_primary', 'buttons_color_secondary',
                'maxui_form_bg',
                'alt_gradient_start_color', 'alt_gradient_end_color',
                'color_community_closed', 'color_community_organizative',
                'color_community_open'])

    model.fieldset('Visibility',
                   _(u'Visibility'),
                   fields=['nonvisibles'])

    model.fieldset('Quick Links',
                   _(u'QuickLinks'),
                   fields=['quicklinks_literal', 'quicklinks_icon', 'quicklinks_table'])

    model.fieldset('Communities',
                   _(u'Communities'),
                   fields=['activity_view', 'show_literals', 'url_terms', 'types_notify_mail', 'subject_template', 'message_template', 'message_template_activity_comment'])

    model.fieldset('Google Analytics',
                   u'Google Analytics',
                   fields=['gAnalytics_enabled', 'gAnalytics_view_ID', 'gAnalytics_JSON_info'])

    model.fieldset('Bitly',
                   u'Bitly',
                   fields=['bitly_username', 'bitly_api_key'])

    html_title_ca = schema.TextLine(
        title=_(u"html_title_ca",
                default=u"Títol del web amb HTML tags (negretes) [CA]"),
        description=_(u"help_html_title",
                      default=u"Afegiu el títol del Ulearn. Podeu incloure tags HTML"),
        required=False,
    )

    html_title_es = schema.TextLine(
        title=_(u"html_title_es",
                default=u"Títol del web amb HTML tags (negretes) [ES]"),
        description=_(u"help_html_title",
                      default=u"Afegiu el títol del Ulearn. Podeu incloure tags HTML"),
        required=False,
    )

    html_title_en = schema.TextLine(
        title=_(u"html_title_en",
                default=u"Títol del web amb HTML tags (negretes) [EN]"),
        description=_(u"help_html_title",
                      default=u"Afegiu el títol del Ulearn. Podeu incloure tags HTML"),
        required=False,
    )

    campus_url = schema.TextLine(
        title=_(u'campus_url',
                default=_(u'URL del campus')),
        description=_(u'help_campus_url',
                      default=_(u'Afegiu la URL del campus associat a aquestes comunitats.')),
        required=False,
        default=u'',
    )

    library_url = schema.TextLine(
        title=_(u'library_url',
                default=_(u'URL de la biblioteca')),
        description=_(u'help_library_url',
                      default=_(u'Afegiu la URL de la biblioteca associada a aquestes comunitats.')),
        required=False,
        default=u'',
    )

    threshold_winwin1 = schema.TextLine(
        title=_(u'llindar_winwin1',
                default=_(u'Llindar del winwin 1')),
        description=_(u'help_llindar_winwin1',
                      default=_(u'Aquest és el llindar del winwin #1.')),
        required=False,
        default=u'50',
    )

    threshold_winwin2 = schema.TextLine(
        title=_(u'llindar_winwin2',
                default=_(u'Llindar del winwin 2')),
        description=_(u'help_llindar_winwin2',
                      default=_(u'Aquest és el llindar del winwin #2.')),
        required=False,
        default=u'100',
    )

    threshold_winwin3 = schema.TextLine(
        title=_(u'llindar_winwin3',
                default=_(u'Llindar del winwin 3')),
        description=_(u'help_llindar_winwin3',
                      default=_(u'Aquest és el llindar del winwin #3.')),
        required=False,
        default=u'500',
    )

    stats_button = schema.Bool(
        title=_(u'stats_button',
                default=_(u"Mostrar botó d'accés a estadístiques diàries")),
        description=_(u'help_stats_button',
                      default=_(u"Mostra o no el botó d'accés a estadístiques diàries a stats/activity i stats/chats")),
        required=False,
        default=False,
    )

    info_servei = schema.TextLine(
        title=_(u'info_servei',
                default=_(u'Informació del servei')),
        description=_(u'help_info_servei',
                      default=_(u'Aquest és l\'enllaç al servei.')),
        required=False,
    )

    activate_news = schema.Bool(
        title=_(u'activate_news',
                default=_(u"Mostra les noticies a les que estic subscrit")),
        description=_(u'help_activate_news',
                      default=_(u"Mostra o no el botó de Noticies a la tile central de les comunitats")),
        required=False,
        default=False,
    )

    activate_sharedwithme = schema.Bool(
        title=_(u'activate_sharedwithme',
                default=_(u"Mostra el que hi ha compartit amb mi")),
        description=_(u'help_activate_sharedwithme',
                      default=_(u"Mostra o no el botó del que hi ha compartit amb mi i el que hi ha compartit a les comunitats")),
        required=False,
        default=False,
    )

    buttonbar_selected = schema.Choice(
        title=_(u'buttonbar_selected'),
        description=_(u'Select the active button in the button bar.'),
        vocabulary=buttonbarView,
        required=True,
        default='stream',
    )

    cron_tasks = schema.List(
        title=_(u"cron_tasks", default=u"Cron tasks"),
        description=_(u'Tasques que s\'executaran per la nit'),
        value_type=schema.Choice(source=cronTasksVocabulary),
        required=False,
    )

    url_private_policy = schema.TextLine(
        title=_(u'url_private_policy',
                default=_(u"Url private policy")),
        description=_(u'help_url_private_policy',
                      default=_(u"Url of the private policy.")),
        required=False,
        default=u'',
    )

    url_site = schema.TextLine(
        title=_(u'url_site',
                default=_(u"Url site")),
        description=_(u'help_url_site',
                      default=_(u"Url of the site.")),
        required=False,
        default=u'',
    )

    main_color = schema.TextLine(
        title=_(u'main_color',
                default=_(u'Color principal')),
        description=_(u'help_main_color',
                      default=_(u'Aquest és el color principal de l\'espai.')),
        required=True,
        default=u'#003556',
    )

    secondary_color = schema.TextLine(
        title=_(u'secondary_color',
                default=_(u'Color secundari')),
        description=_(u'help_secondary_color',
                      default=_(u'Aquest és el color secundari de l\'espai.')),
        required=True,
        default=u'#003556',
    )

    maxui_form_bg = schema.TextLine(
        title=_(u'maxui_form_bg',
                default=_(u'Color del fons del widget de MAX.')),
        description=_(u'help_maxui_form_bg',
                      default=_(u'Aquest és el color del fons del widget de MAX.')),
        required=True,
        default=u'#E8E8E8',
    )

    alt_gradient_start_color = schema.TextLine(
        title=_(u'alt_gradient_start_color',
                default=_(u'Color inicial dels gradients.')),
        description=_(u'help_alt_gradient_start_color',
                      default=_(u'Aquest és el color inicial dels gradients.')),
        required=True,
        default=u'#FFFFFF',
    )

    alt_gradient_end_color = schema.TextLine(
        title=_(u'alt_gradient_end_color',
                default=_(u'Color final dels gradients')),
        description=_(u'help_alt_gradient_end_color',
                      default=_(u'Aquest és el color final dels gradients.')),
        required=True,
        default=u'#FFFFFF',
    )

    background_property = schema.TextLine(
        title=_(u'background_property',
                default=_(u'Propietat de fons global')),
        description=_(u'help_background_property',
                      default=_(u'Aquest és la propietat de CSS de background.')),
        required=True,
        default=u'transparent',
    )

    background_color = schema.TextLine(
        title=_(u'background_color',
                default=_(u'Color de fons global')),
        description=_(u'help_background_color',
                      default=_(u'Aquest és el color de fons global o la propietat corresponent.')),
        required=True,
        default=u'#EAE9E4',
    )

    buttons_color_primary = schema.TextLine(
        title=_(u'buttons_color_primary',
                default=_(u'Color primari dels botons')),
        description=_(u'help_buttons_color_primary',
                      default=_(u'Aquest és el color primari dels botons.')),
        required=True,
        default=u'#003556',
    )

    buttons_color_secondary = schema.TextLine(
        title=_(u'buttons_color_secondary',
                default=_(u'Color secundari dels botons')),
        description=_(u'help_buttons_color_secondary',
                      default=_(u'Aquest és el color secundari dels botons.')),
        required=True,
        default=u'#003556',
    )

    color_community_closed = schema.TextLine(
        title=_(u'color_community_closed',
                default=_(u'Color comunitat tancada')),
        description=_(u'help_color_community_closed',
                      default=_(u'Aquest és el color per les comunitats tancades.')),
        required=True,
        default=u'#08C2B1',
    )

    color_community_organizative = schema.TextLine(
        title=_(u'color_community_organizative',
                default=_(u'Color comunitat organitzativa')),
        description=_(u'help_color_community_organizative',
                      default=_(u'Aquest és el color per les comunitats organitzatives.')),
        required=True,
        default=u'#C4B408',
    )

    color_community_open = schema.TextLine(
        title=_(u'color_community_open',
                default=_(u'Color comunitat oberta')),
        description=_(u'help_color_community_open',
                      default=_(u'Aquest és el color per les comunitats obertes.')),
        required=True,
        default=u'#556B2F',
    )

    form.widget(nonvisibles=Select2MAXUserInputFieldWidget)
    nonvisibles = schema.List(
        title=_(u'no_visibles'),
        description=_(u'Llista amb les persones que no han de sortir a les cerques i que tenen acces restringit per la resta de persones.'),
        value_type=schema.TextLine(),
        required=False,
        default=[])

    people_literal = schema.Choice(
        title=_(u'people_literal'),
        description=_(u'Literals que identifiquen als usuaris de les comunitats i les seves aportacions.'),
        values=[_(u'thinnkers'), _(u'persones'), _(u'participants'), _(u'collegiates'), _(u'who_is_who')],
        required=True,
        default=_(u'persones'))

    form.widget(quicklinks_literal=DataGridFieldFactory)
    quicklinks_literal = schema.List(title=_(u'Text Quick Links'),
                                     description=_(u'Add the quick links by language'),
                                     value_type=DictRow(title=_(u'help_quicklinks_literal'),
                                                        schema=ILiteralQuickLinks))

    quicklinks_icon = schema.TextLine(
        title=_(u'quicklinks_icon',
                default='icon-link'),
        description=_(u'help_quicklinks_icon',
                      default=_(u'Afegiu la icona del Font Awesome que voleu que es mostri')),
        required=False,
        default=u'',
    )

    form.widget(quicklinks_table=DataGridFieldFactory)
    quicklinks_table = schema.List(title=_(u'QuickLinks'),
                                   description=_(u'Add the quick links by language'),
                                   value_type=DictRow(title=_(u'help_quicklinks_table'),
                                                      schema=ITableQuickLinks))
    activity_view = schema.Choice(
        title=_(u'activity_view'),
        description=_(u'help_activity_view'),
        vocabulary=communityActivityView,
        required=True,
        default=u'Darreres activitats')

    dexterity.write_permission(language='zope2.ViewManagementScreens')
    language = schema.Choice(
        title=_(u'language',
                default=_(u'Idioma de l\'espai')),
        description=_(u'help_site_language',
                      default=_(u'Aquest és l\'idioma de l\'espai, que es configura quan el paquet es reinstala.')),
        required=True,
        values=['ca', 'es', 'en'],
        default='ca',
    )

    url_forget_password = schema.TextLine(
        title=_(u'url_forget_password',
                default=_(u'URL contrasenya oblidada')),
        description=_(u'help_url_forget_password',
                      default=_(u'Url per defecte: "/mail_password_form?userid=". Per a dominis externs indiqueu la url completa, "http://www.domini.cat"')),
        required=True,
        default=_(u'/mail_password_form?userid=')
    )

    show_news_in_app = schema.Bool(
        title=_(u'show_news_in_app',
                default=_(u"Show News Items in App")),
        description=_(u'help_show_news_in_app',
                      default=_(u"If selected, then gives the option to show the News Items in Mobile App.")),
        required=False,
        default=False,
    )

    show_literals = schema.Bool(
        title=_(u'show_literals',
                default=_(u"Show literal")),
        description=_(u'help_show_literals',
                      default=_(u"Disable or enable the display of community types in the portlet.")),
        required=False,
        default=False,
    )

    url_terms = schema.TextLine(
        title=_(u'url_terms',
                default=_(u"Url terms of use")),
        description=_(u'help_url_terms',
                      default=_(u"Url of the terms of use.")),
        required=False,
        default=u'',
    )

    subject_template = schema.TextLine(
        title=_(u'subject_template',
                default=_(u"Subject template")),
        description=_(u'help_subject_template',
                      default=_(u"Subject template to notify.")),
        required=False,
        default=u'',
    )

    message_template = schema.Text(
        title=_(u'message_template',
                default=_(u"Messate template")),
        description=_(u'help_message_template',
                      default=_(u"Message template to notify.")),
        required=False,
        default=u'',
    )

    message_template_activity_comment = schema.Text(
        title=_(u'message_template_activity_comment',
                default=_(u"Message template Activity and Comment")),
        description=_(u'help_message_template_activity_comment',
                      default=_(u"Message template to notify activity and comment.")),
        required=False,
        default=u'',
    )

    types_notify_mail = schema.List(
        title=_(u"types_notify_mail", default=u"Types to notify mail"),
        description=_(u'Select de types to notify mail'),
        value_type=schema.Choice(source=typesNotifyMailVocabulary),
        required=False,
        default=[u'Document', u'Link', u'File', u'Event', u'News Item', u'ExternalContent']
    )

    gAnalytics_enabled = schema.Bool(
        title=_(u"Enable querying Google Analytics' servers"),
        required=True,
        default=False
    )

    gAnalytics_view_ID = schema.TextLine(
        title=_(u'View ID'),
        description=_(u"Obtainable from the View Settings panel on Google Analytics Admin control panel"),
        required=False
    )

    gAnalytics_JSON_info = schema.Text(
        title=_(u"JSON encoded user info"),
        description=_(u"Enter the content of the JSON file given when the service account was created"),
        required=False
    )

    bitly_username = schema.TextLine(
        title=_(u"Bitly username"),
        description=_(u"The bitly username"),
        required=True,
    )

    dexterity.read_permission(bitly_api_key='zope2.ViewManagementScreens')
    dexterity.write_permission(bitly_api_key='zope2.ViewManagementScreens')
    bitly_api_key = schema.TextLine(
        title=_(u'Bitly api key'),
        description=_(u'The API Key Bitly'),
        required=True,
    )


class UlearnControlPanelSettingsForm(controlpanel.RegistryEditForm):
    """ Ulearn settings form """

    schema = IUlearnControlPanelSettings
    id = 'UlearnControlPanelSettingsForm'
    label = _(u'Ulearn settings')
    description = _(u'help_ulearn_settings_editform',
                    default=_(u'uLearn configuration registry.'))

    def updateFields(self):
        super(UlearnControlPanelSettingsForm, self).updateFields()

    def updateWidgets(self):
        super(UlearnControlPanelSettingsForm, self).updateWidgets()

    @button.buttonAndHandler(_('Save'), name=None)
    def handleSave(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self.applyChanges(data)

        if data.get('nonvisibles', False):
            """ Make users invisible in searches """
            maxclient, settings = getUtility(IMAXClient)()
            maxclient.setActor(settings.max_restricted_username)
            maxclient.setToken(settings.max_restricted_token)

            current_vips = maxclient.admin.security.get()
            current_vips = current_vips.get('roles').get('NonVisible', [])

            un_vip = [a for a in current_vips if a not in data.get('nonvisibles')]
            for user in un_vip:
                maxclient.admin.security.roles['NonVisible'].users[user].delete()

            make_vip = [vip for vip in data.get('nonvisibles') if vip not in current_vips]

            for user in make_vip:
                maxclient.admin.security.roles['NonVisible'].users[user].post()

        if data.get('activate_sharedwithme', True):
            if api.portal.get_registry_record('base5.core.controlpanel.core.IBaseCoreControlPanelSettings.elasticsearch') is not None:
                portal = api.portal.get()
                if portal.portal_actions.object.local_roles.visible is False:
                    portal.portal_actions.object.local_roles.visible = True
                portal.portal_actions.object.local_roles.manage_changeProperties(
                    available_expr="python:here.portal_type not in ['ulearn.community']")
                transaction.commit()

            else:
                IStatusMessage(self.request).addStatusMessage(_(u'Has marcat el comparteix pero falta la url del elasticsearch'), 'info')
        else:
            portal = api.portal.get()
            if portal.portal_actions.object.local_roles.visible is False:
                portal.portal_actions.object.local_roles.visible = True
            portal.portal_actions.object.local_roles.manage_changeProperties(
                available_expr="python:here.portal_type in ['privateFolder']")
            transaction.commit()

        IStatusMessage(self.request).addStatusMessage(_(u'Changes saved'), 'info')
        self.context.REQUEST.RESPONSE.redirect('@@ulearn-controlpanel')

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        IStatusMessage(self.request).addStatusMessage(_(u'Edit cancelled'),
                                                      'info')
        self.request.response.redirect('%s/%s' % (self.context.absolute_url(),
                                                  self.control_panel_view))


class UlearnControlPanel(controlpanel.ControlPanelFormWrapper):
    """ Ulearn settings control panel """
    form = UlearnControlPanelSettingsForm
