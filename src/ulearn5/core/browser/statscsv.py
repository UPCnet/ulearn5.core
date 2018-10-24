# -*- coding: utf-8 -*-
from five import grok
from plone import api
from zope.interface import Interface
from Acquisition import aq_inner

from Products.CMFCore.utils import getToolByName
from zope.component import getUtility

from datetime import datetime

from mrs5.max.utilities import IMAXClient

from zope.site.hooks import setSite
from plone.namedfile.file import NamedBlobFile
from plone.dexterity.utils import createContentInContainer

from ulearn5.core.browser.stats import StatsQueryBase
from ulearn5.core.browser.stats import STATS
from ulearn5.core.browser.stats import first_moment_of_month
from zope.component import getUtilitiesFor
from souper.interfaces import ICatalogFactory

import StringIO
import csv
import unicodedata
import time
import transaction


HEADER_CSV = ['id', 'last_login_time']


def set_header_csv():
    user_properties_utility = getUtility(ICatalogFactory, name='user_properties')

    try:
        extender_name = api.portal.get_registry_record('base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender')
    except:
        extender_name = ''

    if extender_name:
        if extender_name in [a[0] for a in getUtilitiesFor(ICatalogFactory)]:
            extended_user_properties_utility = getUtility(ICatalogFactory, name=extender_name)
            extended = list(set(extended_user_properties_utility.properties) - set(user_properties_utility.properties))
            HEADER_CSV.extend(user_properties_utility.properties)
            HEADER_CSV.extend(extended)
            HEADER_CSV.remove('username')


def ListLastLoginCSV():
    pmd = api.portal.get_tool(name='portal_memberdata')
    output = []
    for user in pmd._members.items():
        user_memberdata = api.user.get(username=user[0])
    if user_memberdata:
        userProfile = get_user_properties_stats(user_memberdata)
        output.append(userProfile)
    return output


def get_user_properties_stats(user):
    profile_data = []
    for attr in HEADER_CSV:
        value = user.getProperty(attr) if user.getProperty(attr) else ''
        if attr == 'last_login_time':
            value = '{}/{}/{} {}'.format("%02d" % value.day(), "%02d" % value.month(), value.year(), value.Time())
        profile_data.append(value)
    return profile_data


def getDestinationFolder(stats_folder):
    portal = api.portal.get()
    setSite(portal)
    # Create 'stats_folder' folder if not exists
    if portal.get(stats_folder) is None:
        makeFolder(portal, stats_folder)
    portal = portal.get(stats_folder)
    today = datetime.now()
    context = aq_inner(portal)
    tool = getToolByName(context, 'translation_service')
    month = tool.translate(today.strftime("%B"), 'ulearn', context=context).encode()
    month = month.lower()
    year = today.strftime("%G")
    # Create year folder and month folder if not exists
    if portal.get(year) is None:
        makeFolder(portal, year)
        portal = portal.get(year)
        makeFolder(portal, month)
    # Create month folder if not exists
    else:
        portal = portal.get(year)
        if portal.get(month) is None:
            makeFolder(portal, month)
    portal = portal.get(month)
    return portal


def makeFolder(portal, name):
    transaction.begin()
    obj = createContentInContainer(portal, 'Folder', id='{}'.format(name), title='{}'.format(name), description='{}'.format(name))
    obj.reindexObject()
    transaction.commit()


