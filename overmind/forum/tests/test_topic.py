from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse

from forum.models import Topic


class TopicCreationTest(TestCase):
    fixtures = ['forum/tests/small_size_forum.yaml']

    def setUp(self):
        u = get_user_model().objects.get(username='bobross')
        u.set_password('a')
        u.save()
        self.client = Client()
        self.assertTrue(self.client.login(username='bobross', password='a'))

    def test_topic_creation(self):
        topics_count = Topic.objects.count()
        url = reverse('forum:topic-create')
        data = {
            'subject': 'my own topic',
            'content': 'init content of my topic',
            'tags': [1, 3],
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(topics_count + 1, Topic.objects.count())
        topic = Topic.objects.order_by('-created')[0]
        self.assertEqual(topic.subject, data['subject'])
        self.assertEqual(topic.response_count, 0)
        self.assertEqual(topic.posts.count(), 1)
        post = topic.posts.all()[0]
        self.assertEqual(post.author.username, 'bobross')
