# -*- coding: utf-8 -*-
from Products.CMFPlone.interfaces import INonInstallable
from zope.interface import implementer
from plone import api
from zope.component import getUtility
from zope.component import queryUtility
from zope.component import getMultiAdapter
from zope.component.hooks import getSite
from plone.registry.interfaces import IRegistry
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletAssignmentMapping
from plone.portlets.utils import registerPortletType
from plone.portlets.utils import unregisterPortletType
from Products.CMFCore.utils import getToolByName
from ulearn5.core.controlpanel import IUlearnControlPanelSettings
from ulearn5.core.controlportlets import IPortletsSettings

from ulearn5.core import _

import logging

PROFILE_ID = 'profile-ulearn5.core:default'
# Specify the indexes you want, with ('index_name', 'index_type')
INDEXES = (('subscribed_users', 'KeywordIndex'),
           ('subscribed_items', 'FieldIndex'),
           ('community_type', 'FieldIndex'),
           ('community_hash', 'FieldIndex'),
           ('is_shared', 'BooleanIndex'),
           )


@implementer(INonInstallable)
class HiddenProfiles(object):

    def getNonInstallableProfiles(self):
        """Hide uninstall profile from site-creation and quickinstaller"""
        return [
            'ulearn5.core:uninstall',
        ]


def post_install(context):
    """Post install script"""
    # Do something at the end of the installation of this package.


def uninstall(context):
    """Uninstall script"""
    # Do something at the end of the uninstallation of this package.


# Afegit creació d'indexos programàticament i controladament per:
# http://maurits.vanrees.org/weblog/archive/2009/12/catalog
def add_catalog_indexes(context, logger=None):
    """Method to add our wanted indexes to the portal_catalog.

    @parameters:

    When called from the import_various method below, 'context' is
    the plone site and 'logger' is the portal_setup logger.  But
    this method can also be used as upgrade step, in which case
    'context' will be portal_setup and 'logger' will be None.
    """
    if logger is None:
        # Called as upgrade step: define our own logger.
        logger = logging.getLogger(__name__)

    # Run the catalog.xml step as that may have defined new metadata
    # columns.  We could instead add <depends name="catalog"/> to
    # the registration of our import step in zcml, but doing it in
    # code makes this method usable as upgrade step as well.  Note that
    # this silently does nothing when there is no catalog.xml, so it
    # is quite safe.
    setup = getToolByName(context, 'portal_setup')
    setup.runImportStepFromProfile(PROFILE_ID, 'catalog')

    catalog = getToolByName(context, 'portal_catalog')
    indexes = catalog.indexes()

    indexables = []
    for name, meta_type in INDEXES:
        if name not in indexes:
            catalog.addIndex(name, meta_type)
            indexables.append(name)
            logger.info('Added %s for field %s.', meta_type, name)
    if len(indexables) > 0:
        logger.info('Indexing new indexes %s.', ', '.join(indexables))
        catalog.manage_reindexIndex(ids=indexables)


def setup_ulearn_icon_set():
    # The list is composed of up to four rows of icons, each row being a string
    # with the name (comma separated) of each icon. There should be all four
    # rows in place, even if they are empty
    ulearn_custom_icons = [u'fullscreen,|,code,|,save,|,plonetemplates,|,bold,italic,underline,strikethrough,|,forecolor,|,justifyleft,justifycenter,justifyright,|,cut,copy,paste,pastetext,pasteword,|,search,replace,|,bullist,numlist,|,outdent,indent,blockquote,|,undo,redo,|,link,unlink,anchor',
                           u'formatselect,style,|,cleanup,removeformat,|,image,media,|,tablecontrols,styleprops,|,visualaid,|,sub,sup,|,charmap',
                           u'',
                           u''
                           ]

    api.portal.set_registry_record('base5.core.controlpanel.core.IGenwebCoreControlPanelSettings.custom_editor_icons', ulearn_custom_icons)


