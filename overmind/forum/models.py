import datetime
import math

from django.conf import settings
from django.core.urlresolvers import reverse
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


class TagManager(models.Manager):
    def list_all(self):
        "Results are cached in memory"
        if not hasattr(self, '_cached_list_all'):
            self._cached_list_all = list(self.all())
        return self._cached_list_all


class Tag(models.Model):
    label = models.CharField(max_length=32, unique=True)
    description = models.TextField(default='', blank=True)
    objects = TagManager()

    def __str__(self):
        return self.label


class Topic(models.Model):
    subject = models.CharField(max_length=256)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now_add=True, db_index=True)
    tags = models.ManyToManyField(Tag)
    response_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    is_deleted = models.BooleanField(db_index=True, default=False)
    is_closed = models.BooleanField(default=False)
    is_solved = models.BooleanField(default=False)
    # updated whenever content was changed (value used for caching)
    content_updated = models.DateTimeField(auto_now_add=True)

    def get_absolute_url(self, last_page=False):
        if self.is_deleted:
            return None
        slug = slugify('{}_{}'.format(self.subject, self.created.date()))
        url = reverse('forum:posts-list', args=(slug, self.pk))
        if last_page:
            num_pages = math.ceil((self.response_count + 1) / settings.FORUM_POSTS_PER_PAGE)
            url = "{}?page={}".format(url, num_pages)
        return url

    def posts_count(self):
        return self.response_count + 1

    def __str__(self):
        return self.subject


class TopicHistory(models.Model):
    ACTION_CHOICES = (
        ('deleted', 'Topic was deleted'),
        ('recovered', 'Topic was recovered'),
        ('subject_changed', 'Topic subject was changed'),
        ('solved', 'Topic was marked as solved'),
        ('not_solved', 'Topic was marked as not solved'),
        ('closed', 'Topic was closed'),
        ('opened', 'Topic was opened'),
        ('spam_reported', 'Topic was reported as spam'),
    )
    topic = models.ForeignKey(Topic)
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    created = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    prev_subject = models.TextField(default='', blank=True)

    def action_description(self):
        return dict(self.ACTION_CHOICES)[self.action]


class Post(models.Model):
    topic = models.ForeignKey(Topic, related_name='posts')
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    content = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now_add=True)
    ip = models.IPAddressField(null=True, blank=True)
    is_deleted = models.BooleanField(db_index=True, default=False)
    is_solving = models.BooleanField(default=False)

    def __str__(self):
        return self.content[:120]

    def get_absolute_url(self):
        return reverse('forum:post-details', args=(self.topic_id, self.pk, ))


class PostHistory(models.Model):
    ACTION_CHOICES = (
        ('deleted', 'Post was deleted'),
        ('recovered', 'Post was recovered'),
        ('content_changed', 'Post content was changed'),
        ('spam_reported', 'Post was reported as spam'),
        ('is_solving', 'Post was marked as solving a problem'),
        ('not_solving', 'Post mark of solving a problem was removed'),
    )
    post = models.ForeignKey(Post)
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    created = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    prev_content = models.TextField(default='', blank=True)

    def action_description(self):
        return dict(self.ACTION_CHOICES)[self.action]
