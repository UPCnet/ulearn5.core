# -*- coding: utf-8 -*-
from Products.CMFPlone.interfaces import INonInstallable
from zope.interface import implementer
from plone import api
from zope.interface import alsoProvides
from zope.component import queryUtility
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component.hooks import getSite
from plone.registry.interfaces import IRegistry
from plone.dexterity.utils import createContentInContainer
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletAssignmentMapping
from plone.portlets.utils import registerPortletType, unregisterPortletType

from Products.CMFCore.utils import getToolByName

# from base5.core.browser.interfaces import IHomePage
from ulearn5.core.controlpanel import IUlearnControlPanelSettings
from ulearn5.core.controlportlets import IPortletsSettings

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


def setup_safe_html_transform():
    transforms = api.portal.get_tool('portal_transforms')
    transform = getattr(transforms, 'safe_html')

    valid = transform.get_parameter_value('valid_tags')
    nasty = transform.get_parameter_value('nasty_tags')
    stripped = transform.get_parameter_value('stripped_attributes')

    # uLearn nasty tags
    ulearn_nasty = ['script', 'applet', 'iframe']
    for tag in ulearn_nasty:
        if tag in valid:
            # Delete from valid
            valid[tag] = 0
            del valid[tag]
        # Add to nasty
        if tag not in nasty:
            nasty[tag] = 1

    current_style_whitelist = [a for a in transform.get_parameter_value('style_whitelist')]
    current_style_whitelist.append('color')

    kwargs = {}
    kwargs['valid_tags'] = valid
    kwargs['nasty_tags'] = nasty
    kwargs['stripped_attributes'] = stripped
    kwargs['style_whitelist'] = current_style_whitelist
    for k in list(kwargs):
        if isinstance(kwargs[k], dict):
            v = kwargs[k]
            kwargs[k + '_key'] = v.keys()
            kwargs[k + '_value'] = [str(s) for s in v.values()]
            del kwargs[k]

    transform.set_parameters(**kwargs)
    transform._p_changed = True
    transform.reload()


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


