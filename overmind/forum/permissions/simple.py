import datetime

from django.utils.timezone import utc

from forum.models import Moderator, Post, Topic


class SimpleManager:
    _edit_limit_date = datetime.timedelta(minutes=10)

    def __init__(self, user):
        self.user = user
        self._topics_cache = {}
        self._posts_cache = {}

    def _post_from_cache(self, post_or_pk):
        if isinstance(post_or_pk, Post):
            post = post_or_pk
        else:
            post_pk = int(post_or_pk)
            post = self._posts_cache.get(post_pk)
            if not post:
                post = Post.objects.get(pk=post_pk)
        self._posts_cache[post.id] = post
        return post

    def _topic_from_cache(self, topic_or_pk):
        if isinstance(topic_or_pk, Topic):
            topic = topic_or_pk
        else:
            topic_pk = int(topic_or_pk)
            topic = self._topics_cache.get(topic_pk)
            if not topic:
                topic = Topic.objects.get(pk=topic_pk)
        self._topics_cache[topic.id] = topic
        return topic

    def is_moderator(self):
        if not hasattr(self, '_is_moderator_cache'):
            if self.user.is_anonymous():
                self._is_moderator_cache = False
            else:
                is_mod = Moderator.objects.filter(user=self.user).exists()
                self._is_moderator_cache = is_mod
        return self._is_moderator_cache

    def can_edit_topic(self, topic_or_pk):
        if self.user.is_anonymous():
            return False
        if self.is_moderator():
            return True
        return False

    def can_close_topic(self, topic_or_pk):
        if self.user.is_anonymous():
            return False
        if self.is_moderator():
            return True
        return False

    def can_create_topic(self):
        return self.user.is_authenticated()

    def can_delete_topic(self, topic_or_pk):
        return self.is_moderator()

    def can_edit_post(self, post_or_pk):
        if self.user.is_anonymous():
            return False
        if self.is_moderator():
            return True
        post = self._post_from_cache(post_or_pk)
        now = datetime.datetime.now().replace(tzinfo=utc)
        if post.topic.updated == post.created \
                and post.author_id == self.user.id \
                and post.created + self._edit_limit_date > now:
            return True
        return False

    def can_create_post(self, topic_or_pk):
        if self.user.is_anonymous():
            return False
        if self.is_moderator():
            return True
        topic = self._topic_from_cache(topic_or_pk)
        return True
        if topic.is_closed:
            return False

    def can_solve_topic_with_post(self, post_or_pk):
        if self.user.is_anonymous():
            return False
        if self.is_moderator():
            return True
        post = self._post_from_cache(post_or_pk)
        if self.user.id == post.topic.author_id:
            return True
        return False

    def can_delete_post(self, post_or_pk):
        return self.can_edit_post(post_or_pk)

    def can_report_topic_as_spam(self, topic_or_pk):
        return self.user.is_authenticated()

    def can_report_post_as_spam(self, post_or_pk):
        return self.user.is_authenticated()
