from plone.restapi.services import Service
from ulearn5.core.services import UnknownEndpoint
from ulearn5.core.services.appconfig import AppConfig
from ulearn5.core.services.banners import Banners
from ulearn5.core.services.communities import Communities
from ulearn5.core.services.events import Events
from ulearn5.core.services.folders import Folders
from ulearn5.core.services.groups import Groups
from ulearn5.core.services.item import Item
from ulearn5.core.services.links import Links
from ulearn5.core.services.news import News
from ulearn5.core.services.notifications import Notifications
from ulearn5.core.services.notifymail import Notifymail
from ulearn5.core.services.notnotifymail import Notnotifymail
from ulearn5.core.services.notnotifypush import Notnotifypush
from ulearn5.core.services.people import People
from ulearn5.core.services.profile import Profile
from ulearn5.core.services.profilesettings import ProfileSettings
from ulearn5.core.services.saveeditacl import SaveEditACL
from zope.interface import implementer
from zope.publisher.interfaces.browser import IBrowserPublisher


@implementer(IBrowserPublisher)
class APIBase(Service):
    """
    Base service, used to manage subpaths of @api
    """

    PATH_DICT = {
        "appconfig": AppConfig,
        "banners": Banners,
        "communities": Communities,
        "saveeditacl": SaveEditACL,
        "notnotifymail": Notnotifymail,
        "notnotifypush": Notnotifypush,
        "notifymail": Notifymail,
        "events": Events,
        "folders": Folders,
        "groups": Groups,
        "item": Item,
        "links": Links,
        "news": News,
        "notifications": Notifications,
        "people": People,
        "profilesettings": ProfileSettings,
        "profile": Profile,
    }

    def __init__(self, context, request):
        super().__init__(context, request)
        self.subpath = []

    def publishTraverse(self, request, name):
        """
        Store dynamic path parts (after @api) in self.subpath
        """
        self.subpath.append(name)
        return self

    def browserDefault(self, request):
        """
        Error handling. Must be here to avoid errors
        """
        return self, ()

    def reply(self):
        """
        Main method. Calls the corresponding handler for the subpath
        """
        if not self.subpath:
            # Plain petition to @api (no subpath)
            return {"message": "Welcome to the API base", "code": 200}

        # Identifying the subpath (first segment after @api)
        route = self.subpath[0]
        handler_class = self.PATH_DICT.get(route)

        if handler_class:
            # Send parameters (query or body) to the handler
            kwargs = {key: value for key, value in self.request.form.items()}

            # Call the corresponding handler
            handler = handler_class(self.context, self.request, **kwargs)
            return handler.handle_subpath(self.subpath[1:])

        # Path not found in PATH_DICT
        raise UnknownEndpoint(f"Unknown endpoint: {route}")
