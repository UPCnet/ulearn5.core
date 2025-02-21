# -*- coding: utf-8 -*-
import transaction
from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow
from mrs5.max.utilities import IMAXClient
from plone import api
from plone.app.registry.browser import controlpanel
from plone.autoform import directives
from plone.supermodel import model
from Products.statusmessages.interfaces import IStatusMessage
from ulearn5.core import _
from ulearn5.core.widgets.select2_maxuser_widget import \
    Select2MAXUserInputFieldWidget
from z3c.form import button
from zope import schema
from zope.component import getUtility
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

communityActivityView = SimpleVocabulary(
    [SimpleTerm(value='Darreres activitats', title=_('Darreres activitats')),
     SimpleTerm(value='Activitats mes valorades', title=_('Activitats mes valorades')),
     SimpleTerm(value='Activitats destacades', title=_('Activitats destacades'))]
)

buttonbarView = SimpleVocabulary(
    [SimpleTerm(value='stream', title=_('Stream')),
     SimpleTerm(value='mycommunities', title=_('My Communities')),
     SimpleTerm(value='news', title=_('News')),
     SimpleTerm(value='sharedwithme', title=_('Shared With Me'))]
)

cronTasksVocabulary = SimpleVocabulary(
    [SimpleTerm(value='syncldapgroups', title=_('syncldapgroups')),
     SimpleTerm(value='rebuild_user_catalog', title=_('rebuild_user_catalog')),
     SimpleTerm(value='delete_user_catalog', title=_('delete_user_catalog')),
     SimpleTerm(value='delete_local_roles', title=_('delete_local_roles')),
     SimpleTerm(value='api/saveeditacl', title=_('api/saveeditacl')),
     SimpleTerm(value='etherpad_searchabletext', title=_('etherpad_searchabletext')),
     SimpleTerm(value='rebuild_users_portrait', title=_('rebuild_users_portrait')),
     SimpleTerm(value='export_users_communities', title=_('export_users_communities')),
     ]
)

typesNotifyMailVocabulary = SimpleVocabulary(
    [SimpleTerm(value='Document', title=_('Document')),
     SimpleTerm(value='Link', title=_('Link')),
     SimpleTerm(value='File', title=_('File')),
     SimpleTerm(value='Event', title=_('Event')),
     SimpleTerm(value='News Item', title=_('News Item')),
     SimpleTerm(value='ExternalContent', title=_('ExternalContent')),
     SimpleTerm(value='Activity', title=_('Activity')),
     SimpleTerm(value='Comment', title=_('Comment')),
     ]
)


class ILiteralQuickLinks(model.Schema):
    language = schema.Choice(
        title=_('Language'),
        required=True,
        vocabulary='plone.app.vocabularies.SupportedContentLanguages'
    )
    text = schema.TextLine(title=_('Text'), required=False)


class ITableQuickLinks(model.Schema):
    language = schema.Choice(
        title=_('Language'),
        required=True,
        vocabulary='plone.app.vocabularies.SupportedContentLanguages'
    )
    text = schema.TextLine(title=_('Text'), required=False)
    link = schema.TextLine(title=_('Link'), required=False)
    icon = schema.TextLine(title=_('Font Awesome Icon'), required=False)
    new_window = schema.Bool(title=_('New window'), required=False, default=True)


