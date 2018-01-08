# -*- coding: utf-8 -*-
from five import grok
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.hooks import getSite
from zope.interface import Interface

from Products.CMFCore.utils import getToolByName
from plone import api
from plone.dexterity.interfaces import IDexterityContent
from plone.indexer import indexer

from ulearn5.core.interfaces import IUlearn5CoreLayer

from Products.Archetypes.interfaces import IBaseObject
from base5.core.utilities import IElasticSearch
from ulearn5.core.gwuuid import IGWUUID

import json
import re
import uuid


class IElasticSharing(Interface):
    """ Marker for ElasticSharing global utility """


class ElasticSharing(object):
    """
    The records that will be stored to represent sharing on ES will
    represent shared permissions over an object, storing the
    following attributes:
        principal: The id of the user or group
        path: Path to the object relative to portal root
        roles: Roles assigned to the principal on this object
        uuid: Unique ID of the community where this object belongs
    """
    grok.implements(IElasticSharing)

    def __init__(self):
        try:
            self.elastic = getUtility(IElasticSearch)
        except:
            pass
        self._root_path = None

    @property
    def site_root_path(self):
        if self._root_path is None:
            site = getSite()
            self._root_path = '/'.join(site.getPhysicalPath())

        return self._root_path

    def relative_path(self, object):
        absolute_path = '/'.join(object.getPhysicalPath())
        return re.sub(r'^{}'.format(self.site_root_path), r'', absolute_path)

    def object_local_roles(self, object):
        """ Remap local roles to exclude Owner roles """
        current_local_roles = {}
        for principal, roles in object.__ac_local_roles__.items():
            effective_roles = [role for role in roles if role not in ['Owner']]
            if effective_roles:
                current_local_roles[principal] = effective_roles
        return current_local_roles

    def get_index_name(self):
        """
            We want to have an index name of the form of:
            security.<name_of_the_instance>.<epoch_time_of_instance_creation>
            e.g
                security.plone.1448983804

            to ensure unique index names.
        """
        portal = api.portal.get()
        portal_path = '_'.join([a for a in portal.getPhysicalPath() if a])
        portal_created = int(portal.created())
        return 'security.{}.{}'.format(portal_path, portal_created)

    def make_record(self, object, principal):
        """
            Constructs a record based on <object> properties, suitable
            to be inserted on ES
        """
        path = self.relative_path(object)

        record = dict(
            index=self.get_index_name(),
            doc_type='sharing',
            id=str(uuid.uuid1()),
            body=dict(
                path=path,
                principal=principal,
                roles=api.user.get_roles(username=principal, obj=object),
                uuid=IGWUUID(object).get(),
                )
            )
        return record

    def get(self, object, principal=None):
        """
            Returns an existing elastic index for a site object, empty object or list if no register found.
            If principal not specified, will return all records for an object:
        """
        path = self.relative_path(object)
        self.elastic = getUtility(IElasticSearch)
        elastic_index = ElasticSharing().get_index_name().lower()
        if principal is None:
            # Change to query elastic for a register matching principal and path
            # and return a list of items or None if query empty
            es_results = self.elastic().search(index=elastic_index,
                                               doc_type='sharing',
                                               body={'query': {'match': {'uuid': IGWUUID(object).get()}}}
                                               )
            result = []
            if es_results['hits']['total'] > 0:
                # result = [es_results['hits']['hits'][0]['_source']]
                for i in range(es_results['hits']['total']):
                    result.append(es_results['hits']['hits'][i]['_source'])

        else:
            # Change to Query elastic for all registers matching path
            # and returm ONE item
            es_results = self.elastic().search(index=elastic_index,
                                               doc_type='sharing',
                                               body={'query': {
                                                        'bool': {
                                                            'must': [{
                                                                'match': {'principal': principal}},
                                                                {
                                                                'match': {'uuid': IGWUUID(object).get()}}]
                                                            }}})
            result = []
            if es_results['hits']['total'] > 0:
                result = [es_results['hits']['hits'][0]['_source']]
        return result

    def modified(self, object):
        """ Handler for local roles changed event. Will add or remove a record form elastic """
        current_local_roles = self.object_local_roles(object)

        try:
            # Search for records to be deleted
            existing_records = self.get(object)

            existing_principals = [aa['principal'] for aa in existing_records]

            current_principals = current_local_roles.keys()
            current_principals_in_groups = []

            for cprincipal in current_principals:
                if api.group.get(groupname=cprincipal):
                    users = api.user.get_users(groupname=cprincipal)
                    for user in users:
                        current_principals_in_groups.append(user.id)

            principals_to_delete = set(existing_principals) - set(current_principals_in_groups) - set(current_principals)
            for principal in principals_to_delete:
                self.remove(object, principal)

            # Add new records or modify existing ones
            for principal, roles in current_local_roles.items():
                if api.group.get(groupname=principal):
                    users = api.user.get_users(groupname=principal)
                owner = object.getOwner()._id
                for user in users:
                    principal = user.id

                    if principal != owner:
                        es_record = self.get(object, principal)

                        if not es_record:
                            self.add(object, principal)
                        elif es_record[0]['roles'] != roles:
                            self.modify(object, principal, attributes=roles)
                        else:
                            pass
                    else:
                        es_record = self.get(object, principal)

                    if not es_record:
                        self.add(object, principal)
                    elif es_record[0]['roles'] != roles:
                        self.modify(object, principal, attributes=roles)
                    else:
                        pass
                    # No changes to roles, ignore others
        except:
            pass

    def add(self, object, principal):
        """ Adds a shared object index """
        record = self.make_record(object, principal)
        SharedMarker(object).share()
        self.elastic = getUtility(IElasticSearch)
        self.elastic().create(**record)

    def modify(self, object, principal, attributes):
        """
            Modifies an existing ES record
        """
        # Unused?
        # path = self.relative_path(object)
        self.elastic = getUtility(IElasticSearch)
        elastic_index = ElasticSharing().get_index_name().lower()
        result = self.elastic().search(index=elastic_index,
                                       doc_type='sharing',
                                       body={'query': {
                                                'bool': {
                                                    'must': [{'match': {'principal': principal}},
                                                             {'match': {'uuid': IGWUUID(object).get()}}]
                                                            }}})

        self.elastic().update(index=elastic_index,
                              doc_type='sharing',
                              id=result['hits']['hits'][0]['_id'],
                              body={'doc': {'_source': {'roles': attributes}}})

    def remove(self, object, principal):
        """ Removes a shared object index """
        # Unused?
        # path = self.relative_path(object)
        SharedMarker(object).unshare()
        self.elastic = getUtility(IElasticSearch)
        elastic_index = ElasticSharing().get_index_name().lower()
        result = self.elastic().search(index=elastic_index,
                                       doc_type='sharing',
                                       body={'query': {
                                                'bool': {
                                                    'must': [{'match': {'principal': principal}},
                                                             {'match': {'uuid': IGWUUID(object).get()}}]
                                                            }}})

        self.elastic().delete(index=elastic_index, doc_type='sharing', id=result['hits']['hits'][0]['_id'])

    def shared_on(self, object):
        """ Returns a list of all items shared on a specific community """
        base_path = '/'.join(object.getPhysicalPath())
        portal_catalog = getToolByName(getSite(), 'portal_catalog')
        shared_items = portal_catalog.searchResults(is_shared=True)

        return [item for item in shared_items if item.getPath().startswith(base_path)]

    def shared_with(self, username):
        """
            Returns a list of all items shared with a specific user, and all groups
            where this user belongs to
        """
        user_groups = []
        principals = user_groups + [username]
        portal = api.portal.get()
        portal_catalog = getToolByName(getSite(), 'portal_catalog')

        communities_by_path = {a.getPath(): a for a in portal_catalog.unrestrictedSearchResults(portal_type='ulearn.community')}

    def format_item(item):
        #community_path = re.sub(r'(^{}\/[^\/]+)\/?.*$'.format(self.site_root_path), r'\1', str(item['path']))
        community_path = str(format(self.site_root_path) + '/' + item['path'].split('/')[1])
        community = communities_by_path[community_path]

        item_catalog = portal_catalog.unrestrictedSearchResults(gwuuid=str(item['uuid']))[0]
        return dict(
            title=item_catalog.Title,
            url=item_catalog.getURL(),
            portal_type=item_catalog.portal_type,
            community_displayname=community.Title,
            community_url=community.getURL(),
            by=item_catalog.Creator,
            by_profile='{}/profile/{}'.format(getSite().absolute_url(), item_catalog.Creator)
                )

    def is_shared(item):
        item_catalog = portal_catalog.unrestrictedSearchResults(gwuuid=str(item['uuid']))[0]

        object = item_catalog._unrestrictedGetObject()

        groups = []
        groups_user = api.group.get_groups(username=username)
        if groups_user:
            groups = [group.id for group in groups_user]

        if [group for group in groups if group in object.__ac_local_roles__.keys()]:
            owner = object.getOwner()._id
            if username != owner:
                return True
            else:
                return False
        elif username in object.__ac_local_roles__.keys():
            is_Owner = [a for a in object.__ac_local_roles__[username] if a in ['Owner']]
            if is_Owner:
                return False
            effective_roles = [a for a in object.__ac_local_roles__[username] if a not in ['Owner']]
            if effective_roles:
                return True
        return False

        # shared_items = portal_catalog.searchResults(is_shared=True)

        # XXX TODO
        # principals should return a list of all the principals for the current
        # user
        self.elastic = getUtility(IElasticSearch)
        elastic_index = ElasticSharing().get_index_name().lower()
        shared_items = self.elastic().search(index=elastic_index,
                                             doc_type='sharing',
                                             body={'query': {
                                                    'bool': {
                                                        'must': {'match_all': {}},
                                                        'filter': {
                                                            'terms': {
                                                                'principal': principals
                                                                }
                                                            }
                                                        }},
                                                    'size': 1000})

        shared_items = [a['_source'] for a in shared_items['hits']['hits']]
        # Tha is_shared is still required?

        results = [format_item(a) for a in shared_items if is_shared(a)]

        # Ordena els resultats per title
        results.sort(key=lambda a: a['title'].lower())

        return results

