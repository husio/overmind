import datetime
import math

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.core.urlresolvers import reverse
from django.db import connection, transaction
from django.db.models import Q
from django.http import HttpResponseForbidden, HttpResponseGone
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import utc
from django.views.decorators.cache import never_cache

from . import cache, permissions
from .models import Topic, Post, Tag, LastSeen, PostHistory, TopicHistory
from .forms import TopicForm, PostForm, SearchForm


@never_cache
def posts_search(request):
    form = SearchForm()
    if request.GET.get('pattern', None):
        form = SearchForm(request.GET)

    if form.is_valid():
        posts = Post.objects.exclude(is_deleted=True)\
                .select_related().order_by('-created')
        tag_labels = request.GET.getlist('tag')
        if tag_labels:
            posts = posts.filter(topic__tags__label__in=tag_labels).distinct()
        pattern = form.cleaned_data.get('pattern')
        posts = posts.filter(content__icontains=pattern)
    else:
        posts = Post.objects.none()

    paginator = Paginator(posts,
                          getattr(settings, 'FORUM_SEARCH_RESULT_PER_PAGE', 25))
    try:
        page = paginator.page(request.GET.get('page', 1))
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    tags = []
    for tag in Tag.objects.list_all():
        tags.append({
            'label': tag.label,
            'checked': tag.label in request.GET.getlist('tag'),
        })
    ctx = {
        'form': form,
        'posts': page,
        'tags': tags,
        'pattern': form.is_valid() and form.cleaned_data.get('pattern', None),
    }
    return render(request, 'forum/posts_search.html', ctx)


def topics_list(request):
    topics = Topic.objects.exclude(is_deleted=True).select_related()\
            .prefetch_related('tags').order_by('-updated')

    tag_labels = request.GET.getlist('tag')
    if tag_labels:
        topics = topics.filter(tags__label__in=tag_labels).distinct()

    paginator = Paginator(topics, settings.FORUM_TOPICS_PER_PAGE)
    try:
        page = paginator.page(request.GET.get('page', 1))
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    tags = []
    for tag in Tag.objects.list_all():
        tags.append({
            'label': tag.label,
            'checked': tag.label in request.GET.getlist('tag'),
        })

    ctx = {
        'topics': page,
        'tags': tags,
        'POSTS_PER_PAGE': settings.FORUM_POSTS_PER_PAGE,
    }
    return render(request, 'forum/topics_list.html', ctx)


def posts_list(request, topic_pk):
    topic = get_object_or_404(Topic, pk=topic_pk)
    if topic.is_deleted:
        return HttpResponseGone()
    posts = Post.objects.filter(topic=topic, is_deleted=False)\
            .select_related('author').order_by('created')
    paginator = Paginator(posts, settings.FORUM_POSTS_PER_PAGE)
    paginator._count = topic.posts_count()
    try:
        page = paginator.page(request.GET.get('page', 1))
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    topic.view_count += 1
    topic.save()

    ctx = {
        'topic': topic,
        'posts': page,
    }
    return render(request, 'forum/posts_list.html', ctx)


@never_cache
def post_details(request, topic_pk, post_pk):
    "Redirect to topic details page, on which given post can be found"
    query = Post.objects.exclude(Q(topic__is_deleted=True) | Q(is_deleted=True))
    post = get_object_or_404(query.select_related(), pk=post_pk)
    cursor = connection.cursor()
    sql = """
        SELECT
            COUNT(*)
        FROM
            {post_table_name}
        WHERE
            topic_id = %s
            AND NOT is_deleted
            AND created < %s
    """.format(post_table_name=Post._meta.db_table)

    cursor.execute(sql, [post.topic_id, post.created])
    (position, ) = cursor.fetchone()
    page = math.ceil((position + 1) / settings.FORUM_POSTS_PER_PAGE)
    url = post.topic.get_absolute_url()
    if page > 1:
        url += '?page={}'.format(page)
    url += '#post-{}'.format(post_pk)
    return redirect(url)


@never_cache
def posts_list_last_page(request, topic_pk):
    topic = get_object_or_404(Topic, pk=topic_pk)
    if topic.is_deleted:
        return HttpResponseGone()
    return redirect(topic.get_absolute_url(last_page=True))


@never_cache
@login_required
def topic_create(request):
    perm_manager = permissions.manager_for(request.user)
    if not perm_manager.can_create_topic():
        return HttpResponseForbidden()

    if request.method == 'POST':
        topic = Topic(author=request.user)
        form = TopicForm(request.POST, instance=topic)
        form = TopicForm(request.POST, instance=topic)
        if form.is_valid():
            ip = request.META.get('REMOTE_ADDR')
            topic = form.save(ip)
            cache.expire_group('topic:all')
            return redirect(topic.get_absolute_url())
    else:
        form = TopicForm()
    ctx = {'form': form}
    return render(request, 'forum/topic_create.html', ctx)