def setup_ulearn_portlets():
    portlets_slots = ["plone.leftcolumn", "plone.rightcolumn",
                      "ContentWellPortlets.AbovePortletManager1", "ContentWellPortlets.AbovePortletManager2",
                      "ContentWellPortlets.AbovePortletManager3", "ContentWellPortlets.BelowPortletManager1",
                      "ContentWellPortlets.BelowPortletManager2", "ContentWellPortlets.BelowPortletManager3",
                      "ContentWellPortlets.BelowTitlePortletManager1", "ContentWellPortlets.BelowTitlePortletManager2",
                      "ContentWellPortlets.BelowTitlePortletManager3"]

    site = getSite()
    activate_portlets = []
    for manager_name in portlets_slots:
        if 'ContentWellPortlets' in manager_name:
            manager = getUtility(IPortletManager, name=manager_name, context=site['front-page'])
            mapping = getMultiAdapter((site['front-page'], manager), IPortletAssignmentMapping)
            [activate_portlets.append(item[1].title) for item in mapping.items()]
        else:
            manager = getUtility(IPortletManager, name=manager_name, context=site)
            mapping = getMultiAdapter((site, manager), IPortletAssignmentMapping)
            [activate_portlets.append(item[1].title) for item in mapping.items()]

    registry = queryUtility(IRegistry)
    portlets_tool = registry.forInterface(IPortletsSettings, check=False)
    portlets = IPortletsSettings.namesAndDescriptions()
    if portlets:
        for portlet, description in portlets:
            idPortlet = portlet.replace('_', '.')
            valuePortlet = portlets_tool.__getattr__(portlet) if portlets_tool.__getattr__(portlet) else description.default

            if valuePortlet is True:
                registerPortletType(site,
                                    title=portlet,
                                    description=portlet,
                                    addview=idPortlet)

            if idPortlet.split('.')[-1] in activate_portlets:
                valuePortlet = True
                registerPortletType(site,
                                    title=portlet,
                                    description=portlet,
                                    addview=idPortlet)

            if valuePortlet is False:
                unregisterPortletType(site, idPortlet)

    lessvars = registry.get('plone.lessvariables', {})
    lessvars['plone-screen-sm-min'] = u'300px'
    lessvars['plone-screen-xs-min'] = u'300px'

    import transaction
    transaction.commit()


def setupVarious(context):
    # Ordinarily, GenericSetup handlers check for the existence of XML files.
    # Here, we are not parsing an XML file, but we use this text file as a
    # flag to check that we actually meant for this import step to be run.
    # The file is found in profiles/default.
    if context.readDataFile('ulearn5.core_various.txt') is None:
        return

    portal = context.getSite()
    logger = logging.getLogger(__name__)

    add_catalog_indexes(portal, logger)
    setup_ulearn_icon_set()
    setup_ulearn_portlets()

    # Set the default page to the homepage view
    portal.setDefaultPage('front-page')

    # Allow connected users to view the homepage by allowing them either on
    # Plone site and in the front-page (HomePortlets placeholder)
    portal.manage_setLocalRoles('AuthenticatedUsers', ['Reader'])
    portal['front-page'].manage_setLocalRoles('AuthenticatedUsers', ['Reader'])

    # Assign permission for delete the front-page
    portal['front-page']._Delete_objects_Permission = ('Manager',)

    # Rename front-page
    portal['front-page'].setTitle(portal.translate(_(u'Front page')))
    portal['front-page'].reindexObject()

    # Set mailhost
    mh = getToolByName(portal, 'MailHost')
    mh.smtp_host = 'localhost'
    portal.email_from_name = 'uLearn Administrator'
    portal.email_from_address = 'no-reply@upcnet.es'

    # Delete original 'Events' folder for not to colision with the community ones
    if getattr(portal, 'events', False):
        portal.manage_delObjects('events')

    # Delete 'Members' folder
    if getattr(portal, 'Members', False):
        portal.manage_delObjects('Members')

    # Recall the last language set for this instance in case of reinstall
    registry = queryUtility(IRegistry)
    settings = registry.forInterface(IUlearnControlPanelSettings, check=False)

    pl = getToolByName(portal, 'portal_languages')
    pl.setDefaultLanguage(settings.language)
    pl.addSupportedLanguage(settings.language)

    # Remove right column portlets programatically because now don't use them
    portal = getSite()
    target_manager = queryUtility(IPortletManager, name='plone.rightcolumn', context=portal)
    target_manager_assignments = getMultiAdapter((portal, target_manager), IPortletAssignmentMapping)

    # purge existing portlets
    for portlet in target_manager_assignments.keys():
        del target_manager_assignments[portlet]

    # Set default TimeZone (p.a.event)
    api.portal.set_registry_record('plone.portal_timezone', 'Europe/Madrid')
    api.portal.set_registry_record('plone.first_weekday', 0)

    # Unset validate e-mail as we want the users to be created right the way
    portal.validate_email = False

    # Update types with default action listing
    site_properties = api.portal.get_tool(name='portal_properties').site_properties
    try:
        site_properties.manage_addProperty('typesUseViewActionInListings', 'ulearn.video', 'lines')
    except:
        print "La propietat 'ulearn.video' ja estava afegida al portal site_properties"

    # Define colors of site
    registry = queryUtility(IRegistry)
    context.settings = registry.forInterface(IUlearnControlPanelSettings)
    context.settings.main_color = u'#003556'
    context.settings.secondary_color = u'#003556'
    context.settings.background_property = u'transparent'
    context.settings.background_color = u'#EAE9E4'
    context.settings.buttons_color_primary = u'#003556'
    context.settings.buttons_color_secondary = u'#003556'
    context.settings.maxui_form_bg = u'#E8E8E8'
    context.settings.alt_gradient_start_color = u'#FFFFFF'
    context.settings.alt_gradient_end_color = u'#FFFFFF'
    context.settings.color_community_closed = u'#08C2B1'
    context.settings.color_community_organizative = u'#C4B408'
    context.settings.color_community_open = u'#556B2F'

    import transaction
    transaction.commit()
