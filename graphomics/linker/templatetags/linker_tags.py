from django import template

register = template.Library()


@register.simple_tag
def get_read_only_status(analysis, user):
    return analysis.get_read_only_status(user)


@register.simple_tag
def get_read_only_str(analysis, user):
    return analysis.get_read_only_str(user)
