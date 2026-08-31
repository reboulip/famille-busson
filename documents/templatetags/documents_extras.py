from django import template

from documents.access import effective_groups as _effective_groups
from documents.access import user_can_access_category

register = template.Library()


@register.filter
def can_access(category, user):
    return user_can_access_category(user, category)


@register.filter
def effective_groups(category):
    return _effective_groups(category)
