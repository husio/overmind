from django.conf import settings
from django.utils.importlib import import_module


def manager():
    cls_path = getattr(settings, 'FORUM_PERMISSIONS_MANAGER',
                       'forum.permissions.simple.SimpleManager')
    path, clsname = cls_path.rsplit('.', 1)
    module = import_module(path)
    cls = getattr(module, clsname)
    return cls


def manager_for(user):
    return manager()(user)
