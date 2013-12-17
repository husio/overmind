from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic import RedirectView

from dynamicwidgets import handlers


admin.autodiscover()
handlers.default.autodiscover()

urlpatterns = patterns('',
    url(r'^$',
        RedirectView.as_view(url='forum/')),
    url(r'^forum/',
        include('forum.urls', 'forum')),
    url(r'^auth/',
        include('simpleauth.urls', 'simpleauth')),
    url(r'^dynamicwidget/',
        include('dynamicwidgets.urls', 'dynamicwidget')),
    url(r'^_/admin/',
        include(admin.site.urls)),
)


urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
