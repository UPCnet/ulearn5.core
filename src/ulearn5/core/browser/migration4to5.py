# -*- coding: utf-8 -*-
from Acquisition import aq_inner
from base5.core.utilities import IElasticSearch
from base5.core.utils import json_response
from base5.portlets.browser.manager import IColStorage
from datetime import datetime
from five import grok
from mimetypes import MimeTypes
from plone import api
from plone.app.discussion.interfaces import IDiscussionSettings
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from plone.namedfile.file import NamedBlobImage
from plone.portlets.interfaces import IPortletAssignmentMapping
from plone.portlets.interfaces import IPortletManager
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces import ILanguageSchema
from Products.CMFPlone.interfaces import IPloneSiteRoot
from Products.CMFPlone.interfaces.constrains import ISelectableConstrainTypes
from Products.CMFPlone.interfaces.controlpanel import ISiteSchema
from Products.CMFPlone.interfaces.syndication import ISiteSyndicationSettings
from repoze.catalog.query import Eq
from souper.soup import get_soup
from ulearn5.core.api import api_resource
from ulearn5.core.browser.sharing import ElasticSharing
from ulearn5.core.browser.sharing import IElasticSharing
from ulearn5.core.content.community import ICommunity
from ulearn5.core.controlpanel import IUlearnControlPanelSettings
from ulearn5.core.gwuuid import ATTRIBUTE_NAME
from ulearn5.core.gwuuid import IGWUUID
from ulearn5.core.setuphandlers import setup_ulearn_portlets
from ulearn5.core.utils import is_activate_owncloud
from ulearn5.owncloud.utils import update_owncloud_permission
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.hooks import getSite
from zope.interface import alsoProvides
from zope.interface import Interface
from base5.core.utils import get_all_user_properties
from base5.core.utils import add_user_to_catalog

from plone.app.layout.navigation.root import getNavigationRootObject

from ulearn5.owncloud.api.owncloud import HTTPResponseError
from ulearn5.owncloud.api.owncloud import OCSResponseError
from ulearn5.owncloud.utilities import IOwncloudClient
from ulearn5.owncloud.utils import get_domain



import base64
import json
import logging
import os
import requests
import shutil
import subprocess
import time
import transaction


ATTRIBUTE_NAME_FAVORITE = '_favoritedBy'

# from ulearn5.core.api.people import Person

logger = logging.getLogger(__name__)


grok.templatedir("views_templates")


