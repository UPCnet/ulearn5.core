# -*- coding: utf-8 -*-
from five import grok
from plone import api
from zope.interface import Interface
from Acquisition import aq_chain
from collections import Counter

from Products.CMFCore.utils import getToolByName
from zope.component import getUtility

from plone.memoize.view import memoize_contextless

from datetime import datetime
from zope.component.hooks import getSite

from mrs5.max.utilities import IMAXClient
from ulearn5.core.content.community import ICommunity
import json
import calendar
from zope.schema.interfaces import IVocabularyFactory
from ulearn5.core import _


def next_month(current):
    next_month = 1 if current.month == 12 else current.month + 1
    next_year = current.year + 1 if next_month == 1 else current.year
    last_day_of_next_month = calendar.monthrange(next_year, next_month)[1]
    next_day = current.day if current.day <= last_day_of_next_month else last_day_of_next_month
    return current.replace(month=next_month, year=next_year, day=next_day)


def last_day_of_month(dt):
    return calendar.monthrange(dt.year, dt.month)[1]


def first_moment_of_month(dt):
    return dt.replace(day=1, hour=0, minute=0, second=0)


def last_moment_of_month(dt):
    return dt.replace(day=last_day_of_month(dt), hour=23, minute=59, second=59)


def last_twelve_months_range():
    current_year = datetime.now().year
    last_year = current_year - 1
    current_month = datetime.now().month
    last_year_month = 1 if current_month == 12 else current_month + 1

    return (last_year, last_year_month, current_year, current_month)

STATS = ['activity', 'comments', 'documents', 'links', 'media']


class StatsView(grok.View):
    grok.context(Interface)
    grok.name('ulearn-stats')
    grok.require('base.webmaster')

    def __init__(self, context, request):
        super(StatsView, self).__init__(context, request)
        self.catalog = getToolByName(self.portal(), 'portal_catalog')

    @memoize_contextless
    def portal(self):
        return getSite()

    def get_communities(self):
        all_communities = [{'hash': 'all', 'title': _(u'Todas las comunidades')}]
        all_communities += [{'hash': community.community_hash, 'title': community.Title} for community in self.catalog.searchResults(portal_type='ulearn.community')]
        return json.dumps(all_communities)

    def get_months(self, position):
        all_months = []
        vocab = getUtility(IVocabularyFactory,
                           name='plone.app.vocabularies.Month')

        last_12 = last_twelve_months_range()
        current_month_day = last_12[1] if position == 'start' else last_12[3]

        for field in vocab(self.context):
            month_number = field.value + 1
            selected = month_number == current_month_day
            all_months += [{'value': month_number, 'title': field.title, 'selected': selected}]

        return all_months

    def get_years(self, position):
        all_years = []
        years = range(datetime.now().year - 11, datetime.now().year + 1)
        last_12 = last_twelve_months_range()
        current_year = last_12[0] if position == 'start' else last_12[2]

        for year in years:
            selected = year == current_year
            all_years += [{'value': year, 'title': year, 'selected': selected}]

        return all_years


