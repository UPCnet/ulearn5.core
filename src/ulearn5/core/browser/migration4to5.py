import logging
import json
import base64
import requests

from mimetypes import MimeTypes

from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName

from plone import api
from plone.namedfile.file import NamedBlobImage
from zope.interface import alsoProvides
from plone.protect.interfaces import IDisableCSRFProtection

from Products.CMFPlone.interfaces import IPloneSiteRoot
from zope.component import getMultiAdapter
from base5.core.utils import add_user_to_catalog
from ulearn5.core.utils import byteify

# Define tus atributos constantes aquí si no están importados
ATTRIBUTE_NAME = 'gwuuid'
ATTRIBUTE_NAME_FAVORITE = 'favoritedBy'

logger = logging.getLogger(__name__)


class MigrationCommunitiesView(BrowserView):
    """ Vista para migrar comunidades desde Plone 4 a Plone 5 """

    def __call__(self):
        self.request.set('disable_border', True)
        self.update()
        return self.index()

    def update(self):
        try:
            alsoProvides(self.request, IDisableCSRFProtection)
        except Exception:
            pass

        if self.request.environ.get('REQUEST_METHOD') == 'POST':
            hscope = 'widgetcli'
            pc = api.portal.get_tool('portal_catalog')

            if self.request.form.get('url_instance_v4'):
                url_instance_v4 = self.request.form.get('url_instance_v4')
                husernamev4 = self.request.form.get('husernamev4')
                htokenv4 = self.request.form.get('htokenv4')
                comunitats_no_migrar = self.request.form.get('comunitats_no_migrar', '')
                comunitats_a_migrar = self.request.form.get('comunitats_a_migrar', '')

                comunitats_no_migrar = comunitats_no_migrar.splitlines()
                comunitats_a_migrar = comunitats_a_migrar.splitlines()

                headers = {
                    'X-Oauth-Username': husernamev4,
                    'X-Oauth-Token': htokenv4,
                    'X-Oauth-Scope': hscope
                }

                # response = requests.get("{url_instance_v4}/api/communitiesmigration", headers=headers)
                logger.info('Buscant comunitats per migrar')
                # communities = json.loads(response.content)
                response = '[\n  {\n    "CreationDate": "2024-09-12T07:08:35+02:00", \n    "Creator": "jmbernat", \n    "ModificationDate": "2024-09-18T13:13:42+02:00", \n    "UID": "6969fba512c1427b909c6a2825f695d4", \n    "activity_view": "Darreres activitats", \n    "community_hash": "86dc4064452e7c44c0cc273b05c40fe54199ce09", \n    "description": "", \n    "editacl": {\n      "groups": [], \n      "users": [\n        {\n          "displayName": "Josep Bernat", \n          "id": "jmbernat", \n          "role": "owner"\n        }, \n        {\n          "displayName": "Rosa Mart\\u00ed de la Morena", \n          "id": "43442877v", \n          "role": "writer"\n        }, \n        {\n          "displayName": "Josep Bernat Berenguer", \n          "id": "78096118d", \n          "role": "reader"\n        }, \n        {\n          "displayName": "Ulearn User1", \n          "id": "ulearn.user1", \n          "role": "owner"\n        }, \n        {\n          "displayName": "M\\u00f2nica Mart\\u00ednez Galante", \n          "id": "47617759p", \n          "role": "writer"\n        }\n      ]\n    }, \n    "favoritedBy": "set([\'78096118d\', \'jmbernat\', \'47617759p\', \'ulearn.user1\'])", \n    "gwuuid": "413d4a72b7d14854bb240f032e4011b6", \n    "id": "comunicacio", \n    "image": false, \n    "is_shared": false, \n    "listCreators": [\n      "jmbernat"\n    ], \n    "notify_activity_via_push": false, \n    "notify_activity_via_push_comments_too": false, \n    "rawimage": "", \n    "title": "Comunicaci\\u00f3", \n    "twitter_hashtag": null, \n    "type": "Open", \n    "url": "http://shaylapre:11098/7/apdcat/comunicacio"\n  }, \n  {\n    "CreationDate": "2025-01-29T08:56:15+01:00", \n    "Creator": "78096118d", \n    "ModificationDate": "2025-01-29T08:56:17+01:00", \n    "UID": "8ebecb33f7404792a40a454fa01bc096", \n    "activity_view": "Darreres activitats", \n    "community_hash": "bbc27a95217838fe717f5a355ee73bbf0fcb8d05", \n    "description": "", \n    "editacl": {\n      "groups": [], \n      "users": [\n        {\n          "displayName": "Josep Bernat Berenguer", \n          "id": "78096118d", \n          "role": "owner"\n        }, \n        {\n          "displayName": "Ulearn User1", \n          "id": "ulearn.user1", \n          "role": "reader"\n        }\n      ]\n    }, \n    "favoritedBy": "set([\'78096118d\'])", \n    "gwuuid": "82a81b5fe936454ba57606ab13a17a70", \n    "id": "apdcat", \n    "image": false, \n    "is_shared": false, \n    "listCreators": [\n      "78096118d"\n    ], \n    "notify_activity_via_push": false, \n    "notify_activity_via_push_comments_too": false, \n    "rawimage": "", \n    "title": "APDCAT", \n    "twitter_hashtag": null, \n    "type": "Open", \n    "url": "http://shaylapre:11098/7/apdcat/apdcat"\n  }, \n  {\n    "CreationDate": "2024-12-09T13:30:56+01:00", \n    "Creator": "jmbernat", \n    "ModificationDate": "2025-03-28T14:08:31+01:00", \n    "UID": "01cb8f71701e499da6adb4952c8e153c", \n    "activity_view": "Darreres activitats", \n    "community_hash": "2895d9efab03528b280861f028c57576a36edb33", \n    "description": "", \n    "editacl": {\n      "groups": "", \n      "users": [\n        {\n          "id": "jmbernat", \n          "role": "owner"\n        }, \n        {\n          "displayName": "", \n          "id": "78096118d", \n          "role": "writer"\n        }\n      ]\n    }, \n    "favoritedBy": "set([\'78096118d\', \'jmbernat\'])", \n    "gwuuid": "73ff47d2361a49709f4fb0c6b7ebfe29", \n    "id": "gestio-economica", \n    "image": false, \n    "is_shared": false, \n    "listCreators": [\n      "jmbernat"\n    ], \n    "notify_activity_via_push": false, \n    "notify_activity_via_push_comments_too": false, \n    "rawimage": "", \n    "title": "Gesti\\u00f3 Econ\\u00f2mica", \n    "twitter_hashtag": null, \n    "type": "Open", \n    "url": "http://shaylapre:11098/7/apdcat/gestio-economica"\n  }, \n  {\n    "CreationDate": "2024-10-25T15:44:50+01:00", \n    "Creator": "jmbernat", \n    "ModificationDate": "2025-03-28T14:16:14+01:00", \n    "UID": "bc350e582bb0441a8a5887d2fa094dcf", \n    "activity_view": "Darreres activitats", \n    "community_hash": "559e016f4d535d279e3d8734c7adcb0dcbdf68bb", \n    "description": "", \n    "editacl": {\n      "groups": [], \n      "users": [\n        {\n          "displayName": "Josep Bernat", \n          "id": "jmbernat", \n          "role": "owner"\n        }, \n        {\n          "displayName": "Xavier Urios Aparisi", \n          "id": "35101362g", \n          "role": "reader"\n        }, \n        {\n          "displayName": "", \n          "id": "78096118d", \n          "role": "writer"\n        }\n      ]\n    }, \n    "favoritedBy": "set([\'78096118d\', \'jmbernat\'])", \n    "gwuuid": "cef806ca83b34b89a6fa73b56c409941", \n    "id": "assessoria-juridica", \n    "image": false, \n    "is_shared": false, \n    "listCreators": [\n      "jmbernat"\n    ], \n    "notify_activity_via_push": false, \n    "notify_activity_via_push_comments_too": false, \n    "rawimage": "", \n    "title": "Assessoria Jur\\u00eddica", \n    "twitter_hashtag": null, \n    "type": "Open", \n    "url": "http://shaylapre:11098/7/apdcat/assessoria-juridica"\n  }, \n  {\n    "CreationDate": "2024-09-20T11:22:46+01:00", \n    "Creator": "jmbernat", \n    "ModificationDate": "2024-10-02T12:23:20+01:00", \n    "UID": "6e67542ad8764493a33b0e1cb89a7719", \n    "activity_view": "Darreres activitats", \n    "community_hash": "db0d1ee03bd5b8536e3f0311d091944ac8dd62fe", \n    "description": "", \n    "editacl": {\n      "groups": [\n        {\n          "id": "APDCAT", \n          "role": "reader"\n        }\n      ], \n      "users": [\n        {\n          "displayName": "Josep Bernat", \n          "id": "jmbernat", \n          "role": "owner"\n        }, \n        {\n          "displayName": "Xavier Mar\\u00edn V\\u00edlchez", \n          "id": "38147193z", \n          "role": "owner"\n        }, \n        {\n          "displayName": "Ulearn User1", \n          "id": "ulearn.user1", \n          "role": "owner"\n        }, \n        {\n          "displayName": "josep test", \n          "id": "joseptest", \n          "role": "reader"\n        }\n      ]\n    }, \n    "favoritedBy": "set([\'ulearn.user1\', \'jmbernat\', \'78096118d\'])", \n    "gwuuid": "f22fc39aba62427abd4a6164140f5a9c", \n    "id": "gestio-de-persones", \n    "image": false, \n    "is_shared": false, \n    "listCreators": [\n      "jmbernat"\n    ], \n    "notify_activity_via_push": false, \n    "notify_activity_via_push_comments_too": false, \n    "rawimage": "", \n    "title": "Gesti\\u00f3 de Persones", \n    "twitter_hashtag": null, \n    "type": "Closed", \n    "url": "http://shaylapre:11098/7/apdcat/gestio-de-persones"\n  }, \n  {\n    "CreationDate": "2024-10-28T13:37:53+01:00", \n    "Creator": "ulearn.user1", \n    "ModificationDate": "2024-10-28T13:37:55+01:00", \n    "UID": "fe5b3eb3e7bd47b2a9eb59b77a7d8451", \n    "activity_view": "Darreres activitats", \n    "community_hash": "3ff5f8240577c998e49862f34f06619df4a1d274", \n    "description": "", \n    "editacl": {\n      "groups": "", \n      "users": [\n        {\n          "id": "ulearn.user1", \n          "role": "owner"\n        }\n      ]\n    }, \n    "favoritedBy": "set([\'ulearn.user1\'])", \n    "gwuuid": "54a26085d0e04fd5a7aa646f40f6e9a2", \n    "id": "proves", \n    "image": false, \n    "is_shared": false, \n    "listCreators": [\n      "ulearn.user1"\n    ], \n    "notify_activity_via_push": false, \n    "notify_activity_via_push_comments_too": false, \n    "rawimage": "", \n    "title": "Proves", \n    "twitter_hashtag": null, \n    "type": "Organizative", \n    "url": "http://shaylapre:11098/7/apdcat/proves"\n  }\n]'
                communities = json.loads(response)

                for community in communities:
                    if (community['id'] not in comunitats_no_migrar) and (
                        community['id'] in comunitats_a_migrar or not comunitats_a_migrar
                    ):
                        logger.info('Migrant comunitat {}'.format(community['title']))
                        result = pc.unrestrictedSearchResults(
                            portal_type='ulearn.community', id=str(community['id'])
                        )

                        if result:
                            logger.info('Community already exists: {}'.format(community['title']))
                            continue

                        # Crear imagen si existe
                        imageObj = None
                        if community.get('image'):
                            mime = MimeTypes()
                            mime_type = mime.guess_type(community['image'])[0]
                            imgName = community['image'].split('/')[-1]
                            imgData = base64.b64decode(community['rawimage'])
                            imageObj = NamedBlobImage(
                                data=imgData,
                                filename=imgName,
                                contentType=mime_type
                            )

                        new_community_id = self.context.invokeFactory(
                            'ulearn.community',
                            id=str(community['id']),
                            title=community['title'],
                            description=community['description'],
                            image=imageObj,
                            community_type=community['type'],
                            activity_view=community['activity_view'],
                            twitter_hashtag=community['twitter_hashtag'],
                            notify_activity_via_push=community['notify_activity_via_push'],
                            notify_activity_via_push_comments_too=community['notify_activity_via_push_comments_too'],
                            checkConstraints=False
                        )

                        brain = pc.unrestrictedSearchResults(
                            portal_type='ulearn.community', id=new_community_id
                        )

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

                            # Permisos ACL
                            adapter = community_new.adapted()
                            adapter.update_acl(community['editacl'])
                            acl = adapter.get_acl()

                            try:
                                adapter.set_plone_permissions(acl)
                            except Exception:
                                if acl.get('groups') == u'':
                                    acl['groups'] = []
                                    adapter.set_plone_permissions(acl)

                            adapter.update_hub_subscriptions()

                            logger.info('Created community: {}'.format(community['title']))

                logger.info('Ha finalitzat la migració de les comunitats.')