class migrationCommunities(grok.View):
    """ Aquesta vista migra comunitats de Plone 4 a la nova versió en Plone 5 """
    grok.name('migrationcommunities')
    grok.template('migrationcommunities')
    grok.context(IPloneSiteRoot)
    grok.require('cmf.ManagePortal')


    def update(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        if self.request.environ['REQUEST_METHOD'] == 'POST':
            hscope = 'widgetcli'
            pc = api.portal.get_tool('portal_catalog')
            communities = pc.searchResults(portal_type='ulearn.community')

            if self.request.form['url_instance_v4'] != '':
                url_instance_v4 = self.request.form['url_instance_v4']
                husernamev4 = self.request.form['husernamev4']
                htokenv4 = self.request.form['htokenv4']
                comunitats_no_migrar = self.request.form['comunitats_no_migrar']
                comunitats_a_migrar = self.request.form['comunitats_a_migrar']

                json_communities = requests.get(url_instance_v4 + '/api/communitiesmigration', headers={'X-Oauth-Username': husernamev4,'X-Oauth-Token': htokenv4, 'X-Oauth-Scope': hscope})
                logger.info('Buscant comunitats per migrar')
                communities = json.loads(json_communities.content)

                for community in communities:

                    if (community['id'] not in comunitats_no_migrar) and (community['id'] in comunitats_a_migrar or comunitats_a_migrar == ''):

                        logger.info('Migrant comunitat {}'.format(community['title'].encode('utf-8')))
                        result = pc.unrestrictedSearchResults(portal_type='ulearn.community', id=str(community['id']))


                        if result:
                            success_response = 'community already exists: ' + community['title']
                            status = 200
                        else:
                            # Creo la comunidad
                            imageObj = ''
                            if community['image']:
                                mime = MimeTypes()
                                mime_type = mime.guess_type(community['image'])
                                imgName = (community['image'].split('/')[-1]).decode('utf-8')
                                imgData = base64.decodestring(str(community['rawimage']))
                                imageObj = NamedBlobImage(data=imgData,
                                                          filename=imgName,
                                                          contentType=mime_type[0])

                            new_community_id = self.context.invokeFactory('ulearn.community', str(community['id']),
                                                                          title=community['title'],
                                                                          description=community['description'],
                                                                          image=imageObj,
                                                                          community_type=community['type'],
                                                                          activity_view=community['activity_view'],
                                                                          twitter_hashtag=community['twitter_hashtag'],
                                                                          notify_activity_via_push=community['notify_activity_via_push'],
                                                                          notify_activity_via_push_comments_too=community['notify_activity_via_push_comments_too'],
                                                                          checkConstraints=False)

                            # Modifico los datos de la comunidad
                            brain = pc.unrestrictedSearchResults(portal_type='ulearn.community', id=new_community_id)
                            if brain:
                                community_new = brain[0].getObject()

                                setattr(community_new, ATTRIBUTE_NAME_FAVORITE, set(eval(community['favoritedBy'])))
                                community_new.reindexObject(idxs=['favoritedBy'])

                                setattr(community_new, ATTRIBUTE_NAME, str(community['gwuuid']))
                                community_new.reindexObject(idxs=['gwuuid'])

                                community_new.listCreators = community['listCreators']
                                community_new.ModificationDate = community['ModificationDate']
                                community_new.created = community['CreationDate']
                                community_new.CreationDate = community['CreationDate']

                                community_new.is_shared = community['is_shared']
                                community_new.Creator = community['Creator']
                                community_new.UID = community['UID']

                                community_new.reindexObject()

                                # Migro los permisos del EDITACL

                                adapter = community_new.adapted()

                                # Ejemplo editacl
                                #community['editacl'] = {u'users': [{u'role': u'owner', u'displayName': u'Victor Fernandez', u'id': u'alberto.duran'}], u'groups': []}

                                # Change the uLearn part of the community

                                adapter.update_acl(community['editacl'])
                                acl = adapter.get_acl()
                                try:
                                    adapter.set_plone_permissions(acl)
                                except:
                                    if acl['groups'] == u'':
                                        acl['groups'] = []
                                        adapter.set_plone_permissions(acl)

                                # Communicate the change in the community subscription to the uLearnHub
                                # XXX: Until we do not have a proper Hub online
                                adapter.update_hub_subscriptions()

                                # If is activate owncloud modify permissions owncloud
                                if is_activate_owncloud(self.context):
                                    update_owncloud_permission(community_new, acl)

                            success_response = 'Created community: ' + community['title']

                        logger.info(success_response)

            logger.info('Ha finalitzat la migració de les comunitats.')

class migrationDocumentsCommunities(grok.View):
    """ Aquesta vista migra la carpeta Documents de les comunitats de Plone 4 a la nova versió en Plone 5 """
    grok.name('migrationdocumentscommunities')
    grok.template('migrationdocumentscommunities')
    grok.context(IPloneSiteRoot)
    grok.require('cmf.ManagePortal')


    def update(self):
        from plone.protect.interfaces import IDisableCSRFProtection
        alsoProvides(self.request, IDisableCSRFProtection)

        if self.request.environ['REQUEST_METHOD'] == 'POST':
            hscope = 'widgetcli'
            pc = api.portal.get_tool('portal_catalog')
            communities = pc.searchResults(portal_type='ulearn.community')

            if self.request.form['url_instance_v4'] != '':
                url_instance_v4 = self.request.form['url_instance_v4']
                husernamev4 = self.request.form['husernamev4']
                htokenv4 = self.request.form['htokenv4']
                url_instance_v5 = self.request.form['url_instance_v5']
                remote_username = self.request.form['remote_username']
                remote_password = self.request.form['remote_password']
                comunitats_no_migrar = self.request.form['comunitats_no_migrar']
                comunitats_a_migrar = self.request.form['comunitats_a_migrar']
                servidor_comunitats_V4 = self.request.form['servidor_comunitats_V4']
                # (p.e: ssh/jane_id_rsa) --> Este es para Comunitats Externs
                certificado_maquina_comunitats_V4 = self.request.form['certificado_maquina_comunitats_V4']
                # /var/plone/genweb.zope/var
                path_guardar_export_dexterity_comunitats_V4 = self.request.form['path_guardar_export_dexterity_comunitats_V4']
                # /Dades/plone/ulearn5.zope/var
                path_guardar_export_dexterity_comunitats_V5 = self.request.form['path_guardar_export_dexterity_comunitats_V5']

                json_communities = requests.get(url_instance_v4 + '/api/communitiesmigration', headers={'X-Oauth-Username': husernamev4,'X-Oauth-Token': htokenv4, 'X-Oauth-Scope': hscope})
                logger.info('Buscant comunitats per migrar')
                communities = json.loads(json_communities.content)
                for community in communities:
                    if (community['id'] not in comunitats_no_migrar) and (community['id'] in comunitats_a_migrar or comunitats_a_migrar == ''):
                        logger.info('Migrant comunitat {}'.format(community['title'].encode('utf-8')))

                        ############################# Migracio de la carpeta documents de la comunitat ############################################
                        result = requests.get(url_instance_v4 + '/' + community['id'] + '/documents/export_dexterity?dir=' + path_guardar_export_dexterity_comunitats_V4 + '/',
                                                headers={'X-Oauth-Username': husernamev4,'X-Oauth-Token': htokenv4, 'X-Oauth-Scope': hscope})
                        if not result.ok:
                            logger.info('Ha fallat export_dexterity als documents, REINTENTANT....')
                            time.sleep(10)
                            result = requests.get(url_instance_v4 + '/' + community['id'] + '/documents/export_dexterity?dir=' + path_guardar_export_dexterity_comunitats_V4 + '/',
                                                    headers={'X-Oauth-Username': husernamev4,'X-Oauth-Token': htokenv4, 'X-Oauth-Scope': hscope})

                        if result.ok:
                            shutil.rmtree(path_guardar_export_dexterity_comunitats_V5 + '/content')

                            cmd = 'scp -i ' + certificado_maquina_comunitats_V4 + ' -r root@' + servidor_comunitats_V4 + ':' + path_guardar_export_dexterity_comunitats_V4 + '/content'  + ' ' + path_guardar_export_dexterity_comunitats_V5
                            subprocess.Popen([cmd], shell=True).wait()
                            migrat = requests.get(url_instance_v5 + '/' + community['id'] + '/documents/comunitats_import', auth=(remote_username, remote_password))
                            if migrat.ok:
                                logger.info('He migrat la carpeta documents de: ' + community['title'].encode('utf-8'))
                            else:
                                logger.error('NO he migrat la carpeta documents de: ' + community['title'].encode('utf-8'))

                        ############################# Migracio de la carpeta esdeveniments de la comunitat ############################################
                        result = requests.get(url_instance_v4 + '/' + community['id'] + '/events/export_dexterity?dir=' + path_guardar_export_dexterity_comunitats_V4 + '/',
                                                headers={'X-Oauth-Username': husernamev4,'X-Oauth-Token': htokenv4, 'X-Oauth-Scope': hscope})
                        if not result.ok:
                            logger.info('Ha fallat export_dexterity als esdeveniments, REINTENTANT....')
                            time.sleep(10)
                            result = requests.get(url_instance_v4 + '/' + community['id'] + '/events/export_dexterity?dir=' + path_guardar_export_dexterity_comunitats_V4 + '/',
                                                    headers={'X-Oauth-Username': husernamev4,'X-Oauth-Token': htokenv4, 'X-Oauth-Scope': hscope})

                        if result.ok:
                            shutil.rmtree(path_guardar_export_dexterity_comunitats_V5 + '/content')

                            cmd = 'scp -i ' + certificado_maquina_comunitats_V4 + ' -r root@' + servidor_comunitats_V4 + ':' + path_guardar_export_dexterity_comunitats_V4 + '/content'  + ' ' + path_guardar_export_dexterity_comunitats_V5
                            subprocess.Popen([cmd], shell=True).wait()
                            migrat = requests.get(url_instance_v5 + '/' + community['id'] + '/events/comunitats_import', auth=(remote_username, remote_password))
                            if migrat.ok:
                                logger.info('He migrat la carpeta esdeveniments de: ' + community['title'].encode('utf-8'))
                            else:
                                logger.error('NO he migrat la carpeta esdeveniments de: ' + community['title'].encode('utf-8'))
                logger.info('Ha finalitzat la migració de les comunitats.')


class migrationPath(grok.View):
    """ Aquesta vista migra el contingut del path indicat de Plone 4 a la nova versió en Plone 5 """
    grok.name('migrationpath')
    grok.template('migrationpath')
    grok.context(IPloneSiteRoot)
    grok.require('cmf.ManagePortal')


    def update(self):
        from plone.protect.interfaces import IDisableCSRFProtection
        alsoProvides(self.request, IDisableCSRFProtection)

        if self.request.environ['REQUEST_METHOD'] == 'POST':
            hscope = 'widgetcli'

            if self.request.form['url_instance_v4'] != '':
                url_instance_v4 = self.request.form['url_instance_v4']
                husernamev4 = self.request.form['husernamev4']
                htokenv4 = self.request.form['htokenv4']
                url_instance_v5 = self.request.form['url_instance_v5']
                remote_username = self.request.form['remote_username']
                remote_password = self.request.form['remote_password']
                path_a_migrar = self.request.form['path_a_migrar']
                servidor_comunitats_V4 = self.request.form['servidor_comunitats_V4']
                # (p.e: ssh/jane_id_rsa) --> Este es para Comunitats Externs
                certificado_maquina_comunitats_V4 = self.request.form['certificado_maquina_comunitats_V4']
                # /var/plone/genweb.zope/var
                path_guardar_export_dexterity_comunitats_V4 = self.request.form['path_guardar_export_dexterity_comunitats_V4']
                # /Dades/plone/ulearn5.zope/var
                path_guardar_export_dexterity_comunitats_V5 = self.request.form['path_guardar_export_dexterity_comunitats_V5']

                logger.info('Migrant path {}'.format(path_a_migrar))

                ############################# Migracio del path ###################################################
                result = requests.get(url_instance_v4 + '/' + path_a_migrar + '/export_dexterity?dir=' + path_guardar_export_dexterity_comunitats_V4 + '/',
                                        headers={'X-Oauth-Username': husernamev4,'X-Oauth-Token': htokenv4, 'X-Oauth-Scope': hscope})
                if not result.ok:
                    logger.info('Ha fallat export_dexterity del path, REINTENTANT....')
                    time.sleep(10)
                    result = requests.get(url_instance_v4 + '/' + path_a_migrar + '/export_dexterity?dir=' + path_guardar_export_dexterity_comunitats_V4 + '/',
                                            headers={'X-Oauth-Username': husernamev4,'X-Oauth-Token': htokenv4, 'X-Oauth-Scope': hscope})

                if result.ok:
                    shutil.rmtree(path_guardar_export_dexterity_comunitats_V5 + '/content')

                    #produccion
                    #cmd = 'scp -i ' + certificado_maquina_comunitats_V4 + ' -r root@' + servidor_comunitats_V4 + ':' + path_guardar_export_dexterity_comunitats_V4 + '/content'  + ' ' + path_guardar_export_dexterity_comunitats_V5

                    #pre
                    cmd = 'scp -r root@' + servidor_comunitats_V4 + ':' + path_guardar_export_dexterity_comunitats_V4 + '/content'  + ' ' + path_guardar_export_dexterity_comunitats_V5

                    #local
                    #cmd = 'scp -r ' + path_guardar_export_dexterity_comunitats_V4 + '/content'  + ' ' + path_guardar_export_dexterity_comunitats_V5
                    subprocess.Popen([cmd], shell=True).wait()
                    migrat = requests.get(url_instance_v5 + '/comunitats_import', auth=(remote_username, remote_password))
                    if migrat.ok:
                        logger.info('He migrat el path: ' + path_a_migrar)
                    else:
                        logger.error('NO he migrat el path: ' + path_a_migrar)

                logger.info('Ha finalitzat la migració del path.')


class migrationPortalRoleManager(grok.View):
    """ Aquesta vista migra els permisos del site portal-role-manager de Plone 4 a la nova versió en Plone 5 """
    grok.name('migrationportalrolemanager')
    grok.template('migrationportalrolemanager')
    grok.context(IPloneSiteRoot)
    grok.require('cmf.ManagePortal')


    def update(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        if self.request.environ['REQUEST_METHOD'] == 'POST':
            hscope = 'widgetcli'

            if self.request.form['url_instance_v4'] != '':
                url_instance_v4 = self.request.form['url_instance_v4']
                husernamev4 = self.request.form['husernamev4']
                htokenv4 = self.request.form['htokenv4']

                json_permission = requests.get(url_instance_v4 + '/api/portalrolemanagermigration', headers={'X-Oauth-Username': husernamev4,'X-Oauth-Token': htokenv4, 'X-Oauth-Scope': hscope})
                logger.info('Buscant els permissos del portal-role-manager per migrar')
                permissions = json.loads(json_permission.content)

                portal = api.portal.get()
                role_manager = portal.acl_users.portal_role_manager

                for permission in permissions:
                    if permission['users_assigned'] != []:
                        for user in permission['users_assigned']:
                            role_add = role_manager.assignRoleToPrincipal(permission['role_id'],  user[0])
                            if role_add:
                                logger.info('Afegit al rol: ' + permission['role_id'] + ' - usuari: ' + user[0])

                logger.info('Ha finalitzat la migració del portal-role-manager.')

class migrationEditaclCommunities(grok.View):
    """ Aquesta vista migra els permisos del editacl de les comunitats de Plone 4 a la nova versió en Plone 5 """
    grok.name('migrationeditaclcommunities')
    grok.template('migrationeditaclcommunities')
    grok.context(IPloneSiteRoot)
    grok.require('cmf.ManagePortal')


    def update(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        if self.request.environ['REQUEST_METHOD'] == 'POST':
            hscope = 'widgetcli'
            pc = api.portal.get_tool('portal_catalog')
            communities = pc.searchResults(portal_type='ulearn.community')

            if self.request.form['url_instance_v4'] != '':
                url_instance_v4 = self.request.form['url_instance_v4']
                husernamev4 = self.request.form['husernamev4']
                htokenv4 = self.request.form['htokenv4']
                comunitats_no_migrar = self.request.form['comunitats_no_migrar']
                comunitats_a_migrar = self.request.form['comunitats_a_migrar']

                json_communities = requests.get(url_instance_v4 + '/api/communitiesmigration', headers={'X-Oauth-Username': husernamev4,'X-Oauth-Token': htokenv4, 'X-Oauth-Scope': hscope})
                logger.info('Buscant comunitats per migrar els permisos del editacl')
                communities = json.loads(json_communities.content)

                for community in communities:

                    if (community['id'] not in comunitats_no_migrar) and (community['id'] in comunitats_a_migrar or comunitats_a_migrar == ''):

                        brain = pc.unrestrictedSearchResults(portal_type='ulearn.community', id=str(community['id']))
                        if brain:
                            community_new = brain[0].getObject()
                            adapter = community_new.adapted()

                            # Ejemplo editacl
                            #community['editacl'] = {u'users': [{u'role': u'owner', u'displayName': u'Victor Fernandez', u'id': u'alberto.duran'}], u'groups': []}

                            # Change the uLearn part of the community

                            adapter.update_acl(community['editacl'])
                            acl = adapter.get_acl()
                            adapter.set_plone_permissions(acl)

                            # Communicate the change in the community subscription to the uLearnHub
                            # XXX: Until we do not have a proper Hub online
                            adapter.update_hub_subscriptions()

                            # If is activate owncloud modify permissions owncloud
                            if is_activate_owncloud(self.context):
                                update_owncloud_permission(community_new, acl)

                            success_response = 'Migrat editacl comunitat: ' + community['title']
                            logger.info(success_response)

            logger.info('Ha finalitzat la migració del editacl de les comunitats.')

class migrationUsersProfiles(grok.View):
    """ Aquesta vista migra les properties dels usuaris de Plone 4 a la nova versió en Plone 5 i ho afegeix al soup de Plone 5"""
    grok.name('migrationusersprofile')
    grok.template('migrationusersprofile')
    grok.context(IPloneSiteRoot)
    grok.require('cmf.ManagePortal')


    def update(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        if self.request.environ['REQUEST_METHOD'] == 'POST':
            hscope = 'widgetcli'

            if self.request.form['url_instance_v4'] != '':
                url_instance_v4 = self.request.form['url_instance_v4']
                husernamev4 = self.request.form['husernamev4']
                htokenv4 = self.request.form['htokenv4']

                json_users = requests.get(url_instance_v4 + '/api/userspropertiesmigration', headers={'X-Oauth-Username': husernamev4,'X-Oauth-Token': htokenv4, 'X-Oauth-Scope': hscope})
                logger.info('Buscant users per migrar')
                users = json.loads(json_users.content)

                for user in users:
                    try:
                        existing_user = api.user.get(user['id'])
                        existing_user.setMemberProperties(user['properties'])
                        #properties = get_all_user_properties(existing_user)
                        add_user_to_catalog(existing_user, user['properties'], overwrite=True)
                        logger.info('Usuari migrat: ' + user['id'])
                    except:
                        logger.error('Usuari NO migrat: ' + user['id'])


        logger.info('Ha finalitzat la migració dels usuaris.')