class IUlearnControlPanelSettings(model.Schema):
    """ Global Ulearn settings. This describes records stored in the
    configuration registry and obtainable via plone.registry.
    """

    model.fieldset(
        'General',
        _('General'),
        fields=['html_title_ca', 'html_title_es', 'html_title_en', 'language', 'url_forget_password', 'campus_url', 'library_url', 'people_literal',
                'threshold_winwin1', 'threshold_winwin2', 'threshold_winwin3', 'stats_button',
                'info_servei', 'activate_news', 'show_news_in_app', 'activate_sharedwithme',
                'buttonbar_selected', 'cron_tasks', 'url_private_policy', 'url_site'])

    model.fieldset(
        'Design',
        _('Design'),
        fields=['main_color', 'secondary_color', 'background_property',
                'background_color',
                'buttons_color_primary', 'buttons_color_secondary',
                'maxui_form_bg',
                'alt_gradient_start_color', 'alt_gradient_end_color',
                'color_community_closed', 'color_community_organizative',
                'color_community_open'])

    model.fieldset('Visibility',
                   _('Visibility'),
                   fields=['nonvisibles'])

    model.fieldset('Quick Links',
                   _('QuickLinks'),
                   fields=['quicklinks_literal', 'quicklinks_icon', 'quicklinks_table'])

    model.fieldset('Communities',
                   _('Communities'),
                   fields=['activity_view', 'show_literals', 'url_terms', 'types_notify_mail', 'subject_template', 'message_template', 'message_template_activity_comment'])

    model.fieldset('Google Analytics',
                   'Google Analytics',
                   fields=['gAnalytics_enabled', 'gAnalytics_view_ID', 'gAnalytics_JSON_info'])

    model.fieldset('Bitly',
                   'Bitly',
                   fields=['bitly_username', 'bitly_api_key'])

    html_title_ca = schema.TextLine(
        title=_("html_title_ca",
                default="Títol del web amb HTML tags (negretes) [CA]"),
        description=_("help_html_title",
                      default="Afegiu el títol del Ulearn. Podeu incloure tags HTML"),
        required=False,
    )

    html_title_es = schema.TextLine(
        title=_("html_title_es",
                default="Títol del web amb HTML tags (negretes) [ES]"),
        description=_("help_html_title",
                      default="Afegiu el títol del Ulearn. Podeu incloure tags HTML"),
        required=False,
    )

    html_title_en = schema.TextLine(
        title=_("html_title_en",
                default="Títol del web amb HTML tags (negretes) [EN]"),
        description=_("help_html_title",
                      default="Afegiu el títol del Ulearn. Podeu incloure tags HTML"),
        required=False,
    )

    campus_url = schema.TextLine(
        title=_('campus_url',
                default=_('URL del campus')),
        description=_('help_campus_url',
                      default=_('Afegiu la URL del campus associat a aquestes comunitats.')),
        required=False,
        default='',
    )

    library_url = schema.TextLine(
        title=_('library_url',
                default=_('URL de la biblioteca')),
        description=_('help_library_url',
                      default=_('Afegiu la URL de la biblioteca associada a aquestes comunitats.')),
        required=False,
        default='',
    )

    threshold_winwin1 = schema.TextLine(
        title=_('llindar_winwin1',
                default=_('Llindar del winwin 1')),
        description=_('help_llindar_winwin1',
                      default=_('Aquest és el llindar del winwin #1.')),
        required=False,
        default='50',
    )

    threshold_winwin2 = schema.TextLine(
        title=_('llindar_winwin2',
                default=_('Llindar del winwin 2')),
        description=_('help_llindar_winwin2',
                      default=_('Aquest és el llindar del winwin #2.')),
        required=False,
        default='100',
    )

    threshold_winwin3 = schema.TextLine(
        title=_('llindar_winwin3',
                default=_('Llindar del winwin 3')),
        description=_('help_llindar_winwin3',
                      default=_('Aquest és el llindar del winwin #3.')),
        required=False,
        default='500',
    )

    stats_button = schema.Bool(
        title=_('stats_button',
                default=_("Mostrar botó d'accés a estadístiques diàries")),
        description=_('help_stats_button',
                      default=_("Mostra o no el botó d'accés a estadístiques diàries a stats/activity i stats/chats")),
        required=False,
        default=False,
    )

    info_servei = schema.TextLine(
        title=_('info_servei',
                default=_('Informació del servei')),
        description=_('help_info_servei',
                      default=_('Aquest és l\'enllaç al servei.')),
        required=False,
    )

    activate_news = schema.Bool(
        title=_('activate_news',
                default=_("Mostra les noticies a les que estic subscrit")),
        description=_('help_activate_news',
                      default=_("Mostra o no el botó de Noticies a la tile central de les comunitats")),
        required=False,
        default=False,
    )

    activate_sharedwithme = schema.Bool(
        title=_('activate_sharedwithme',
                default=_("Mostra el que hi ha compartit amb mi")),
        description=_('help_activate_sharedwithme',
                      default=_("Mostra o no el botó del que hi ha compartit amb mi i el que hi ha compartit a les comunitats")),
        required=False,
        default=False,
    )

    buttonbar_selected = schema.Choice(
        title=_('buttonbar_selected'),
        description=_('Select the active button in the button bar.'),
        vocabulary=buttonbarView,
        required=True,
        default='stream',
    )

    cron_tasks = schema.List(
        title=_("cron_tasks", default="Cron tasks"),
        description=_('Tasques que s\'executaran per la nit'),
        value_type=schema.Choice(source=cronTasksVocabulary),
        required=False,
    )

    url_private_policy = schema.TextLine(
        title=_('url_private_policy',
                default=_("Url private policy")),
        description=_('help_url_private_policy',
                      default=_("Url of the private policy.")),
        required=False,
        default='',
    )

    url_site = schema.TextLine(
        title=_('url_site',
                default=_("Url site")),
        description=_('help_url_site',
                      default=_("Url of the site.")),
        required=False,
        default='',
    )

    main_color = schema.TextLine(
        title=_('main_color',
                default=_('Color principal')),
        description=_('help_main_color',
                      default=_('Aquest és el color principal de l\'espai.')),
        required=True,
        default='#003556',
    )

    secondary_color = schema.TextLine(
        title=_('secondary_color',
                default=_('Color secundari')),
        description=_('help_secondary_color',
                      default=_('Aquest és el color secundari de l\'espai.')),
        required=True,
        default='#003556',
    )

    maxui_form_bg = schema.TextLine(
        title=_('maxui_form_bg',
                default=_('Color del fons del widget de MAX.')),
        description=_('help_maxui_form_bg',
                      default=_('Aquest és el color del fons del widget de MAX.')),
        required=True,
        default='#E8E8E8',
    )

    alt_gradient_start_color = schema.TextLine(
        title=_('alt_gradient_start_color',
                default=_('Color inicial dels gradients.')),
        description=_('help_alt_gradient_start_color',
                      default=_('Aquest és el color inicial dels gradients.')),
        required=True,
        default='#FFFFFF',
    )

    alt_gradient_end_color = schema.TextLine(
        title=_('alt_gradient_end_color',
                default=_('Color final dels gradients')),
        description=_('help_alt_gradient_end_color',
                      default=_('Aquest és el color final dels gradients.')),
        required=True,
        default='#FFFFFF',
    )

    background_property = schema.TextLine(
        title=_('background_property',
                default=_('Propietat de fons global')),
        description=_('help_background_property',
                      default=_('Aquest és la propietat de CSS de background.')),
        required=True,
        default='transparent',
    )

    background_color = schema.TextLine(
        title=_('background_color',
                default=_('Color de fons global')),
        description=_('help_background_color',
                      default=_('Aquest és el color de fons global o la propietat corresponent.')),
        required=True,
        default='#EAE9E4',
    )

    buttons_color_primary = schema.TextLine(
        title=_('buttons_color_primary',
                default=_('Color primari dels botons')),
        description=_('help_buttons_color_primary',
                      default=_('Aquest és el color primari dels botons.')),
        required=True,
        default='#003556',
    )

    buttons_color_secondary = schema.TextLine(
        title=_('buttons_color_secondary',
                default=_('Color secundari dels botons')),
        description=_('help_buttons_color_secondary',
                      default=_('Aquest és el color secundari dels botons.')),
        required=True,
        default='#003556',
    )

    color_community_closed = schema.TextLine(
        title=_('color_community_closed',
                default=_('Color comunitat tancada')),
        description=_('help_color_community_closed',
                      default=_('Aquest és el color per les comunitats tancades.')),
        required=True,
        default='#08C2B1',
    )

    color_community_organizative = schema.TextLine(
        title=_('color_community_organizative',
                default=_('Color comunitat organitzativa')),
        description=_('help_color_community_organizative',
                      default=_('Aquest és el color per les comunitats organitzatives.')),
        required=True,
        default='#C4B408',
    )

    color_community_open = schema.TextLine(
        title=_('color_community_open',
                default=_('Color comunitat oberta')),
        description=_('help_color_community_open',
                      default=_('Aquest és el color per les comunitats obertes.')),
        required=True,
        default='#556B2F',
    )

    directives.widget('nonvisibles', Select2MAXUserInputFieldWidget)
    nonvisibles = schema.List(
        title=_('no_visibles'),
        description=_('Llista amb les persones que no han de sortir a les cerques i que tenen acces restringit per la resta de persones.'),
        value_type=schema.TextLine(),
        required=False,
        default=[])

    people_literal = schema.Choice(
        title=_('people_literal'),
        description=_('Literals que identifiquen als usuaris de les comunitats i les seves aportacions.'),
        values=[_('thinnkers'), _('persones'), _('participants'), _('collegiates'), _('who_is_who')],
        required=True,
        default=_('persones'))

    directives.widget('quicklinks_table', DataGridFieldFactory)
    quicklinks_literal = schema.List(title=_('Text Quick Links'),
                                     description=_('Add the quick links by language'),
                                     value_type=DictRow(title=_('help_quicklinks_literal'),
                                                        schema=ILiteralQuickLinks))

    quicklinks_icon = schema.TextLine(
        title=_('quicklinks_icon',
                default='icon-link'),
        description=_('help_quicklinks_icon',
                      default=_('Afegiu la icona del Font Awesome que voleu que es mostri')),
        required=False,
        default='',
    )

    directives.widget('quicklinks_table', DataGridFieldFactory)
    quicklinks_table = schema.List(title=_('QuickLinks'),
                                   description=_('Add the quick links by language'),
                                   value_type=DictRow(title=_('help_quicklinks_table'),
                                                      schema=ITableQuickLinks))
    activity_view = schema.Choice(
        title=_('activity_view'),
        description=_('help_activity_view'),
        vocabulary=communityActivityView,
        required=True,
        default='Darreres activitats')

    directives.write_permission(language='zope2.ViewManagementScreens')
    language = schema.Choice(
        title=_('language',
                default=_('Idioma de l\'espai')),
        description=_('help_site_language',
                      default=_('Aquest és l\'idioma de l\'espai, que es configura quan el paquet es reinstala.')),
        required=True,
        values=['ca', 'es', 'en'],
        default='ca',
    )

    url_forget_password = schema.TextLine(
        title=_('url_forget_password',
                default=_('URL contrasenya oblidada')),
        description=_('help_url_forget_password',
                      default=_('Url per defecte: "/mail_password_form?userid=". Per a dominis externs indiqueu la url completa, "http://www.domini.cat"')),
        required=True,
        default=_('/mail_password_form?userid=')
    )

    show_news_in_app = schema.Bool(
        title=_('show_news_in_app',
                default=_("Show News Items in App")),
        description=_('help_show_news_in_app',
                      default=_("If selected, then gives the option to show the News Items in Mobile App.")),
        required=False,
        default=False,
    )

    show_literals = schema.Bool(
        title=_('show_literals',
                default=_("Show literal")),
        description=_('help_show_literals',
                      default=_("Disable or enable the display of community types in the portlet.")),
        required=False,
        default=False,
    )

    url_terms = schema.TextLine(
        title=_('url_terms',
                default=_("Url terms of use")),
        description=_('help_url_terms',
                      default=_("Url of the terms of use.")),
        required=False,
        default='',
    )

    subject_template = schema.TextLine(
        title=_('subject_template',
                default=_("Subject template")),
        description=_('help_subject_template',
                      default=_("Subject template to notify.")),
        required=False,
        default='',
    )

    message_template = schema.Text(
        title=_('message_template',
                default=_("Messate template")),
        description=_('help_message_template',
                      default=_("Message template to notify.")),
        required=False,
        default='',
    )

    message_template_activity_comment = schema.Text(
        title=_('message_template_activity_comment',
                default=_("Message template Activity and Comment")),
        description=_('help_message_template_activity_comment',
                      default=_("Message template to notify activity and comment.")),
        required=False,
        default='',
    )

    types_notify_mail = schema.List(
        title=_("types_notify_mail", default="Types to notify mail"),
        description=_('Select de types to notify mail'),
        value_type=schema.Choice(source=typesNotifyMailVocabulary),
        required=False,
        default=['Document', 'Link', 'File', 'Event', 'News Item', 'ExternalContent']
    )

    gAnalytics_enabled = schema.Bool(
        title=_("Enable querying Google Analytics' servers"),
        required=True,
        default=False
    )

    gAnalytics_view_ID = schema.TextLine(
        title=_('View ID'),
        description=_("Obtainable from the View Settings panel on Google Analytics Admin control panel"),
        required=False
    )

    gAnalytics_JSON_info = schema.Text(
        title=_("JSON encoded user info"),
        description=_("Enter the content of the JSON file given when the service account was created"),
        required=False
    )

    bitly_username = schema.TextLine(
        title=_("Bitly username"),
        description=_("The bitly username"),
        required=True,
    )

    directives.read_permission(bitly_api_key='zope2.ViewManagementScreens')
    directives.write_permission(bitly_api_key='zope2.ViewManagementScreens')
    bitly_api_key = schema.TextLine(
        title=_('Bitly api key'),
        description=_('The API Key Bitly'),
        required=True,
    )