# def setup_ulearn_portlets_settings():
#     registry = queryUtility(IRegistry)
#     ulearn_settings = registry.forInterface(IPortletsSettings)
#     site = getSite()
#
#     activate_portlets = []
#     portlets_slots = ["plone.leftcolumn", "plone.rightcolumn",
#                  "ContentWellPortlets.AbovePortletManager1", "ContentWellPortlets.AbovePortletManager2",
#                  "ContentWellPortlets.AbovePortletManager3", "ContentWellPortlets.BelowPortletManager1",
#                  "ContentWellPortlets.BelowPortletManager2", "ContentWellPortlets.BelowPortletManager3",
#                  "ContentWellPortlets.BelowTitlePortletManager1", "ContentWellPortlets.BelowTitlePortletManager2",
#                  "ContentWellPortlets.BelowTitlePortletManager3"]
#
#     for manager_name in portlets_slots:
#         if 'ContentWellPortlets' in manager_name:
#             manager = getUtility(IPortletManager, name=manager_name, context=site['front-page'])
#             mapping = getMultiAdapter((site['front-page'], manager), IPortletAssignmentMapping)
#             [activate_portlets.append(item[0]) for item in mapping.items()]
#         else:
#             manager = getUtility(IPortletManager, name=manager_name, context=site)
#             mapping = getMultiAdapter((site, manager), IPortletAssignmentMapping)
#
#             [activate_portlets.append(item[0]) for item in mapping.items()]
#
#     portlets = [port for port in ulearn_settings.__registry__.records.items() if 'portlet' in port[0]]
#     if portlets:
#         for portlet, reg in portlets:
#             portlet = portlet.split('.')[-1]
#             idPortlet = portlet.replace('_', '.')
#             namePortlet = portlet.replace('_', ' ')
#
#
#             if reg.value is True:
#                 registerPortletType(site,
#                                     title=namePortlet,
#                                     description=namePortlet,
#                                     addview=idPortlet)
#
#             if idPortlet.split('.')[-1] in activate_portlets:
#                 reg.value = True
#                 registerPortletType(site,
#                                     title=namePortlet,
#                                     description=namePortlet,
#                                     addview=idPortlet)
#
#             if reg.value is False:
#                 unregisterPortletType(site, idPortlet)


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
    setup_safe_html_transform()
    setup_ulearn_icon_set()
    #setup_ulearn_portlets_settings()

    # Fix the DXCT site and add permission to the default page which the
    # portlets are defined to, failing to do so turns in the users can't see the
    # home page - Taken from 'setupdxctsite' view in genweb.core
    pl = getToolByName(portal, 'portal_languages')
    # from plone.dexterity.interfaces import IDexterityContent
    # front_page = getattr(portal, 'front-page', False)
    # if front_page and not IDexterityContent.providedBy(front_page):
    #     portal.manage_delObjects('front-page')
    #     frontpage = createContentInContainer(portal, 'Document', title=u"front-page", checkConstraints=False)
    #     alsoProvides(frontpage, IHomePage)
    #     frontpage.exclude_from_nav = True
    #     frontpage.language = pl.getDefaultLanguage()
    #     frontpage.reindexObject()
    #     logger.info('DX default content site setup successfully.')
    # elif not front_page:
    #     frontpage = createContentInContainer(portal, 'Document', title=u'front-page', checkConstraints=False)
    #     alsoProvides(frontpage, IHomePage)
    #     frontpage.exclude_from_nav = True
    #     frontpage.language = pl.getDefaultLanguage()
    #     frontpage.reindexObject()
    #     logger.info('DX default content site setup successfully.')
    # else:
    #     alsoProvides(front_page, IHomePage)
    #     front_page.language = pl.getDefaultLanguage()
    #     front_page.reindexObject()

    # Set the default page to the homepage view
    portal.setDefaultPage('homepage')

    # Allow connected users to view the homepage by allowing them either on
    # Plone site and in the front-page (HomePortlets placeholder)
    portal.manage_setLocalRoles('AuthenticatedUsers', ['Reader'])
    portal['front-page'].manage_setLocalRoles('AuthenticatedUsers', ['Reader'])

    # Set mailhost
    mh = getToolByName(portal, 'MailHost')
    mh.smtp_host = 'localhost'
    portal.email_from_name = 'uLearn Administrator'
    portal.email_from_address = 'no-reply@upcnet.es'

    # Delete original 'Events' folder for not to colision with the community ones
    if getattr(portal, 'events', False):
        portal.manage_delObjects('events')

    # Recall the last language set for this instance in case of reinstall
    registry = queryUtility(IRegistry)
    settings = registry.forInterface(IUlearnControlPanelSettings)

    pl = getToolByName(portal, 'portal_languages')
    pl.setDefaultLanguage(settings.language)
    pl.supported_langs = [settings.language, ]

    # Add portlets programatically as it seems that there is some bug in the
    # portlets.xml GS when reinstalling the right column
    portal = getSite()
    target_manager = queryUtility(IPortletManager, name='plone.rightcolumn', context=portal)
    target_manager_assignments = getMultiAdapter((portal, target_manager), IPortletAssignmentMapping)

    if 'calendar' not in target_manager_assignments.keys() or \
       'stats' not in target_manager_assignments.keys():
        # purge existing portlets
        for portlet in target_manager_assignments.keys():
            del target_manager_assignments[portlet]

        from ulearn5.core.theme.portlets.calendar import Assignment as calendarAssignment
        from ulearn5.theme.portlets.stats import Assignment as statsAssignment
        # from ulearn.theme.portlets.econnect import Assignment as econnectAssignment

        target_manager_assignments['calendar'] = calendarAssignment()
        target_manager_assignments['stats'] = statsAssignment()
        # target_manager_assignments['econnect'] = econnectAssignment()

    # Set default TimeZone (p.a.event)
    api.portal.set_registry_record('plone.app.event.portal_timezone', 'Europe/Madrid')
    api.portal.set_registry_record('plone.app.event.first_weekday', 0)

    # Unset validate e-mail as we want the users to be created right the way
    portal.validate_email = False

    # Update types with default action listing
    site_properties = api.portal.get_tool(name='portal_properties').site_properties
    site_properties.typesUseViewActionInListings = site_properties.typesUseViewActionInListings + ('ulearn.video',)

    transaction.commit()
