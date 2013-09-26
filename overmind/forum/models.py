import datetime

from django.core.urlresolvers import reverse
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.timezone import utc

from json_field import JSONField


class Moderator(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                related_name='forum_is_moderator')


class LastSeen(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                related_name='forum_last_seen')
    last_seen_all = models.DateTimeField()
    seen_topics = JSONField(default=dict, blank=True)

    @classmethod
    def obtain_for(cls, user):
        """There's no easy way of creating OneToOneField get_or_create
        functionality.

        It's not a manager method, because later we may want to replace it
        with a structure in memcache.
        """
        obj, created = cls.objects.get_or_create(user=user, defaults={
            'last_seen_all': datetime.datetime(2000, 1, 1).replace(tzinfo=utc),
            'seen_topics': {},
        })
        return obj


class Tag(models.Model):
    label = models.CharField(max_length=32, unique=True)
    description = models.TextField(default='', blank=True)

    def __str__(self):
        return self.label


class Topic(models.Model):
    subject = models.CharField(max_length=256)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tag)
    response_count = models.PositiveIntegerField(default=0)

    def get_absolute_url(self):
        slug = slugify('{}-{}'.format(self.created.date(), self.subject))
        return reverse('forum:posts-list', args=(self.pk, slug))

    def __str__(self):
        return self.subject


class Post(models.Model):
    topic = models.ForeignKey(Topic, related_name='posts')
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    content = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    ip = models.IPAddressField(null=True, blank=True)

    def __str__(self):
        return self.content[:120]

    def get_absolute_url(self):
        return self.topic.get_absolute_url()


