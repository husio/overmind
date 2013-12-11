import re

from django import template
from django.utils.safestring import mark_safe


register = template.Library()


@register.simple_tag
@register.filter
def mark_pattern(text, pattern, fmt=r'**\1**'):
    if pattern:
        rx = r"({})".format(re.escape(pattern))
        text = re.sub(rx, fmt, text, flags=re.IGNORECASE)
    return mark_safe(text)
