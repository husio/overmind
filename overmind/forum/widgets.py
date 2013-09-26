import datetime

from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.timezone import utc

from forum.forms import PostForm
from forum.models import Topic, Post, LastSeen, Moderator
from counter import backend
from dynamicwidget.decorators import widget_handler


@widget_handler(r"^topic-view-count:(?P<tid>\d+)$")
def topic_view_count(request, widgets):
    key_tmpl = "topic:view:{}"
    counter = backend.default()
    keys = [key_tmpl.format(w['params']['tid']) for w in widgets]
    counters = counter.get(*keys)
    res = {}
    for widget in widgets:
        value = counters.get(key_tmpl.format(widget['params']['tid']), 0)
        res[widget['wid']] = {
            'html': str(value),
            'counter': value,
        }
    return res


@widget_handler(r"^topic-is-new:(?P<tid>\d+)$")
def topic_is_new(request, widgets):
    if request.user.is_anonymous():
        return {w['wid']: {'html': '', 'isnew': False} for w in widgets}

    topics = {}
    query = Topic.objects.filter(id__in=[w['params']['tid'] for w in widgets])
    for tid, updated in query.values_list('id', 'updated'):
        topics[tid] = updated
    res = {}
    last_seen = LastSeen.obtain_for(request.user)
    for widget in widgets:
        topic_id = int(widget['params']['tid'])
        latest = last_seen.seen_topics.get(
                str(topic_id), request.user.forum_last_seen.last_seen_all)
        updated = topics.get(topic_id)
        if updated.replace(microsecond=0) <= latest:
            res[widget['wid']] = {'html': '', 'isnew': False}
        else:
            res[widget['wid']] = {'html': '*', 'isnew': True}
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
    for pid, created, tid in query.values_list('id', 'created', 'topic_id'):
        created = created.replace(microsecond=0)
        posts[pid] = (tid, created)

        # find out, when the topic was last seen
        if tid not in topics:
            topic_last_seen = last_seen.seen_topics.get(str(tid), last_seen.last_seen_all)
            topic_last_seen = topic_last_seen.replace(microsecond=0)
            topics[tid] = topic_last_seen

        # find the newest post creation date for every related topic
        dt = newest.get(tid)
        if not dt:
            newest[tid] = created
        elif created > dt:
            newest[tid] = created

    res = {}
    for widget in widgets:
        post_id = int(widget['params']['pid'])
        tid, created = posts[post_id]
        is_new = created > topics[tid]
        if is_new:
            res[widget['wid']] = {'html': 'new', 'isnew': True}
        else:
            res[widget['wid']] = {'html': '', 'isnew': False}

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

    is_moderator = Moderator.objects.filter(user=request.user).exists()
    posts = {}
    if not is_moderator:
        post_ids = [w['params']['pid'] for w in widgets]
        query = Post.objects.filter(id__in=post_ids).values('id', 'author',
                                                            'created')
        for post in query:
            posts[post['id']] = post

    res = {}
    edit_limit_date = datetime.datetime.now().replace(tzinfo=utc) \
                      - datetime.timedelta(minutes=10)
    for widget in widgets:
        if is_moderator:
            ctx = {
                'post': {'id': widget['params']['pid']},
                'can_edit': True,
                'can_close': True,
            }
        else:
            post = posts[int(widget['params']['pid'])]
            ctx = {
                'post': post,
                'can_edit': post['author'] == request.user.id \
                            and post['created'] > edit_limit_date,
                'can_close': False,
            }

        html = render_to_string('forum/widgets/post_attributes.html',
                                RequestContext(request, ctx))
        res[widget['wid']] = {'html': html}

    return res


@widget_handler(r"^topic-comment-form:(?P<tid>\d+)$")
def topic_comment_form(request, widgets):
    if request.user.is_anonymous():
        return {w['wid']: {'html': ''} for w in widgets}

    form = PostForm()
    res = {}
    ctx = RequestContext(request, {'form': form})
    for widget in widgets:
        ctx['topic_id'] = widget['params']['tid']
        html = render_to_string('forum/widgets/topic_comment_form.html', ctx)
        res[widget['wid']] = {'html': html}
    return res
