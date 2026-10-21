from django import template

register = template.Library()


@register.filter
def slug_badge(value):
    """'DEALER/CUSTOMER' -> 'DEALER-CUSTOMER' for use in a CSS class name."""
    if not value:
        return ""
    return str(value).replace("/", "-").replace(" ", "-")


@register.filter
def in_list(value, arg):
    """
    Exact membership test against a comma-separated string, e.g.:
        {% if field.name|in_list:"request_remarks,request_comments,attending_engineer" %}
    Needed because Django's built-in `in` operator does a *substring* test
    on strings (so "ro" would match inside "requested_by"); this splits
    `arg` into real tokens first and compares exactly.
    """
    tokens = [t.strip() for t in arg.split(",")]
    return value in tokens
