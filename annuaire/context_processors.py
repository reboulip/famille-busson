from django.conf import settings


def site_version(request) -> dict[str, str]:
    return {"site_version": settings.APP_VERSION}
