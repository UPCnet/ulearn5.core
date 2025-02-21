# -*- coding: utf-8 -*-
"""Init and utils."""

import logging

from zope.i18nmessageid import MessageFactory

_ = MessageFactory('ulearn')

requests_log = logging.getLogger('requests')
requests_log.setLevel(logging.WARNING)

import inspect

from ldap.filter import filter_format as filter_format_original
from plone.app.widgets.utils import \
    get_date_options as get_date_options_original
from plone.app.widgets.utils import \
    get_datetime_options as get_datetime_options_original
#from Products.LDAPUserFolder.utils import from_utf8
from Products.PortalTransforms.transforms.safe_html import \
    hasScript as hasScript_original
from ulearn5.core.patches import (filter_format, from_latin1, get_date_options,
                                  get_datetime_options, hasScript)


def marmoset_patch(old, new, extra_globals={}):  # pragma: no cover
    """
        Hot patching memory-loaded code
    """
    g = old.__globals__
    g.update(extra_globals)
    c = inspect.getsource(new)
    exec(c, g)
    old.__code__ = g[new.__name__].__code__


#marmoset_patch(from_utf8, from_latin1)
marmoset_patch(get_date_options_original, get_date_options)
marmoset_patch(get_datetime_options_original, get_datetime_options)
marmoset_patch(hasScript_original, hasScript)
marmoset_patch(filter_format_original, filter_format)


def initialize(context):
    """Initializer called when used as a Zope 2 product."""
