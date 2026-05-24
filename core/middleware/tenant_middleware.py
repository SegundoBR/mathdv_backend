from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest


class TenantMiddleware(MiddlewareMixin):
    """No-op middleware kept for backward compatibility.

    Tenant header/query extraction was removed in favor of UserInstitution-based
    filtering for all multi-tenant access rules.
    """

    def process_request(self, request: HttpRequest):
        request.tenant = None
        return None
