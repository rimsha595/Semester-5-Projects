from django import template

register = template.Library()

@register.filter
def matches_item(value, other):
    return other.lower() in value.lower()

