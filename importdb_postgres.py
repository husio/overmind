#!/usr/bin/env python
import getpass
import random
import re

import psycopg2



TAGS = [
    'Beginner',
    'Installation',
    'Kernel & Hardware',
    'Desktop Environment',
    'Laptop',
    'Networking',
    'Games',
    'Multimedia',
    'Administration',
    'About forum',
    'Pacman',
    'Random',
]


_bbcode_to_markdown = (
    (re.compile(r'\[b\]((?:.|\n)+?)\[\/b\]'), "**\1**"),
    (re.compile(r'\[u\]((?:.|\n)+?)\[\/u\]'), "*\1*"),
    (re.compile(r'\[s\]((?:.|\n)+?)\[\/s\]'), "~~\1~~"),
    (re.compile(r'\[color\=.+?\]((?:.|\n)+?)\[\/color\]'), "\1"),
    (re.compile(r'(\n)\[\*\]'), "\1* "),
    (re.compile(r'\[\/*list\]'), ''),
    (re.compile(r'\[img\]((?:.|\n)+?)\[\/img\]'), '![](\1)'),
    (re.compile(r'\[url=(.+?)\]((?:.|\n)+?)\[\/url\]'), '[\2](\1)'),
    # TODO - [code]
    # TODO - [quote]
)


def bbcode_to_markdown(text):
    for rx, repl in _bbcode_to_markdown:
        text = rx.sub(repl, text)
    return text


def copy_users(pg_connection, sqlt_connection):
    pg_c = pg_connection.cursor()
    pg_c.execute('''
        SELECT
            id, username, first_name, last_name, last_login, email,
            date_joined
        FROM
            auth_user
    ''')

    sqlt_c = sqlt_connection.cursor()
    for row in pg_c:
        sqlt_c.execute('''
            INSERT INTO
                auth_user(id, username, first_name, last_name, password,
                last_login, is_superuser, email, is_staff, is_active,
                date_joined)
                VALUES (%s, %s, %s, %s, '-', %s, false, %s, false, false, %s)
            ''', row)
    pg_c.close()


def copy_topics(pg_connection, sqlt_connection):
    pg_c = pg_connection.cursor()
    pg_c.execute('''
    SELECT
        id, user_id, name, created, post_count
    FROM
        djangobb_forum_topic
    ''')

    sqlt_c = sqlt_connection.cursor()
    for tag in TAGS:
        sqlt_c.execute('''
            INSERT INTO forum_tag(label, description)
            VALUES (%s, '')
        ''', (tag, ))
    for row in pg_c:
        sqlt_c.execute('''
            INSERT INTO forum_topic(id, author_id, subject, created, updated,
                                    content_updated, response_count,
                                    is_deleted, is_closed, is_solved,
                                    view_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, false, false, false, 0)
        ''', [row[0], row[1], row[2], row[3], row[3], row[3], row[4] - 1])
        attached_tags = {None}
        for _ in range(random.randint(1, 5)):
            tid = None
            while tid in attached_tags:
                tid = random.randint(1, len(TAGS))
            attached_tags.add(tid)

            sqlt_c.execute('''
                INSERT INTO forum_topic_tags (topic_id, tag_id )
                VALUES (%s, %s)
            ''', (row[0], tid))

    pg_c.close()


def copy_posts(pg_connection, sqlt_connection):
    pg_c = pg_connection.cursor()
    pg_c.execute('''
    SELECT
        id, topic_id, user_id, body, created, user_ip
    FROM
        djangobb_forum_post
    ''')

    sqlt_c = sqlt_connection.cursor()
    for row in pg_c:
        row = list(row)
        row[3] = bbcode_to_markdown(row[3])
        row.append(False)
        sqlt_c.execute('''
            INSERT INTO forum_post(id, topic_id, author_id, content, created,
                                   updated, ip, is_deleted, is_solving)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, false)
        ''', [row[0], row[1], row[2], row[3], row[4], row[4], row[5], row[6]])
    pg_c.close()



def main():
    pg_conn = psycopg2.connect(
            dbname="pg_5908", user="pg_5908u", host='archlinux.megiteam.pl',
            port=5435, password=getpass.getpass('archlinux database password:'))
    sqlt_connection = psycopg2.connect(dbname='overmind')
    copy_users(pg_conn, sqlt_connection)
    copy_topics(pg_conn, sqlt_connection)
    copy_posts(pg_conn, sqlt_connection)
    pg_conn.close()
    sqlt_connection.commit()

if __name__ == "__main__":
    main()