class StatsQueryBase(grok.View):
    """ Base methods for ease the extension of the genweb StatsQuery view.
    """
    grok.baseclass()

    def update(self):
        super(StatsQueryBase, self).update()
        catalog = getToolByName(self.portal(), 'portal_catalog')
        self.plone_stats = PloneStats(catalog)
        self.max_stats = MaxStats(self.get_max_client())
        self._params = None

    @memoize_contextless
    def portal(self):
        return getSite()

    def get_max_client(self):
        maxclient, settings = getUtility(IMAXClient)()
        maxclient.setActor(settings.max_restricted_username)
        maxclient.setToken(settings.max_restricted_token)

        return maxclient

    def get_stats(self, stat_type, filters, start, end=None):
        """
        """
        stat_method = 'stat_{}'.format(stat_type)
        # First try to get stats from plone itself
        if hasattr(self.plone_stats, stat_method):
            return getattr(self.plone_stats, stat_method)(filters, start, end)
        elif hasattr(self.max_stats, stat_method):
            return getattr(self.max_stats, stat_method)(filters, start, end)
        else:
            return 0

    def get_month_by_num(self, num):
        """
        """
        ts = getToolByName(self.context, 'translation_service')
        vocab = getUtility(IVocabularyFactory, name='plone.app.vocabularies.Month')
        month_name = {a.value + 1: a.title for a in vocab(self.context)}[num]
        return ts.translate(month_name, context=self.request)

    @property
    def params(self):
        if self._params is None:
            self._params = self.get_params()

        return self._params

    def get_params(self):
        params = {}
        params['search_filters'] = {}
        params['search_filters']['is_drilldown'] = False
        params['stats_requested'] = self.request.form.get('stats_requested', None)
        params['search_filters']['keywords'] = self.request.form.get('keywords', [])
        params['search_filters']['access_type'] = self.request.form.get('access_type', None)

        community = self.request.form.get('community', None)
        params['search_filters']['community'] = None if community == 'all' else community
        user = self.request.form.get('user', None)
        params['search_filters']['user'] = None if user == '' else user

        # Get the drilldown params in case they exist
        drilldown_date = self.request.form.get('drilldown_date', None)
        params['stat_type'] = self.request.form.get('stat_type', None)

        # Dates MUST follow YYYY-MM-DD Format
        start_filter = self.request.form.get('start', '').strip()
        start_filter = start_filter or '{0}-01'.format(*datetime.now().timetuple())
        end_filter = self.request.form.get('end', '').strip()
        end_filter = end_filter or '{0}-12'.format(*datetime.now().timetuple())

        startyear, startmonth, startday = start_filter.split('-')
        endyear, endmonth, endday = end_filter.split('-')

        startyear = int(startyear)
        startmonth = int(startmonth)
        startday = int(startday)
        endyear = int(endyear)
        endmonth = int(endmonth)
        endday = int(endday)

        if drilldown_date:
            drilldown_year, drilldown_month, drilldown_day = drilldown_date.split('-')
            drilldown_year = int(drilldown_year)
            drilldown_month = int(drilldown_month)
            drilldown_day = int(drilldown_day)
            params['drilldown_date'] = datetime(drilldown_year, drilldown_month, drilldown_day)
            params['search_filters']['is_drilldown'] = True

        params['start'] = datetime(startyear, startmonth, startday)
        params['end'] = datetime(endyear, endmonth, endday)

        return params


class StatsQuery(StatsQueryBase):
    grok.context(Interface)
    grok.name('ulearn-stats-query')
    grok.require('base.webmaster')

    def render(self):
        if self.params['end'] < self.params['start']:
            self.params['end'] == self.params['start']

        results = {
            'rows': []
        }

        current = self.params['start']
        while current <= self.params['end']:
            row = [dict(value=self.get_month_by_num(current.month) + u' ' + unicode(current.year),
                        show_drilldown=False)]
            for stat_type in self.params['stats_requested']:
                value = self.get_stats(
                    stat_type,
                    self.params['search_filters'],
                    start=first_moment_of_month(current),
                    end=last_moment_of_month(current))
                row.append(dict(value=value,
                                stat_type=stat_type,
                                drilldown_date=current.strftime('%Y-%m-%d'),
                                show_drilldown=True))
            results['rows'].append(row)
            current = next_month(current)

        output_format = self.request.form.get('format', 'json')
        if output_format == 'json':
            self.request.response.setHeader('Content-type', 'application/json')
            return json.dumps(results)
        elif output_format == 'csv':
            self.request.response.setHeader('Content-type', 'application/csv')
            self.request.response.setHeader('Content-disposition', 'attachment; filename=ulearn-stats-{}.csv'.format(datetime.now().strftime('%Y%m%d%H%M%S')))
            lines = [','.join(['Fecha'] + self.params['stats_requested'])]
            for row in results['rows']:
                lines.append(','.join([str(col['value']) for col in row]))
            return '\n'.join(lines)


class StatsQueryDrilldown(StatsQueryBase):
    grok.context(Interface)
    grok.name('ulearn-stats-query-drilldown')
    grok.require('base.webmaster')

    def render(self):
        drilldown = self.get_stats(
            self.params['stat_type'],
            self.params['search_filters'],
            start=self.params['drilldown_date']
        )

        results = dict(results=drilldown)

        output_format = self.request.form.get('format', 'json')
        if output_format == 'json':
            self.request.response.setHeader('Content-type', 'application/json')
            return json.dumps(results)


