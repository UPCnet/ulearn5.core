# -*- coding: utf-8 -*-
from __future__ import print_function

import logging

from plone import api
from plone.portlets.interfaces import (IPortletAssignmentMapping,
                                       IPortletManager)
from plone.portlets.utils import registerPortletType, unregisterPortletType
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.interfaces import INonInstallable, ITinyMCESchema
from Products.CMFPlone.interfaces.controlpanel import ISiteSchema
from ulearn5.core import _
from ulearn5.core.controlpanel import IUlearnControlPanelSettings
from ulearn5.core.controlportlets import IPortletsSettings
from zope.component import getMultiAdapter, getUtility, queryUtility
from zope.component.hooks import getSite
from zope.interface import implementer

PROFILE_ID = 'profile-ulearn5.core:default'
# Specify the indexes you want, with ('index_name', 'index_type')
INDEXES = (('subscribed_users', 'KeywordIndex'),
           ('subscribed_items', 'FieldIndex'),
           ('community_type', 'FieldIndex'),
           ('community_hash', 'FieldIndex'),
           ('is_shared', 'BooleanIndex'),
           ('timezone', 'FieldIndex'),
           ('tab_view', 'FieldIndex'),
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
    setup = api.portal.get_tool(name='portal_setup')
    setup.runImportStepFromProfile(PROFILE_ID, 'catalog')

    catalog = api.portal.get_tool(name='portal_catalog')
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
    ulearn_custom_icons = ['fullscreen,|,code,|,save,|,plonetemplates,|,bold,italic,underline,strikethrough,|,forecolor,|,justifyleft,justifycenter,justifyright,|,cut,copy,paste,pastetext,pasteword,|,search,replace,|,bullist,numlist,|,outdent,indent,blockquote,|,undo,redo,|,link,unlink,anchor',
                           'formatselect,style,|,cleanup,removeformat,|,image,media,|,tablecontrols,styleprops,|,visualaid,|,sub,sup,|,charmap',
                           '',
                           ''
                           ]

    api.portal.set_registry_record('base5.core.controlpanel.core.IBaseCoreControlPanelSettings.custom_editor_icons', ulearn_custom_icons)


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
            [activate_portlets.append(item[1].title) for item in list(mapping.items())]
        else:
            manager = getUtility(IPortletManager, name=manager_name, context=site)
            mapping = getMultiAdapter((site, manager), IPortletAssignmentMapping)
            [activate_portlets.append(item[1].title) for item in list(mapping.items())]

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
    lessvars['plone-screen-sm-min'] = '300px'
    lessvars['plone-screen-xs-min'] = '300px'

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
    portal['front-page'].setTitle(portal.translate(_('Front page')))
    portal['front-page'].reindexObject()

    # Set mailhost
    mh = api.portal.get_tool(name='MailHost')
    mh.smtp_host = 'localhost'
    portal.email_from_name = 'uLearn Administrator'
    portal.email_from_address = 'no-reply@upcnet.es'

    # Delete original 'Events' folder for not to colision with the community ones
    if getattr(portal, 'events', False):
        portal.manage_delObjects('events')

    # Recall the last language set for this instance in case of reinstall
    registry = queryUtility(IRegistry)
    settings = registry.forInterface(IUlearnControlPanelSettings, check=False)

    pl = api.portal.get_tool(name='portal_languages')
    language = settings.language
    if isinstance(language, str):
        language = language.decode('UTF-8')
    pl.setDefaultLanguage(language)
    pl.addSupportedLanguage(language)

    # Remove right column portlets programatically because now don't use them
    portal = getSite()
    target_manager = queryUtility(IPortletManager, name='plone.rightcolumn', context=portal)
    target_manager_assignments = getMultiAdapter((portal, target_manager), IPortletAssignmentMapping)

    # purge existing portlets
    for portlet in list(target_manager_assignments.keys()):
        del target_manager_assignments[portlet]

    # Set default TimeZone (p.a.event)
    api.portal.set_registry_record('plone.portal_timezone', 'Europe/Madrid')
    api.portal.set_registry_record('plone.first_weekday', 0)

    # Unset validate e-mail as we want the users to be created right the way
    portal.validate_email = False

    # Setup Tiny
    tiny_settings = registry.forInterface(ITinyMCESchema, prefix="plone", check=False)
    tiny_settings.resizing = True
    tiny_settings.autoresize = False
    tiny_settings.editor_width = '100%'
    tiny_settings.editor_height = '500'

    # Permisos para añadir etiquetas
    site_tool = registry.forInterface(ISiteSchema, prefix='plone')
    site_tool.roles_allowed_to_add_keywords = ['Manager', 'Site Administrator', 'Reviewer', 'Authenticated']

    # Update types with default action listing
    site_properties = api.portal.get_tool(name='portal_properties').site_properties
    try:
        site_properties.manage_addProperty('typesUseViewActionInListings', 'ulearn.video\nVideo\nImage', 'lines')
    except:
        print("La propietat 'typesUseViewActionInListings' ja estava afegida al portal site_properties")

    import transaction
    transaction.commit()