class MigrationUsersProfiles(BrowserView):
    """ Aquesta vista migra les properties dels usuaris de Plone 4 a la nova versió en Plone 5 i ho afegeix al soup de Plone 5"""

    def __call__(self):
        self.request.set('disable_border', True)
        self.update()
        return self.index()

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
                json_users = requests.get(url_instance_v4 + '/api/userspropertiesmigration', headers={'X-Oauth-Username': husernamev4, 'X-Oauth-Token': htokenv4, 'X-Oauth-Scope': hscope})
                logger.info('Buscant users per migrar')
                users = json.loads(json_users.content)

                for user in users:
                    try:
                        existing_user = api.user.get(user['id'])
                        existing_user.setMemberProperties(user['properties'])
                        # properties = get_all_user_properties(existing_user)
                        add_user_to_catalog(existing_user, user['properties'], overwrite=True)
                        logger.info('Usuari migrat: ' + user['id'])
                    except:
                        logger.error('Usuari NO migrat: ' + user['id'])

        logger.info('Ha finalitzat la migració dels usuaris.')

class MigrationUsersProfilesSoup(BrowserView):
    """ Aquesta vista migra les properties dels usuaris de Plone 4 que estan en el soup a la nova versió en Plone 5 i ho afegeix al soup de Plone 5"""

    def __call__(self):
        self.request.set('disable_border', True)
        self.update()
        return self.index()

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

                json_users = requests.get(url_instance_v4 + '/api/userspropertiesmigrationsoup', headers={'X-Oauth-Username': husernamev4, 'X-Oauth-Token': htokenv4, 'X-Oauth-Scope': hscope})
                logger.info('Buscant users per migrar')
                users_json = json.loads(json_users.content)
                users = byteify(users_json)

                for user in users:
                    try:
                        existing_user = api.user.get(user['id'])
                        existing_user.setMemberProperties(user['properties'])
                        # properties = get_all_user_properties(existing_user)
                        add_user_to_catalog(existing_user, user['properties'], overwrite=True)
                        logger.info('Usuari migrat: ' + user['id'])
                    except:
                        logger.error('Usuari NO migrat: ' + user['id'])

        logger.info('Ha finalitzat la migració dels usuaris.')