class PloneStats(object):
    """
    """
    def __init__(self, catalog):
        self.catalog = catalog

    def get_community(self, path):
        doc = api.portal.get().unrestrictedTraverse(path)
        for obj in aq_chain(doc):
            if ICommunity.providedBy(obj):
                return obj

    def format_documents(self, results):
        count_dict = {}
        for doc in results:
            community = self.get_community(doc.getPath())
            community_path = '/'.join(community.getPhysicalPath())

            if count_dict.get(community_path, False):
                if count_dict[community_path]['users'].get(doc.Creator):
                    count_dict[community_path]['users'][doc.Creator]['count'] += 1
                else:
                    user_displayName = api.user.get(doc.Creator).getProperty('fullname')
                    if not user_displayName:
                        user_displayName = doc.Creator
                    count_dict[community_path]['users'][doc.Creator] = dict(count=1, displayName=user_displayName)
            else:
                count_dict[community_path] = dict(users={}, displayName=community.title)
                user_displayName = api.user.get(doc.Creator).getProperty('fullname')
                if not user_displayName:
                    user_displayName = doc.Creator
                count_dict[community_path]['users'][doc.Creator] = dict(count=1, displayName=user_displayName)

        rows = []

        for key in sorted([key for key in count_dict]):

            for user in count_dict[key]['users']:
                rows.append(dict(context=count_dict[key]['displayName'],
                                 username=count_dict[key]['users'][user]['displayName'],
                                 count=count_dict[key]['users'][user]['count']))

        return rows

    def stat_by_folder(self, search_folder, filters, start, end=None):
        """
        """
        # Prepare filtes search to get all the
        # target communities
        catalog_filters = dict(portal_type='ulearn.community')

        if filters['community']:
            catalog_filters['community_hash'] = filters['community']

        # List all paths of the resulting comunities
        communities = self.catalog.unrestrictedSearchResults(**catalog_filters)
        folder_paths = ['{}/{}'.format(community.getPath(), search_folder) for community in communities]

        # Prepare filters for the final search
        catalog_filters = dict(
            path={'query': folder_paths, 'depth': 2},
            created={'query': (start, end), 'range': 'min:max'}
        )

        if filters['user']:
            catalog_filters['Creator'] = filters['user']

        if filters['keywords']:
            catalog_filters['SearchableText'] = {'query': filters['keywords'], 'operator': 'or'}

        if filters['portal_type']:
            catalog_filters['portal_type'] = filters['portal_type']

        if filters['is_drilldown']:
            catalog_filters['created'] = {
                'query': (first_moment_of_month(start), last_moment_of_month(start)),
                'range': 'min:max'
            }
            results = self.catalog.unrestrictedSearchResults(**catalog_filters)
            return self.format_documents(results)
        else:
            results = self.catalog.unrestrictedSearchResults(**catalog_filters)
            return results.actual_result_count

    def stat_documents(self, filters, start, end=None):
        """
        """
        filters['portal_type'] = ['Document', 'File', 'AppFile']
        return self.stat_by_folder('documents', filters, start, end)

    def stat_links(self, filters, start, end=None):
        """
        """
        filters['portal_type'] = ['Link', ]
        return self.stat_by_folder('documents', filters, start, end)

    def stat_media(self, filters, start, end=None):
        """
        """
        filters['portal_type'] = ['Image', 'AppImage', 'ulearn.video', 'ulearn.video_embed']
        return self.stat_by_folder('documents', filters, start, end)


