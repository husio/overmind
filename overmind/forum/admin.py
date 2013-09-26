from django.contrib import admin

from forum import models


class PostAdmin(admin.TabularInline):
    model = models.Post


class TopicAdmin(admin.ModelAdmin):
    inlines = (PostAdmin, )


admin.site.register(models.Topic, TopicAdmin)
admin.site.register(models.LastSeen)
admin.site.register(models.Tag)
admin.site.register(models.Moderator)
