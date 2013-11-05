from django.template import RequestContext
from django.template.loader import render_to_string

from counter import backend
from dynamicwidget.decorators import widget_handler

from . import permissions
from .forms import PostForm
from .models import LastSeen, Post, Topic


@widget_handler(r"^topic-view-count:(?P<tid>\d+)$")
def topic_view_count(request, widgets):
    key_tmpl = "topic:view:{}"
    counter = backend.default()
    keys = [key_tmpl.format(w['params']['tid']) for w in widgets]
    counters = counter.get(*keys)
    res = {}
    for widget in widgets:
        value = counters.get(key_tmpl.format(widget['params']['tid']), 0)
        ctx = {'value': value}
        html = render_to_string('forum/widgets/topic_view_count.html', ctx)
        res[widget['wid']] = {'html': html, 'counter': value}
    return res


@widget_handler(r"^topic-is-new:(?P<tid>\d+)$")
def topic_is_new(request, widgets):
    if request.user.is_anonymous():
        return {w['wid']: {'html': '', 'isnew': False} for w in widgets}

    topics = {}
    query = Topic.objects.filter(id__in=[w['params']['tid'] for w in widgets])
    for topic in query:
        topics[topic.id] = topic
    res = {}
    last_seen = LastSeen.obtain_for(request.user)
    for widget in widgets:
        topic_id = int(widget['params']['tid'])
        latest = last_seen.seen_topics.get(
                str(topic_id), request.user.forum_last_seen.last_seen_all)
        topic = topics.get(topic_id)
        is_new = topic.content_updated.replace(microsecond=0) > latest
        ctx = {'is_new': is_new, 'topic': topic}
        html = render_to_string('forum/widgets/topic_is_new.html', ctx)
        res[widget['wid']] = {'html': html, 'isnew': is_new}
    return res


@widget_handler(r"^topic-attributes:(?P<tid>\d+)$")
def topic_attributes(request, widgets):
    if request.user.is_anonymous():
        return {w['wid']: {'html': ''} for w in widgets}

    topics = {}
    query = Topic.objects.filter(id__in=[w['params']['tid'] for w in widgets])
    for topic in query:
        topics[topic.id] = topic

    perm_manager = permissions.manager_for(request.user)

    res = {}
    for widget in widgets:
        topic = topics[int(widget['params']['tid'])]
        ctx = {
            'topic': topic,
            'can_edit': perm_manager.can_edit_topic(topic),
            'can_delete': perm_manager.can_delete_topic(topic),
            'can_close': perm_manager.can_close_topic(topic),
            'can_report_as_spam': perm_manager.can_report_topic_as_spam(topic),
        }
        html = render_to_string('forum/widgets/topic_attributes.html',
                                RequestContext(request, ctx))
        res[widget['wid']] = {'html': html}
    return res


@widget_handler(r"^login-logout$")
def login_logout(request, widgets):
    ctx = RequestContext(request)
    html = render_to_string('forum/widgets/login_logout.html', ctx)
    return {"login-logout": {"html": html}}


@widget_handler(r"post-is-new:(?P<pid>\d+)$")
def post_is_new(request, widgets):
    if request.user.is_anonymous():
        return {w['wid']: {'html': '', 'isnew': False} for w in widgets}

    last_seen = LastSeen.obtain_for(request.user)
    query = Post.objects.filter(id__in=[w['params']['pid'] for w in widgets])
    posts = {}
    topics = {}
    newest = {}
    for pid, updated, tid in query.values_list('id', 'updated', 'topic_id'):
        updated = updated.replace(microsecond=0)
        posts[pid] = (tid, updated)

        # find out, when the topic was last seen
        if tid not in topics:
            topic_last_seen = last_seen.seen_topics.get(str(tid), last_seen.last_seen_all)
            topic_last_seen = topic_last_seen.replace(microsecond=0)
            topics[tid] = topic_last_seen

        # find the newest post creation date for every related topic
        dt = newest.get(tid)
        if not dt:
            newest[tid] = updated
        elif updated > dt:
            newest[tid] = updated

    res = {}
    for widget in widgets:
        post_id = int(widget['params']['pid'])
        tid, updated = posts[post_id]
        is_new = updated > topics[tid]
        ctx = {'is_new': is_new}
        html = render_to_string('forum/widgets/post_is_new.html', ctx)
        res[widget['wid']] = {'html': html, 'isnew': is_new}

    # make sure, we have all topics marked as "seen" with appropriate, fresh
    # date from the newest post we ask for
    for tid, newest_post_dt in newest.items():
        if newest_post_dt > topics[tid]:
            last_seen.seen_topics[str(tid)] = newest_post_dt
            last_seen.save()

    return res


@widget_handler(r"^post-attributes:(?P<pid>\d+)$")
def post_attributes(request, widgets):
    if request.user.is_anonymous():
        return {w['wid']: {'html': ''} for w in widgets}

    posts = {}
    query = Post.objects.filter(id__in=[w['params']['pid'] for w in widgets])
    for post in query:
        posts[post.id] = post

    perm_manager = permissions.manager_for(request.user)

    res = {}
    for widget in widgets:
        post = posts[int(widget['params']['pid'])]
        ctx = {
            'post': post,
            'can_edit': perm_manager.can_edit_post(post),
            'can_delete': perm_manager.can_delete_post(post),
            'can_report_as_spam': perm_manager.can_report_post_as_spam(post),
            'can_solve': perm_manager.can_solve_topic_with_post(post),
        }
        html = render_to_string('forum/widgets/post_attributes.html',
                                RequestContext(request, ctx))
        res[widget['wid']] = {'html': html}
    return res


@widget_handler(r"^topic-comment-form:(?P<tid>\d+)$")
def topic_comment_form(request, widgets):
    if request.user.is_anonymous():
        return {w['wid']: {'html': ''} for w in widgets}

    perm_manager = permissions.manager_for(request.user)

    topics = {}
    topic_ids = [w['params']['tid'] for w in widgets]
    for topic in Topic.objects.filter(id__in=topic_ids):
        topics[topic.id] = topic

    form = PostForm()
    res = {}
    ctx = RequestContext(request, {'form': form, 'user': request.user})
    for widget in widgets:
        topic = topics[int(widget['params']['tid'])]
        if not perm_manager.can_create_post(topic):
            html = ''
        else:
            ctx['topic'] = topic
            html = render_to_string('forum/widgets/topic_comment_form.html', ctx)
        res[widget['wid']] = {'html': html}
    return res


@widget_handler(r"^logged-user-actions$")
def logged_user_actions(request, widgets):
    ctx = RequestContext(request)
    html = render_to_string('forum/widgets/logged_user_actions.html', ctx)
    return {"logged-user-actions": {"html": html}}
