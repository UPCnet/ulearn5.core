# -*- coding: utf-8 -*-

import json
from os import path
from apiclient.discovery import build
from datetime import datetime
from dateutil.relativedelta import relativedelta
from five import grok
from plone import api
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.interfaces import IPloneSiteRoot
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from ulearn5.core.controlpanel import IUlearnControlPanelSettings
from zope.component import getUtility
from oauth2client.service_account import ServiceAccountCredentials



datePoints = ["1d", "15d", "1m", "3m", "6m", "1y"]
dataSet = []

def globGetDatePoints():
    return datePoints + ['+' + datePoints[-1]]

def globGetDataset():
    return json.dumps(dataSet, separators=(',', ':'))

def globGetAccumulatedTable(table):
    accTable = []
    for row in table:
        accTable.append([])
        for cell in row:
            accTable[-1].append(cell)
        for i in xrange(1, len(datePoints) + 1):
            accTable[-1][i + 1] += accTable[-1][i]
    return accTable

def globGetDateIntervals():

    def textToDate(text):
        unit = text[-1]
        value = -int(text[:-1])
        dateAbb = {
            'd': 'days',
            'm': 'months',
            'y': 'years'
        }
        date = datetime.today() + \
               relativedelta(**{
                 dateAbb[unit]: value
               })
        return date

    return [textToDate(point) for point in datePoints] \
         + [datetime.min]


class statsAccessed(grok.View):
    grok.context(IPloneSiteRoot)
    grok.require('cmf.ManagePortal')
    grok_name = 'stats_accessed'
    grok.name(grok_name)

    section = "Accessed"
    updatable = True

    def getDatePoints(self):
        return globGetDatePoints()

    def getDataset(self):
        return globGetDataset()

    def getDateIntervals(self):
        return globGetDateIntervals()

    def getAllAccessedTables(self):
        dateIntervals = self.getDateIntervals()
        # gStoredAnalyticsFileName = "storedAnalytics.json"
        gAnalyticsPath = path.join(path.dirname(__file__))

        # def getStoredAnalytics():
        #     try:
        #         storedAnalytics = file(path.join(gAnalyticsPath, gStoredAnalyticsFileName), "r")
        #         data = json.loads(storedAnalytics.read())
        #         storedAnalytics.close()
        #         return data
        #     except:
        #         return {}

        def getUpToDateAnalytics(communityShortpaths):
            settings = getUtility(IRegistry).forInterface(IUlearnControlPanelSettings)
            if settings is None or \
               settings.gAnalytics_view_ID is None or \
               settings.gAnalytics_JSON_info is None or \
               settings.gAnalytics_enabled is None or \
               settings.gAnalytics_enabled == False:
               return {}
            gAnalytics_view_ID = settings.gAnalytics_view_ID
            gAnalytics_JSON_info = settings.gAnalytics_JSON_info

            # falsePrefixes = ['/2/intranetupcnet',
            #                  '/acl_users/credentials_cookie_auth/require_login?'
            #                  'came_from=https://comunitats.upcnet.es']

            falsePrefixes = []

            credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                           json.loads(gAnalytics_JSON_info),
                           scopes=['https://www.googleapis.com/auth/analytics.readonly'])
            service = build('analytics', 'v3', credentials=credentials)

            gaFilters = ','.join('ga:pagePath=~/' + communityShortpath
                                 for communityShortpath in communityShortpaths)
            numResults = 0
            totalResults = 0
            first = True
            data = {}
            while numResults < totalResults or first:
                analyticsData = service.data().ga().get(**{
                    'ids': 'ga:' + gAnalytics_view_ID,
                    'start_date': '2005-01-01',
                    'end_date': '9999-12-31',
                    'metrics': 'ga:pageviews',
                    'dimensions': 'ga:pagePath,ga:dateHourMinute',
                    'filters': gaFilters,
                    'max_results': '10000',
                    'start_index': str(numResults + 1),
                    'sort': 'ga:dateHourMinute'
                }).execute()
                numResults += len(analyticsData['rows'])
                if not(first) and totalResults != int(analyticsData['totalResults']):
                    numResults = 0
                    totalResults = 0
                    first = True
                    data = {}
                    continue

                totalResults = int(analyticsData['totalResults'])
                for row in analyticsData['rows']:
                    for prefix in falsePrefixes:
                        row[0] = row[0].replace(prefix, '')
                    row[0] = row[0].split('/')[2].split('@@')[0].split('?')[0]
                    if not row[0] in data:
                        data[row[0]] = []
                    data[row[0]].append([row[1], int(row[2])])
                first = False

            for communityShortpath in data:
                data[communityShortpath].reverse()

            # storedAnalytics = file(path.join(gAnalyticsPath, gStoredAnalyticsFileName), "wb")
            # storedAnalytics.write(json.dumps(data, separators=(',', ':')))
            # storedAnalytics.close()

            return data

        communityTitles = {}
        communityShortpaths = []
        for community in api.portal.get_tool(name='portal_catalog').unrestrictedSearchResults(portal_type='ulearn.community'):
            communityShortpath = community.getPath().split('/')[2]
            communityShortpaths.append(communityShortpath)
            communityTitles[communityShortpath] = community.Title


        if True:
            data = getUpToDateAnalytics(communityShortpaths)
        else:
            #data = getStoredAnalytics()
            data = {}

        accessedTable = []
        for communityShortpath in data:
            if communityShortpath in communityTitles:
                index = 0
                accessedTable.append([communityTitles[communityShortpath]]
                                     + [0]*(len(datePoints) + 1))
                for entry in data[communityShortpath]:
                    treatedDate = datetime.strptime(entry[0], "%Y%m%d%H%M%S")
                    while treatedDate < dateIntervals[index]:
                        index += 1
                    accessedTable[-1][index + 1] += entry[1]

        return [accessedTable, globGetAccumulatedTable(accessedTable)]

    def render(self):
        global dataSet
        dataSet = self.getAllAccessedTables()
        # dataSet = self.getAllAccessedTables("update" in self.request.form)
        # if self.updatable and "update" in self.request.form:
        #     return self.getDataset()
        return ViewPageTemplateFile('statisticsTemplate.pt')(self)