grok.global_utility(ElasticSharing)


class SharedWithMe(grok.View):
    grok.context(Interface)
    grok.name('shared_with_me')
    # grok.require('base.authenticated')
    grok.layer(IUlearn5CoreLayer)

    def render(self):
        """ AJAX view to access shared items of the current logged in useR """
        self.request.response.setHeader('Content-type', 'application/json')
        results = []
        sharing = queryUtility(IElasticSharing)
        username = api.user.get_current().id
        results = sharing.shared_with(username)
        return json.dumps(results)


class Shared(grok.View):
    grok.context(Interface)
    # grok.require('base.authenticated')
    grok.layer(IUlearn5CoreLayer)

    def getContent(self):
        """	List all items shared on this community """
        results = []
        sharing = queryUtility(IElasticSharing)
        results = sharing.shared_on(self.context)
        return results


# class Sharing(grok.View):
#     """
#        Substitution of the default sharing view
#     """
#     grok.context(Interface)
#     grok.require('base.authenticated')
#     grok.layer(IUlearn5CoreLayer)

#     def get_acl(self):
#         local_roles = self.context.__ac_local_roles__.keys()
#         acl =


#         return acl


class IShared(Interface):
    def is_shared():
        """ Is this object shared outside a community? (true or false) """
        pass