class GenerateReport(StatsQueryBase):
    grok.context(Interface)
    grok.name('statscsv_view')
    grok.require('base.webmaster')
    """
    Download the content type as a CSV file.
    """

    def render(self):
        maxclient, settings = getUtility(IMAXClient)()
        maxclient.setActor(settings.max_restricted_username)
        maxclient.setToken(settings.max_restricted_token)

        today = datetime.now()

        activities = {'rows': []}
        set_header_csv()
        usersLogin = ListLastLoginCSV()
        for user in usersLogin:
            if user is not None:
                self.iterateActivities(maxclient, user, today, activities)

        activity_folder = self.getTranslateActivityFolder()
        self.printCSV(activities, activity_folder)

        chats = {'rows': []}
        chat_folder = 'chats'
        self.messagesFromUserinChat(maxclient, today, chats)
        self.printCSV(chats, chat_folder)

    def messagesFromUserinChat(self, maxclient, today, chats):
        parameters = {'date_filter': '{}-{:02}'.format(*today.timetuple())}
        parameters['limit'] = 0

        messages = maxclient.messages.get(qs=parameters)

        aggregation = {}
        for message in messages:
            actor = message.get('actor', {}).get('displayName', None)
            actor = unicodedata.normalize('NFKD', actor).encode('ascii', errors='ignore')
            loginid = message.get('actor', {}).get('username', None)
            profile = get_user_properties_stats(loginid) if get_user_properties_stats(loginid) else [actor, actor, '', '', '', '', '', '', '', '']
            conversations = message.get('contexts')
            conversation = conversations[0].get('displayName', u'Conversación privada')

            if actor is not None and conversation is not None:
                user = aggregation.setdefault(actor, {})
                user = aggregation[actor]

                user.setdefault(conversation, [profile, 0])
                user[conversation][1] += 1

        for user, conversations in aggregation.items():
            for conversation, tupla in conversations.items():
                name = tupla[0]
                chat = unicodedata.normalize('NFKD', conversation).encode('ascii', errors='ignore')
                chat = chat.replace(',', '')
                name.extend([chat, tupla[1]])
                chats['rows'].append(name)

    def iterateActivities(self, maxclient, user, today, activities):
        params = {}
        params['search_filters'] = {}
        params['search_filters']['is_drilldown'] = False
        params['search_filters']['keywords'] = []
        params['search_filters']['access_type'] = None

        try:
            userObj = maxclient.people[user[0]].get()
            comunities = len(userObj['subscribedTo'])
            # for each community of this user...
            for i in range(0, comunities):
                row = []
                for c in range(0, len(user)):
                    row.append(user[c])

                community = unicodedata.normalize('NFKD', userObj['subscribedTo'][i]['displayName']).encode('ascii', errors='ignore')
                community = community.replace(',', '')
                comm_hash = userObj['subscribedTo'][i]['hash'].encode()
                params['search_filters']['community'] = comm_hash
                params['search_filters']['user'] = user[0]
                activity, comments, documents, links, media = 0, 0, 0, 0, 0

                # get all stats from 'start' to 'end'
                for stat_type in STATS:
                    value = self.get_stats(stat_type, params['search_filters'], start=first_moment_of_month(today), end=today)
                    if stat_type == 'activity':
                        activity += value
                    elif stat_type == 'comments':
                        comments += value
                    elif stat_type == 'documents':
                        documents += value
                    elif stat_type == 'links':
                        links += value
                    elif stat_type == 'media':
                        media += value
                row.extend([community, str(activity), str(comments), str(documents), str(links), str(media)])
                activities['rows'].append(row)
        except:
            userAttr = dict()
            userAttr = user
            userAttr.extend(['', '0', '0', '0', '0', '0'])
            activities['rows'].append(userAttr)

    def getTranslateActivityFolder(self):
        lang = api.portal.get_registry_record(name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.language')
        if lang == 'ca':
            activity_folder = 'activitat'
        elif lang == 'es':
            activity_folder = 'actividad'
        else:
            activity_folder = 'activity'
        return activity_folder

    def printCSV(self, rows, type_info):
        lines = []
        if type_info == 'actividad':
            HEADER_CSV.extend(['community', 'activity', 'comments', 'documents', 'links', 'media'])
        elif type_info == 'chats':
            HEADER_CSV.extend(['chat', 'number of messages'])

        lines.append(HEADER_CSV)
        [lines.append(row) for row in rows['rows']]
        portal = getDestinationFolder(type_info)
        filename = "%s.csv" % time.strftime("%02d-%02m-%Y")

        output = StringIO.StringIO()
        a = csv.writer(output, delimiter=',')
        a.writerows(lines)
        data = output.getvalue()

        tb = transaction.begin()
        file = NamedBlobFile(data=data, filename=u'{}'.format(filename), contentType='application/csv')
        obj = createContentInContainer(portal, 'AppFile', id='{}'.format(filename), title='{}'.format(filename), file=file, checkConstraints=False)
        obj.reindexObject()
        tb.commit()
        self.response.setBody('%s' % tb.status, lock=True)