class MaxStats(object):
    def __init__(self, maxclient):
        self.maxclient = maxclient

    def get_max_context_displayName(self, context_hash):
        info = self.maxclient.contexts[context_hash].get()
        if info.get('displayName', False):
            return info['displayName']
        else:
            return context_hash

    def format_activity(self, activities):
        count_dict = {}
        for activity in activities:
            if activity.get('contexts', False):
                if count_dict.get(activity['contexts'][0]['url'], False):
                    if count_dict[activity['contexts'][0]['url']]['users'].get(activity['actor']['username']):
                        count_dict[activity['contexts'][0]['url']]['users'][activity['actor']['username']]['count'] += 1
                    else:
                        count_dict[activity['contexts'][0]['url']]['users'][activity['actor']['username']] = dict(count=1, displayName=activity['actor']['displayName'])
                else:
                    count_dict[activity['contexts'][0]['url']] = dict(displayName=activity['contexts'][0]['displayName'],
                                                                      users={})
                    count_dict[activity['contexts'][0]['url']]['users'][activity['actor']['username']] = dict(count=1, displayName=activity['actor']['displayName'])

        rows = []

        for key in sorted([key for key in count_dict]):

            for user in count_dict[key]['users']:
                rows.append(dict(context=count_dict[key]['displayName'],
                                 username=count_dict[key]['users'][user]['displayName'],
                                 count=count_dict[key]['users'][user]['count']))

        return rows

    def format_comments(self, comments):
        count_dict = {}

        for comment in comments:
            if count_dict.get(comment['object']['inReplyTo'][0]['contexts'][0], False):
                if count_dict[comment['object']['inReplyTo'][0]['contexts'][0]]['users'].get(comment['actor']['username']):
                    count_dict[comment['object']['inReplyTo'][0]['contexts'][0]]['users'][comment['actor']['username']]['count'] += 1
                else:
                    count_dict[comment['object']['inReplyTo'][0]['contexts'][0]]['users'][comment['actor']['username']] = dict(count=1, displayName=comment['actor']['displayName'])
            else:
                count_dict[comment['object']['inReplyTo'][0]['contexts'][0]] = dict(users={})
                count_dict[comment['object']['inReplyTo'][0]['contexts'][0]]['users'][comment['actor']['username']] = dict(count=1, displayName=comment['actor']['displayName'])

        rows = []
        for key in sorted([key for key in count_dict]):

            for user in count_dict[key]['users']:
                rows.append(dict(context=self.get_max_context_displayName(key),
                                 username=count_dict[key]['users'][user]['displayName'],
                                 count=count_dict[key]['users'][user]['count']))

        return rows

    def format_messages(self, messages):
        counter = Counter()
        for message in messages:
            counter[message['actor']['displayName']] += 1

        rows = []

        for user, count in counter.most_common():
            rows.append(dict(username=user,
                             count=count))

        return rows

    def format_active_conversations(self, messages):

        counter = {}
        conversations = {}
        rows = []
        for message in messages:
            # Save the participant under the counter
            if not message['contexts'][0]['id'] in counter:
                counter[message['contexts'][0]['id']] = []

            counter[message['contexts'][0]['id']].append(message['actor']['displayName'])
            # Save the conversation displayName or id
            if message['contexts'][0].get('displayName', False):
                conversations[message['contexts'][0]['id']] = message['contexts'][0]['displayName']
            else:
                # We have a private conversation
                conversations[message['contexts'][0]['id']] = u'Conversación privada'

        for key in counter:
            rows.append(dict(context=conversations[key],
                             username=u', '.join(list(set(counter[key])))))
        return rows

    def stat_activity(self, filters, start, end):
        """
        """
        if filters['community']:
            endpoint = self.maxclient.contexts[filters['community']].activities
        else:
            endpoint = self.maxclient.activities

        params = {'date_filter': '{}-{:02}'.format(*start.timetuple())}
        params['limit'] = 0

        if filters['user']:
            params['actor'] = filters['user']

        if filters['keywords']:
            params['keyword'] = filters['keywords']

        if filters['is_drilldown']:
            params['limit'] = 0
            try:
                return self.format_activity(endpoint.get(qs=params))
            except:
                return '?'
        else:
            try:
                return endpoint.head(qs=params)
            except:
                return '?'

    def stat_comments(self, filters, start, end):
        """
        """
        if filters['community']:
            endpoint = self.maxclient.contexts[filters['community']].comments
        else:
            endpoint = self.maxclient.activities.comments

        params = {
            'date_filter': '{}-{:02}'.format(*start.timetuple())
        }
        params['limit'] = 0

        if filters['user']:
            params['actor'] = filters['user']

        if filters['keywords']:
            params['keyword'] = filters['keywords']

        if filters['is_drilldown']:
            params['limit'] = 0
            try:
                return self.format_comments(endpoint.get(qs=params))
            except:
                return '?'
        else:
            try:
                return endpoint.head(qs=params)
            except:
                return '?'

    def stat_messages(self, filters, start, end):
        """
        """
        endpoint = self.maxclient.messages

        params = {'date_filter': '{}-{:02}'.format(*start.timetuple())}
        params['limit'] = 0

        if filters['user']:
            params['actor'] = filters['user']

        if filters['is_drilldown']:
            params['limit'] = 0
            try:
                return self.format_messages(endpoint.get(qs=params))
            except:
                return '?'
        else:
            try:
                return endpoint.head(qs=params)
            except:
                return '?'

    def stat_active(self, filters, start, end):
        """
        """
        endpoint = self.maxclient.conversations.active

        params = {'date_filter': '{}-{:02}'.format(*start.timetuple())}
        params['limit'] = 0

        if filters['user']:
            params['actor'] = filters['user']

        if filters['is_drilldown']:
            try:
                # Carles, sorry major causes workarround. Shame on me.
                msgs_endpoint = self.maxclient.messages
                return self.format_active_conversations(msgs_endpoint.get(qs=params))
            except:
                return '?'
        else:
            try:
                return endpoint.head(qs=params)
            except:
                return '?'