class UlearnControlPanelSettingsForm(controlpanel.RegistryEditForm):
    """ Ulearn settings form """

    schema = IUlearnControlPanelSettings
    id = 'UlearnControlPanelSettingsForm'
    label = _('Ulearn settings')
    description = _('help_ulearn_settings_editform',
                    default=_('uLearn configuration registry.'))

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
                IStatusMessage(self.request).addStatusMessage(_('Has marcat el comparteix pero falta la url del elasticsearch'), 'info')
        else:
            portal = api.portal.get()
            if portal.portal_actions.object.local_roles.visible is False:
                portal.portal_actions.object.local_roles.visible = True
            portal.portal_actions.object.local_roles.manage_changeProperties(
                available_expr="python:here.portal_type in ['privateFolder']")
            transaction.commit()

        IStatusMessage(self.request).addStatusMessage(_('Changes saved'), 'info')
        self.context.REQUEST.RESPONSE.redirect('@@ulearn-controlpanel')

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        IStatusMessage(self.request).addStatusMessage(_('Edit cancelled'),
                                                      'info')
        self.request.response.redirect('%s/%s' % (self.context.absolute_url(),
                                                  self.control_panel_view))


class UlearnControlPanel(controlpanel.ControlPanelFormWrapper):
    """ Ulearn settings control panel """
    form = UlearnControlPanelSettingsForm
