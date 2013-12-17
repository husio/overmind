from django.contrib import admin

from forum import models


class TabularPostAdmin(admin.TabularInline):
    raw_id_fields = ('author', )
    model = models.Post


class TopicHistoryAdmin(admin.TabularInline):
    model = models.TopicHistory
    max_num = 0
    search_fields = ('subject', )
    readonly_fields = ('action', 'created', 'author', 'prev_subject')


class TopicAdmin(admin.ModelAdmin):
    inlines = (TopicHistoryAdmin, TabularPostAdmin)
    raw_id_fields = ('author', )
    readonly_fields = ('view_count', 'response_count', 'posts_count')
    list_filter = ('is_deleted', 'created', 'updated')


class PostHistoryAdmin(admin.TabularInline):
    model = models.PostHistory
    max_num = 0
    readonly_fields = ('action', 'created', 'author', 'prev_content')


class PostAdmin(admin.ModelAdmin):
    inlines = (PostHistoryAdmin, )
    readonly_fields = ('created', 'updated')
    raw_id_fields = ('author', 'topic')
    search_fields = ('topic__subject', 'topic__id')
    list_filter = ('is_deleted', 'created')


admin.site.register(models.Topic, TopicAdmin)
admin.site.register(models.LastSeen)
admin.site.register(models.Tag)
admin.site.register(models.Moderator)
admin.site.register(models.Post, PostAdmin)
