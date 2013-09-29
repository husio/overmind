import datetime

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.urlresolvers import reverse
from django.conf import settings
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.timezone import utc
from django.views.decorators.http import condition

from forum import permissions
from forum.models import Topic, Post, Tag, LastSeen
from forum.forms import TopicForm, PostForm, SearchForm
from counter import backend


def posts_search(request):
    form = SearchForm()

    if request.GET.get('pattern', None):
        form = SearchForm(request.GET)
    else:
        form = SearchForm()

    if form.is_valid():
        posts = Post.objects.select_related().order_by('-created')
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
    for tag in Tag.objects.all():
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



def _latest_topics_update(request):
    if not getattr(settings, 'HTTP_CACHE', True):
        return None
    if request.GET.get('q'):
        return None
    if request.GET.get('page', '1') != '1':
        return None
    topics = Topic.objects.select_related().order_by('-updated')
    tag_labels = request.GET.getlist('tag')
    if tag_labels:
        topics = topics.filter(tags__label__in=tag_labels)
    try:
        return topics[0].updated
    except IndexError:
        return None


@condition(last_modified_func=_latest_topics_update)
def topics_list(request):
    topics = Topic.objects.select_related().prefetch_related('tags')\
            .order_by('-updated')

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
    for tag in Tag.objects.all():
        tags.append({
            'label': tag.label,
            'checked': tag.label in request.GET.getlist('tag'),
        })

    ctx = {
        'topics': page,
        'tags': tags,
    }
    return render(request, 'forum/topics_list.html', ctx)


def _latest_topic_update(request, topic_pk):
    if not getattr(settings, 'HTTP_CACHE', True):
        return None
    topic = get_object_or_404(Topic, pk=topic_pk)
    return topic.updated


@condition(last_modified_func=_latest_topic_update)
def posts_list(request, topic_pk):
    topic = get_object_or_404(Topic, pk=topic_pk)
    posts = Post.objects.filter(topic=topic)\
            .select_related('author').order_by('created')
    paginator = Paginator(posts, settings.FORUM_POSTS_PER_PAGE)
    try:
        page = paginator.page(request.GET.get('page', 1))
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    # this is not always called (condition cache decorator), but that's good
    # thing. It means that the same user is not bumping the counter all the
    # time
    counter = backend.default()
    counter.increment('topic:view:{}'.format(topic.pk))

    ctx = {
        'topic': topic,
        'posts': page,
    }
    return render(request, 'forum/posts_list.html', ctx)


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
            return redirect(topic.get_absolute_url())
    else:
        form = TopicForm()
    ctx = {'form': form}
    return render(request, 'forum/topic_create.html', ctx)


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
                topic.response_count = topic.posts.count() - 1
                topic.updated = post.created
                topic.save()
                return redirect(post.get_absolute_url())
    else:
        form = PostForm()
    ctx = {'topic': topic, 'form': form}
    return render(request, 'forum/post_create.html', ctx)


@login_required
def mark_all_topics_read(request):
    now = datetime.datetime.now().replace(tzinfo=utc)
    last_seen = LastSeen.obtain_for(request.user)
    last_seen.last_seen_all = now
    last_seen.seen_topics = {}
    last_seen.save()
    return redirect(request.META.get('HTTP_REFERER', reverse('forum:topics-list')))
