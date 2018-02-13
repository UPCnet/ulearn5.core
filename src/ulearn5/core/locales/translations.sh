#!/bin/bash

domain=ulearn

msgfmt -o ca/LC_MESSAGES/$domain.mo  ca/LC_MESSAGES/$domain.po
msgfmt -o es/LC_MESSAGES/$domain.mo  es/LC_MESSAGES/$domain.po
msgfmt -o en/LC_MESSAGES/$domain.mo  en/LC_MESSAGES/$domain.po


domain=ulearn.portlets

msgfmt -o ca/LC_MESSAGES/$domain.mo  ca/LC_MESSAGES/$domain.po
msgfmt -o es/LC_MESSAGES/$domain.mo  es/LC_MESSAGES/$domain.po
msgfmt -o en/LC_MESSAGES/$domain.mo  en/LC_MESSAGES/$domain.po