class SharedMarker(grok.Adapter):
    grok.provides(IShared)
    grok.context(Interface)

    def __init__(self, context):
        """ Initialize mark as non-shared """
        self.context = context
        if getattr(self.context, '_shared', None) is None:
            self.unshare()

    def is_shared(self):
        """ Returns True if the object is shared """
        return getattr(self.context, '_shared', False)

    def share(self):
        """ Sets the shared status of the object """
        if not self.is_shared():
            setattr(self.context, '_shared', True)
            self.context.indexObject()
            print
            print 'Shared'
            print

    def unshare(self):
        """ Sets the shared status of the object """
        if self.is_shared():
            setattr(self.context, '_shared', False)
            self.context.indexObject()
            print
            print 'Unshared'
            print

    def SharingChanged(content, event):
        """ Hook to store shared mark on object & elastic """
        elastic_sharing = queryUtility(IElasticSharing)
        elastic_sharing.modified(content)

    def RemoveObject(content, event):
        """ Hook delete object plone remove object elastic """
        elastic_sharing = queryUtility(IElasticSharing)
        current_local_roles = elastic_sharing.object_local_roles(content)
        content.manage_delLocalRoles(current_local_roles)
        elastic_sharing.modified(content)


@indexer(IDexterityContent)
def sharedIndexer(context):
    """ Create a catalogue indexer, registered as an adapter for DX content. """
    return IShared(context).is_shared()
grok.global_adapter(sharedIndexer, name='is_shared')


@indexer(IBaseObject)
def sharedIndexerAT(context):
    """ Create a catalogue indexer, registered as an adapter for AT content. """
    return IShared(context).is_shared()

grok.global_adapter(sharedIndexerAT, name='is_shared')
