from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import Client, TestCase
from django.test.utils import override_settings

from forum.models import Topic, Post


class PostCreationTest(TestCase):
    fixtures = ['forum/tests/small_size_forum.yaml']

    def setUp(self):
        u = get_user_model().objects.get(username='bobross')
        u.set_password('a')
        u.save()
        self.client = Client()
        self.assertTrue(self.client.login(username='bobross', password='a'))

    def test_post_create(self):
        topic = Topic.objects.get(pk=2)
        self.assertEqual(topic.response_count, 3)
        url = reverse('forum:post-create', args=(topic.pk, ))
        data = {'content': 'comment by bob'}
        resp = self.client.post(url, data)
        post = topic.posts.order_by('-created')[0]
        topic = Topic.objects.get(pk=2)
        self.assertEqual(post.content, data['content'])
        self.assertEqual(post.author.username, 'bobross')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(topic.response_count, 4)
        self.assertEqual(topic.response_count, topic.posts.count() - 1)
        self.assertEqual(topic.updated, post.created)


class PostDetailsPageTest(TestCase):
    fixtures = ['forum/tests/small_size_forum.yaml']

    @override_settings(FORUM_POSTS_PER_PAGE=2)
    def test_redirects(self):
        test_data = (
            (2, 2, 'topic/second-topic_2013-09-02/2/#post-2'),
            (2, 3, 'topic/second-topic_2013-09-02/2/#post-3'),
            (2, 4, 'topic/second-topic_2013-09-02/2/?page=2#post-4'),
            (2, 5, 'topic/second-topic_2013-09-02/2/?page=2#post-5'),
        )
        for topic_pk, post_pk, url_suffix in test_data:
            resp = self.client.get(
                    reverse('forum:post-details', args=(topic_pk, post_pk,)))
            self.assertEqual(resp.status_code, 302)
            self.assertTrue(resp.url.endswith(url_suffix),
                            "{} does not end with {}".format(resp.url, url_suffix))

    def test_redirect_post_deleted(self):
        post = Post.objects.get(pk=2)
        post.is_deleted = True
        post.save()
        resp = self.client.get(
                reverse('forum:post-details', args=(post.topic_id, post.pk, )))
        self.assertEqual(resp.status_code, 404)

    def test_redirect_topic_deleted(self):
        post = Post.objects.get(pk=2)
        post.topic.is_deleted = True
        post.topic.save()
        resp = self.client.get(
                reverse('forum:post-details', args=(post.topic_id, post.pk, )))
        self.assertEqual(resp.status_code, 404)


class PostMarkAsSolvingTest(TestCase):
    fixtures = ['forum/tests/small_size_forum.yaml']

    def setUp(self):
        u = get_user_model().objects.get(id=2)
        u.set_password('a')
        u.save()
        self.client = Client()
        self.assertTrue(self.client.login(username=u.username, password='a'))

    def test_any_post_solving_is_solving_topic(self):
        topic_id = 2

        def toggle_solve_post(post_id):
            url = reverse("forum:post-toggle-is-solving", args=(topic_id, post_id))
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302)

        def topic_is_solved():
            return Topic.objects.filter(id=topic_id, is_solved=True).exists()

        self.assertFalse(topic_is_solved())
        toggle_solve_post(3)
        self.assertTrue(topic_is_solved())
        toggle_solve_post(4)
        self.assertTrue(topic_is_solved())
        toggle_solve_post(4)
        self.assertTrue(topic_is_solved())
        toggle_solve_post(3)
        self.assertFalse(topic_is_solved())

    def test_solving_does_not_change_post_order(self):
        topic_id = 2

        def toggle_solve_post(post_id):
            url = reverse("forum:post-toggle-is-solving", args=(topic_id, post_id))
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302)

        def assert_posts_order(expected_order):
            url = reverse("forum:posts-list", args=(topic_id, ))
            resp = self.client.get(url)
            posts = resp.context['posts'].object_list
            post_ids = [p.id for p in posts]
            self.assertEqual(list(expected_order), list(post_ids))

        assert_posts_order([2, 3, 4])
        toggle_solve_post(3)
        assert_posts_order([2, 3, 4])
        toggle_solve_post(3)
        assert_posts_order([2, 3, 4])
        toggle_solve_post(4)
        toggle_solve_post(5)
        assert_posts_order([2, 3, 4])


class PostDeleteTest(TestCase):
    fixtures = ['forum/tests/small_size_forum.yaml']

    def setUp(self):
        u = get_user_model().objects.get(id=2)
        u.set_password('a')
        u.save()
        self.client = Client()
        self.assertTrue(self.client.login(username=u.username, password='a'))

    def post_toggle_delete(self, topic_id, post_id):
        url = reverse("forum:post-toggle-delete", args=(topic_id, post_id))
        return self.client.get(url)
