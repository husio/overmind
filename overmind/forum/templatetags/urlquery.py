from urllib import parse

from django import template
from django.http import HttpRequest


register = template.Library()


@register.simple_tag
def urlquery_add(request_or_urlquery, **kwargs):
    if isinstance(request_or_urlquery, HttpRequest):
        urlquery = request_or_urlquery.META['QUERY_STRING']
    else:
        urlquery = request_or_urlquery
    pairs = parse.parse_qsl(urlquery)
    pairs.extend(kwargs.items())
    return parse.urlencode(pairs)


@register.simple_tag
def urlquery_remove(request_or_urlquery, *args, **kwargs):
    if isinstance(request_or_urlquery, HttpRequest):
        urlquery = request_or_urlquery.META['QUERY_STRING']
    else:
        urlquery = request_or_urlquery
    pairs = parse.parse_qsl(urlquery)
    names = set(args)
    newpairs = []
    for key, value in pairs:
        if key in names:
            continue
        if str(kwargs.get(key)) == value:
            continue
        newpairs.append((key, value))
    return parse.urlencode(newpairs)


@register.simple_tag
def urlquery_set(request_or_urlquery, **kwargs):
    if isinstance(request_or_urlquery, HttpRequest):
        urlquery = request_or_urlquery.META['QUERY_STRING']
    else:
        urlquery = request_or_urlquery
    pairs = parse.parse_qsl(urlquery)
    newpairs = []
    for key, value in pairs:
        if key in kwargs:
            continue
        newpairs.append((key, value))
    newpairs.extend(kwargs.items())
    return parse.urlencode(newpairs)


@register.simple_tag
def urlquery_toggle(request_or_urlquery, **kwargs):
    if isinstance(request_or_urlquery, HttpRequest):
        urlquery = request_or_urlquery.META['QUERY_STRING']
    else:
        urlquery = request_or_urlquery

    newpairs = parse.parse_qsl(urlquery)
    for key, value in kwargs.items():
        try:
            newpairs.remove((key, value))
        except ValueError:
            newpairs.append((key, value))
    return parse.urlencode(newpairs)
