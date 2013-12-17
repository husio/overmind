import json

from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings

from forum.models import Post, Topic


WIDGETS_URL = reverse("dynamicwidget:widgets")


class LastSeenTest(TestCase):
    fixtures = ['forum/tests/small_size_forum.yaml']

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
                'mikeymike', 'mikeymike@example.com', 'password')
        is_logged = self.client.login(username='mikeymike', password='password')
        self.assertTrue(is_logged)

    @override_settings(FORUM_POSTS_PER_PAGE=1)
    def test_last_seen_updated_on_widget_fetch(self):
        self.assertTrue(self.is_topic_new(2))
        posts = Post.objects.filter(topic__id=2).order_by('created')
        post_ids = tuple(posts.values_list('id', flat=True))
        self.assertTrue(self.is_post_new(post_ids[0]),
                        "at first, all posts are new")
        self.assertFalse(self.is_post_new(post_ids[0]),
                         "but the are marked as seen after first check")
        self.assertTrue(self.is_topic_new(2),
                        "topic should stay new as long as there is at least "
                        "one unseen post")
        msg = 'we have still two unseen posts, but we only have to "see" the '\
              'latest to see the whole topic'
        self.assertTrue(self.is_post_new(post_ids[-1]), msg)
        self.assertFalse(self.is_post_new(post_ids[-1]), msg)
        self.assertFalse(self.is_topic_new(2), msg)
        self.assertFalse(self.is_post_new(post_ids[1]),
                         "second post should be also seen now")

    def is_post_new(self, post_id):
        post_isnew_key = "post-is-new:{}".format(post_id)
        post_isnew_url = "{}?wid={}".format(WIDGETS_URL, post_isnew_key)
        response = self.client.get(post_isnew_url)
        self.assertEqual(response.status_code, 200)
        resp = json.loads(response.content.decode('utf8'))
        return resp[post_isnew_key]['isnew']

    def is_topic_new(self, topic_id):
        topic_isnew_key = "topic-is-new:{}".format(topic_id)
        topic_isnew_url = "{}?wid={}".format(WIDGETS_URL, topic_isnew_key)
        response = self.client.get(topic_isnew_url)
        self.assertEqual(response.status_code, 200)
        resp = json.loads(response.content.decode('utf8'))
        return resp[topic_isnew_key]['isnew']

    def tearDown(self):
        self.user.delete()


class TopicViewCountTest(TestCase):
    fixtures = ['forum/tests/small_size_forum.yaml']

    def test_topic_view_count(self):
        topic = Topic.objects.get(pk=1)
        widget_key = 'topic-view-count:{}'.format(topic.id)
        self.assertEqual(self.counter_value(widget_key), 0)
        self.client.get(topic.get_absolute_url())
        self.assertEqual(self.counter_value(widget_key), 1)
        self.client.get(topic.get_absolute_url())
        self.assertEqual(self.counter_value(widget_key), 2)

    def counter_value(self, key):
        response = self.client.get("{}?wid={}".format(WIDGETS_URL, key))
        self.assertEqual(response.status_code, 200)
        resp = json.loads(response.content.decode('utf8'))
        return resp[key]['counter']


