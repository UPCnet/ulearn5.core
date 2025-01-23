from mrs5.max.browser.controlpanel import IMAXUISettings
from plone import api
from plone.registry.interfaces import IRegistry
from Products.Five.browser import BrowserView
from zope.component import queryUtility
from zope.component.hooks import getSite


TEMPLATE = """\
if (!window._MAXUI) {window._MAXUI = {}; }
window._MAXUI.username = '%(username)s';
window._MAXUI.oauth_token = '%(oauth_token)s';
window._MAXUI.max_server = '%(max_server)s';
window._MAXUI.max_server_alias = '%(max_server_alias)s';
window._MAXUI.avatar_url = '%(avatar_url)s';
window._MAXUI.profile_url = '%(profile_url)s'
window._MAXUI.contexts = '%(contexts)s';
window._MAXUI.activitySource = '%(activitySource)s';
window._MAXUI.activitySortView = '%(activitySortView)s';
window._MAXUI.language = '%(language)s';
window._MAXUI.hidePostboxOnTimeline = false;
window._MAXUI.domain = '%(domain)s';
"""


class communityVariables(BrowserView):

    def render(self):
        self.request.response.addHeader('content-type', 'text/javascript;;charset=utf-8')
        self.request.response.addHeader('cache-control', 'must-revalidate, max-age=0, no-cache, no-store')
        portal_url = getSite().absolute_url()

        registry = queryUtility(IRegistry)
        settings = registry.forInterface(IMAXUISettings, check=False)

        pl = api.portal.get_tool('portal_languages')
        if api.user.is_anonymous():  # the user has not logged in
            username = ''
            oauth_token = ''
            default_lang = pl.getDefaultLanguage()
        else:
            user = api.user.get_current()
            # Force username to lowercase
            username = user.id.lower()
            oauth_token = user.getProperty('oauth_token', None)
            default_lang = user.getProperty('language')
            if default_lang == '':
                default_lang = pl.getDefaultLanguage()

        pl = api.portal.get_tool('portal_languages')

        activity_views_map = {
            'Darreres Activitats': 'recent',
            'Activitats mes valorades': 'likes',
            'Activitats destacades': 'flagged'
        }

        try:
            activity_view = self.context.activity_view
        except Exception as e:
            print(e)
            activity_view = 'darreres_activitats'

        return TEMPLATE % dict(
            username=username,
            oauth_token=oauth_token,
            max_server=settings.max_server,
            max_server_alias=settings.max_server_alias,
            avatar_url='%s/people/{0}/avatar/mini' % (settings.max_server),
            profile_url='%s/profile/{0}' % (portal_url),
            contexts=self.context.absolute_url(),
            activitySource='activities',
            activitySortView=activity_views_map.get(activity_view, 'recent'),
            language=default_lang,
            domain=settings.domain
        )
