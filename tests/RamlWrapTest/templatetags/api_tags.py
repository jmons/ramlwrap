from django import template
from django.utils.html import format_html
import json
import re

register = template.Library()

@register.filter
def hash(h, key):
    return h[key]

@register.filter
def json_dump(obj):
    return json.dumps(obj)