class statsModified(grok.View):
    grok.context(IPloneSiteRoot)
    grok.require('cmf.ManagePortal')
    grok_name = 'stats_modified'
    grok.name(grok_name)

    section = "Modified"
    updatable = False

    def getDatePoints(self):
        return globGetDatePoints()

    def getDataset(self):
        return globGetDataset()

    def getDateIntervals(self):
        return globGetDateIntervals()

    def getAllModifiedTables(self):
        dateIntervals = self.getDateIntervals()
        modifiedTable = []
        catalog = api.portal.get_tool(name='portal_catalog')
        for community in catalog.unrestrictedSearchResults(
            portal_type='ulearn.community'):
            modifiedTable.append([community.Title] + [0]*(len(datePoints) + 1))
            for file in catalog.unrestrictedSearchResults(
                    path=community.getPath()):
                index = 0
                entry = file.modified.asdatetime().replace(tzinfo=None)
                while entry < dateIntervals[index]:
                    index += 1
                modifiedTable[-1][index + 1] += 1

        return [modifiedTable, globGetAccumulatedTable(modifiedTable)]

    def render(self):
        global dataSet
        dataSet = self.getAllModifiedTables()
        return ViewPageTemplateFile('statisticsTemplate.pt')(self)

class statsAccessed(grok.View):
    grok.context(IPloneSiteRoot)
    grok.require('cmf.ManagePortal')
    grok_name = 'stats_accessed_communities'
    grok.name(grok_name)

    section = "Accessed"
    updatable = True

    def getDatePoints(self):
        return ['community', 'page', 'title', 'content_type', 'data',  'pageviews']

    def getDataset(self):
        return json.dumps(dataSet)


    def getDateIntervals(self):
        return globGetDateIntervals()

    def getAllAccessedTables(self):
        dateIntervals = self.getDateIntervals()
        # gStoredAnalyticsFileName = "storedAnalytics.json"
        gAnalyticsPath = path.join(path.dirname(__file__))

        # def getStoredAnalytics():
        #     try:
        #         storedAnalytics = file(path.join(gAnalyticsPath, gStoredAnalyticsFileName), "r")
        #         data = json.loads(storedAnalytics.read())
        #         storedAnalytics.close()
        #         return data
        #     except:
        #         return {}

        def getUpToDateAnalytics(communityShortpaths):
            settings = getUtility(IRegistry).forInterface(IUlearnControlPanelSettings)
            if settings is None or \
               settings.gAnalytics_view_ID is None or \
               settings.gAnalytics_JSON_info is None or \
               settings.gAnalytics_enabled is None or \
               settings.gAnalytics_enabled == False:
               return {}
            gAnalytics_view_ID = settings.gAnalytics_view_ID
            gAnalytics_JSON_info = settings.gAnalytics_JSON_info

            # falsePrefixes = ['/2/intranetupcnet',
            #                  '/acl_users/credentials_cookie_auth/require_login?'
            #                  'came_from=https://comunitats.upcnet.es']

            falsePrefixes = []

            credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                           json.loads(gAnalytics_JSON_info),
                           scopes=['https://www.googleapis.com/auth/analytics.readonly'])
            service = build('analytics', 'v3', credentials=credentials)

            gaFilters = ','.join('ga:pagePath=~/' + communityShortpath
                                 for communityShortpath in communityShortpaths)
            numResults = 0
            totalResults = 0
            first = True
            data = {}
            while numResults < totalResults or first:
                analyticsData = service.data().ga().get(**{
                    'ids': 'ga:' + gAnalytics_view_ID,
                    'start_date': '2005-01-01',
                    'end_date': '9999-12-31',
                    'metrics': 'ga:pageviews',
                    'dimensions': 'ga:pagePathLevel2,ga:pagePath,ga:pageTitle,ga:dimension1,ga:dateHourMinute',
                    'filters': gaFilters,
                    'max_results': '20',
                    'sort': '-ga:pageviews'
                }).execute()
                numResults += len(analyticsData['rows'])
                # if not(first) and totalResults != int(analyticsData['totalResults']):
                #     numResults = 0
                #     totalResults = 0
                #     first = True
                #     data = {}
                #     continue

                totalResults = int(analyticsData['totalResults'])
                # for row in analyticsData['rows']:
                #     # for prefix in falsePrefixes:
                #     #     row[0] = row[0].replace(prefix, '')
                #     row[0] = row[0].split('/')[1].split('@@')[0].split('?')[0]
                #     if not row[0] in data:
                #         data[row[0]] = []
                #     data[row[0]].append([row[1],row[2],row[3],row[4],int(row[5])])
                first = False

            # for communityShortpath in data:
            #     data[communityShortpath].reverse()

            # storedAnalytics = file(path.join(gAnalyticsPath, gStoredAnalyticsFileName), "wb")
            # storedAnalytics.write(json.dumps(data, separators=(',', ':')))
            # storedAnalytics.close()
            return analyticsData['rows']

        communityTitles = {}
        communityShortpaths = []
        for community in api.portal.get_tool(name='portal_catalog').unrestrictedSearchResults(portal_type='ulearn.community'):
            communityShortpath = community.getPath().split('/')[2]
            communityShortpaths.append(communityShortpath)
            communityTitles[communityShortpath] = community.Title


        if True:
            data = getUpToDateAnalytics(communityShortpaths)
        else:
            #data = getStoredAnalytics()
            data = {}

        # accessedTable = []
        # for communityShortpath in data:
        #     if communityShortpath in communityTitles:
        #         index = 0
        #         accessedTable.append([communityTitles[communityShortpath]]
        #                              + [0]*(len(datePoints) + 1))
        #         for entry in data[communityShortpath]:
        #             treatedDate = datetime.strptime(entry[3], "%Y%m%d%H%M%S")
        #             import ipdb;ipdb.set_trace()
        #             while treatedDate < dateIntervals[index]:
        #                 index += 1
        #             accessedTable[-1][index + 1] += entry[4]
        # return [accessedTable, globGetAccumulatedTable(accessedTable)]
        return data

    def render(self):
        global dataSet
        dataSet = self.getAllAccessedTables()
        # dataSet = self.getAllAccessedTables("update" in self.request.form)
        # if self.updatable and "update" in self.request.form:
        #     return self.getDataset()
        return ViewPageTemplateFile('statisticsTemplate.pt')(self)
