# -*- coding: utf-8 -*-
"""Init and utils."""

from Products.LDAPUserFolder.utils import from_utf8
from Products.PortalTransforms.transforms.safe_html import hasScript as hasScript_original
from patches import from_latin1
from patches import get_date_options
from patches import hasScript
from plone.app.widgets.utils import get_date_options as get_date_options_original
from zope.i18nmessageid import MessageFactory

import inspect
import logging

_ = MessageFactory('ulearn')

requests_log = logging.getLogger('requests')
requests_log.setLevel(logging.WARNING)


def marmoset_patch(old, new, extra_globals={}):  # pragma: no cover
    """
        Hot patching memory-loaded code
    """
    g = old.func_globals
    g.update(extra_globals)
    c = inspect.getsource(new)
    exec c in g
    old.func_code = g[new.__name__].func_code


marmoset_patch(from_utf8, from_latin1)
marmoset_patch(get_date_options_original, get_date_options)
marmoset_patch(hasScript_original, hasScript)


def initialize(context):
    """Initializer called when used as a Zope 2 product."""