@never_cache
@login_required
def post_create(request, topic_pk):
    topic = get_object_or_404(Topic, pk=topic_pk)

    perm_manager = permissions.manager_for(request.user)
    if not perm_manager.can_create_post(topic):
        return HttpResponseForbidden()

    if request.method == 'POST':
        with transaction.autocommit():
            post = Post(topic=topic, author=request.user)
            form = PostForm(request.POST, instance=post)
            if form.is_valid():
                post = form.save(commit=False)
                post.ip = request.META.get('REMOTE_ADDR')
                post.save()
                posts_count = topic.posts.exclude(is_deleted=True).count()
                topic.response_count = posts_count - 1
                topic.updated = post.created
                topic.content_updated = post.created
                topic.save()
                cache.expire_groups((
                    'topic:all',
                    'topic:{}'.format(topic.pk),
                ))
                return redirect(post.get_absolute_url())
    else:
        form = PostForm()
    ctx = {'topic': topic, 'form': form}
    return render(request, 'forum/post_create.html', ctx)


@never_cache
@login_required
def mark_all_topics_read(request):
    now = datetime.datetime.now().replace(tzinfo=utc)
    last_seen = LastSeen.obtain_for(request.user)
    last_seen.last_seen_all = now
    last_seen.seen_topics = {}
    last_seen.save()
    return redirect(request.META.get('HTTP_REFERER', reverse('forum:topics-list')))


def user_details(request, user_pk):
    user = get_object_or_404(get_user_model(), pk=user_pk)
    topics = Topic.objects.filter(is_deleted=False, author=user)
    posts = Post.objects.filter(is_deleted=False, author=user)
    ctx = {
        'user': user,
        'topics_count': topics.count(),
        'posts_count': posts.count(),
        'latest_topics': topics[:10],
        'latest_posts': posts[:8],
    }
    return render(request, 'forum/user_details.html', ctx)


@never_cache
def topic_toggle_delete(request, topic_pk):
    topic = get_object_or_404(Topic, pk=topic_pk)
    perm_manager = permissions.manager_for(request.user)
    if not perm_manager.can_delete_topic(topic):
        return HttpResponseForbidden()

    action = 'recovered' if topic.is_deleted else 'deleted'
    TopicHistory.objects.create(topic=topic, action=action, author=request.user)

    topic.is_deleted = not topic.is_deleted
    now = datetime.datetime.now().replace(tzinfo=utc)
    topic.updated = now
    topic.content_updated = now
    topic.save()
    cache.expire_groups((
        'topic:all',
        'topic:{}'.format(topic.pk),
    ))
    url = request.META.get('HTTP_REFERER', None)
    if not url:
        url = topic.get_absolute_url()
    return redirect(url)


@never_cache
@transaction.atomic
def topic_toggle_close(request, topic_pk):
    topic = get_object_or_404(Topic, pk=topic_pk)
    perm_manager = permissions.manager_for(request.user)
    if not perm_manager.can_close_topic(topic):
        return HttpResponseForbidden()

    topic.is_closed = not topic.is_closed
    now = datetime.datetime.now().replace(tzinfo=utc)
    topic.content_updated = now
    topic.save()

    action = 'closed' if topic.is_closed else 'opened'
    TopicHistory.objects.create(topic=topic, action=action,
                                author=request.user)
    cache.expire_groups((
        'topic:all',
        'topic:{}'.format(topic.pk),
    ))

    url = request.META.get('HTTP_REFERER', None)
    if not url:
        url = topic.get_absolute_url()
    return redirect(url)


@never_cache
@transaction.atomic
def post_toggle_delete(request, topic_pk, post_pk):
    post = get_object_or_404(Post, topic__pk=topic_pk, pk=post_pk)
    perm_manager = permissions.manager_for(request.user)
    if not perm_manager.can_delete_post(post):
        return HttpResponseForbidden()

    action = 'recovered' if post.is_deleted else 'deleted'
    PostHistory.objects.create(post=post, action=action, author=request.user)

    now = datetime.datetime.now().replace(tzinfo=utc)
    post.is_deleted = not post.is_deleted
    post.save()

    topic = post.topic
    topic.content_updated = now
    topic.response_count = topic.posts.filter(is_deleted=False).count()
    topic.save()

    cache.expire_groups((
        'topic:all',
        'topic:{}'.format(post.topic.pk),
    ))
    url = request.META.get('HTTP_REFERER', None)
    if not url:
        url = post.get_absolute_url()
    return redirect(url)


