# -*- coding: utf-8 -*-
from zope import schema
from zope.component import getUtility
from z3c.form import button
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from plone.supermodel import model
from plone.directives import dexterity, form
from plone.app.registry.browser import controlpanel

from Products.statusmessages.interfaces import IStatusMessage

from ulearn5.core import _
from mrs5.max.utilities import IMAXClient
from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow
from plone import api
import transaction
from ulearn5.core.widgets.select2_maxuser_widget import Select2MAXUserInputFieldWidget


communityActivityView = SimpleVocabulary(
    [SimpleTerm(value=u'Darreres activitats', title=_(u'Darreres activitats')),
     SimpleTerm(value=u'Activitats mes valorades', title=_(u'Activitats mes valorades')),
     SimpleTerm(value=u'Activitats destacades', title=_(u'Activitats destacades'))]
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
        fields=['language', 'campus_url', 'library_url', 'people_literal',
                'threshold_winwin1', 'threshold_winwin2',
                'threshold_winwin3', 'stats_button', 'info_servei', 'activate_news', 'show_news_in_app', 'activate_sharedwithme', 'buttonbar_selected'])

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
                   fields=['activity_view', 'show_literals'])

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
        values=['stream', 'news', 'mycommunities', 'sharedwithme'],
        required=True,
        default='stream')

    main_color = schema.TextLine(
        title=_(u'main_color',
                default=_(u'Color principal')),
        description=_(u'help_main_color',
                      default=_(u'Aquest és el color principal de l\'espai.')),
        required=True,
        default=u'#f58d3d',
    )

    secondary_color = schema.TextLine(
        title=_(u'secondary_color',
                default=_(u'Color secundari')),
        description=_(u'help_secondary_color',
                      default=_(u'Aquest és el color secundari de l\'espai.')),
        required=True,
        default=u'#f58d3d',
    )

    maxui_form_bg = schema.TextLine(
        title=_(u'maxui_form_bg',
                default=_(u'Color del fons del widget de MAX.')),
        description=_(u'help_maxui_form_bg',
                      default=_(u'Aquest és el color del fons del widget de MAX.')),
        required=True,
        default=u'#34495c',
    )

    alt_gradient_start_color = schema.TextLine(
        title=_(u'alt_gradient_start_color',
                default=_(u'Color inicial dels gradients.')),
        description=_(u'help_alt_gradient_start_color',
                      default=_(u'Aquest és el color inicial dels gradients.')),
        required=True,
        default=u'#f58d3d',
    )

    alt_gradient_end_color = schema.TextLine(
        title=_(u'alt_gradient_end_color',
                default=_(u'Color final dels gradients')),
        description=_(u'help_alt_gradient_end_color',
                      default=_(u'Aquest és el color final dels gradients.')),
        required=True,
        default=u'#f58d3d',
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
        default=u'#eae9e4',
    )

    buttons_color_primary = schema.TextLine(
        title=_(u'buttons_color_primary',
                default=_(u'Color primari dels botons')),
        description=_(u'help_buttons_color_primary',
                      default=_(u'Aquest és el color primari dels botons.')),
        required=True,
        default=u'#34495E',
    )

    buttons_color_secondary = schema.TextLine(
        title=_(u'buttons_color_secondary',
                default=_(u'Color secundari dels botons')),
        description=_(u'help_buttons_color_secondary',
                      default=_(u'Aquest és el color secundari dels botons.')),
        required=True,
        default=u'#34495E',
    )

    color_community_closed = schema.TextLine(
        title=_(u'color_community_closed',
                default=_(u'Color comunitat tancada')),
        description=_(u'help_color_community_closed',
                      default=_(u'Aquest és el color per les comunitats tancades.')),
        required=True,
        default=u'#f58d3d',
    )

    color_community_organizative = schema.TextLine(
        title=_(u'color_community_organizative',
                default=_(u'Color comunitat organitzativa')),
        description=_(u'help_color_community_organizative',
                      default=_(u'Aquest és el color per les comunitats organitzatives.')),
        required=True,
        default=u'#b5c035',
    )

    color_community_open = schema.TextLine(
        title=_(u'color_community_open',
                default=_(u'Color comunitat oberta')),
        description=_(u'help_color_community_open',
                      default=_(u'Aquest és el color per les comunitats obertes.')),
        required=True,
        default=u'#888888',
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
        values=[_(u'thinnkers'), _(u'persones'), _(u'participants')],
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
        default='es',
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
            if api.portal.get_registry_record('base5.core.controlpanel.core.IGenwebCoreControlPanelSettings.elasticsearch') != None:
                portal = api.portal.get()
                if portal.portal_actions.object.local_roles.visible == False:
                    portal.portal_actions.object.local_roles.visible = True
                portal.portal_actions.object.local_roles.manage_changeProperties(
                available_expr = "python:here.portal_type not in ['ulearn.community']")
                transaction.commit()

            else:
                IStatusMessage(self.request).addStatusMessage(_(u'Has marcat el comparteix pero falta la url del elasticsearch'), 'info')
        else:
            portal = api.portal.get()
            if portal.portal_actions.object.local_roles.visible == False:
                portal.portal_actions.object.local_roles.visible = True
            portal.portal_actions.object.local_roles.manage_changeProperties(
            available_expr = "python:here.portal_type in ['privateFolder']")
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
