import collections
import json
import time

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.gzip import gzip_page

from dynamicwidget import handlers, dotdict


@never_cache
@gzip_page
def widgets(request):
    wids = request.GET.getlist('wid')
    matching_handlers = collections.defaultdict(list)
    result = {}

    # find handlers and group wids by handler function
    for wid in wids:
        fn, params = handlers.default.find(wid)
        if fn:
            match = dotdict.Dict(wid=wid, params=dotdict.Dict(params))
            matching_handlers[fn].append(match)
        else:
            result[wid] = {'error': 'widget "{}" does not exist'.format(wid)}

    # for every widget handler, call it with all related wids at once
    for handler, args in matching_handlers.items():
        result.update(handler(request, args))

    # because when running locally it's always fast, allow to symulate delay
    if settings.DEBUG and getattr(settings, 'DYNAMIC_WIDGET_DEBUG_SLEEP', 0):
        time.sleep(settings.DYNAMIC_WIDGET_DEBUG_SLEEP)

    content = json.dumps(result)
    return HttpResponse(content, content_type='application/json')
