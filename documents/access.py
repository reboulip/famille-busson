from documents.models import Category, Document


def effective_groups(category):
    """Walk from category up through its ancestors, returning the groups of the
    nearest ancestor-or-self that has its own groups set. Empty list if none in
    the chain does (fully public). A restricted category's descendants inherit
    its groups rather than setting their own -- see Category's m2m_changed
    receiver, which enforces that only one category per ancestry chain can be
    directly restricted."""
    node = category
    while node is not None:
        groups = list(node.groups.all())
        if groups:
            return groups
        node = node.parent
    return []


def user_can_access_category(user, category):
    if user.is_staff or user.is_superuser:
        return True
    groups = effective_groups(category)
    if not groups:
        return True
    user_group_ids = set(user.groups.values_list("id", flat=True))
    return any(group.id in user_group_ids for group in groups)


def accessible_categories(user):
    """The fully-open subset of categories -- used for upload category
    selectors and document listing/search, which must never leak a locked
    category's contents. Category *listing/tree* views should query
    Category.objects.all() directly instead (every category is visible in
    listings, just locked when not accessible -- see the sprint brief)."""
    if user.is_staff or user.is_superuser:
        return Category.objects.all()

    all_categories = list(Category.objects.all().prefetch_related("groups"))
    by_id = {category.id: category for category in all_categories}
    user_group_ids = set(user.groups.values_list("id", flat=True))

    def _is_accessible(category):
        node = category
        while node is not None:
            groups = list(node.groups.all())
            if groups:
                return any(group.id in user_group_ids for group in groups)
            node = by_id.get(node.parent_id) if node.parent_id else None
        return True

    accessible_ids = [category.id for category in all_categories if _is_accessible(category)]
    return Category.objects.filter(id__in=accessible_ids)


def accessible_documents(user):
    return Document.objects.filter(category__in=accessible_categories(user))