@never_cache
@transaction.atomic
def post_toggle_is_solving(request, topic_pk, post_pk):
    post = get_object_or_404(Post, topic__pk=topic_pk, pk=post_pk)
    perm_manager = permissions.manager_for(request.user)
    if not perm_manager.can_solve_topic_with_post(post):
        return HttpResponseForbidden()


    post.is_solving = not post.is_solving

    action = 'solving' if post.is_solving else 'not_solving'
    PostHistory.objects.create(post=post, action=action, author=request.user)

    topic = post.topic
    topic_is_solved = post.is_solving or \
                      topic.posts.filter(is_solving=True).count() > 1
    if topic.is_solved != topic_is_solved:
        topic.is_solved = topic_is_solved
        action = 'solved' if topic_is_solved else 'not_solved'
        TopicHistory.objects.create(topic=post.topic, action=action,
                                    author=request.user)

    now = datetime.datetime.now().replace(tzinfo=utc)
    post.save()
    topic.content_updated = now
    topic.save()

    cache.expire_groups((
        'topic:all',
        'topic:{}'.format(topic.pk),
    ))

    url = request.META.get('HTTP_REFERER', None)
    if not url:
        url = topic.get_absolute_url()
    return redirect(url)


@never_cache
@transaction.atomic
def post_edit(request, topic_pk, post_pk):
    post = get_object_or_404(Post, topic__pk=topic_pk, pk=post_pk)
    perm_manager = permissions.manager_for(request.user)
    if not perm_manager.can_edit_post(post):
        return HttpResponseForbidden()

    if request.method == "POST":
        old_content = post.content
        form = PostForm(request.POST, instance=post)
        if form.is_valid():

            # nothing changed
            if post.content == old_content:
                return redirect(post.get_absolute_url())

            now = datetime.datetime.now().replace(tzinfo=utc)
            post.updated = now
            PostHistory.objects.create(
                    post=post, action='content_changed', author=request.user,
                    prev_content=old_content, created=now)
            post = form.save()
            post.topic.updated = now
            post.topic.content_updated = now
            post.topic.save()
            cache.expire_groups((
                'topic:all',
                'topic:{}'.format(post.topic_id),
            ))
            return redirect(post.get_absolute_url())
    else:
        form = PostForm(instance=post)

    ctx = {'form': form, 'post': post}
    return render(request, "forum/post_edit.html", ctx)


@never_cache
@login_required
def post_report_as_spam(request, topic_pk, post_pk):
    post = get_object_or_404(Post, is_deleted=False, topic__pk=topic_pk,
                             pk=post_pk)
    _, created = PostHistory.objects.get_or_create(
            post=post, author=request.user, action='spam_reported')
    if created:
        all_reports = PostHistory.objects.filter(action='spam_reported',
                                                 post=post)
        if all_reports.count() > 5:
            now = datetime.datetime.now().replace(tzinfo=utc)
            post.is_deleted = True
            post.updated = now
            post.save()
            post.topic.updated = now
            post.topic.content_updated = now
            post.topic.save()
            cache.expire_group('topic:{}'.format(post.topic_id))
    dest_url = request.META.get('HTTP_REFERER', None)
    if not dest_url:
        dest_url = post.get_absolute_url()
    return redirect(dest_url)


@never_cache
@login_required
def topic_report_as_spam(request, topic_pk):
    topic = get_object_or_404(Topic, is_deleted=False, pk=topic_pk)
    _, created = TopicHistory.objects.get_or_create(
            topic=topic, author=request.user, action='spam_reported')
    if created:
        all_reports = TopicHistory.objects.filter(action='spam_reported',
                                                  topic=topic)
        if all_reports.count() > 5:
            now = datetime.datetime.now().replace(tzinfo=utc)
            topic.is_deleted = True
            topic.updated = now
            topic.content_updated = now
            topic.save()
            cache.expire_groups((
                'topic:all',
                'topic:{}'.format(topic.pk),
            ))
    dest_url = request.META.get('HTTP_REFERER', None)
    if not dest_url:
        dest_url = topic.get_absolute_url()
    return redirect(dest_url)


@never_cache
@user_passes_test(lambda u: permissions.manager_for(u).is_moderator())
def latest_reports(request):
    mod_actions = ['deleted', 'spam_reported']
    topics_history = TopicHistory.objects.filter(action__in=mod_actions)\
            .select_related('topic', 'author', 'topic__author')\
            .order_by('-created')
    posts_history  = PostHistory.objects.filter(action__in=mod_actions)\
            .select_related('post', 'post__topic', 'post__author', 'author')\
            .order_by('-created')

    ctx = {
        'topics_history': topics_history[:100],
        'posts_history': posts_history[:100],
    }
    return render(request, 'forum/latest_reports.html', ctx)
