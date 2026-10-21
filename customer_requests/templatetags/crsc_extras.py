from django import template

register = template.Library()


@register.filter
def in_list(value, arg):
    tokens = [t.strip() for t in arg.split(",")]
    return value in tokens


@register.filter
def slug_badge(value):
    if not value:
        return ""
    return str(value).replace("/", "-").replace(" ", "-")
