def neighbours(photo):
    """Return `(previous_photo, next_photo)` within the same album, in the
    canonical chronological order (`Photo.objects.chronological()`). Defined
    once here so the lightbox and photo-detail prev/next navigation (later
    items) never re-derive the ordering independently and risk disagreeing
    about what "next" means."""
    ordered = list(photo.album.photos.chronological())
    try:
        index = ordered.index(photo)
    except ValueError:
        return None, None
    previous_photo = ordered[index - 1] if index > 0 else None
    next_photo = ordered[index + 1] if index < len(ordered) - 1 else None
    return previous_photo, next_photo
