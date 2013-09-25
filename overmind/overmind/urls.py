from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic import RedirectView

from dynamicwidget import handlers


admin.autodiscover()
handlers.default.autodiscover()

urlpatterns = patterns('',
    url(r'^$',
        RedirectView.as_view(url='forum/')),
    url(r'^forum/',
        include('forum.urls', 'forum')),
    url(r'^auth/',
        include('simpleauth.urls', 'simpleauth')),
    url(r'^counter/',
        include('counter.urls', 'counter')),
    url(r'^dynamicwidget/',
        include('dynamicwidget.urls', 'dynamicwidget')),
    url(r'^_/admin/',
        include(admin.site.urls)),
)


urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
