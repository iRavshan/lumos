from apps.team.models import StaffMember


class StaffBusinessMiddleware:
    """
    Agar tizimga xodim (operator yoki supervisor) login qilgan bo'lsa (username staff_<id> shaklida),
    request.user.business va request.user.staff_member ni uning korxonasiga ulab beradi.
    Shu tariqa xodim vebsaytda o'z biznesining murojaatlari va suhbatlarini bemalol ko'ra oladi.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Check if user already has a valid business (owner)
            is_owner = False
            try:
                if hasattr(request.user, 'business') and request.user.business:
                    is_owner = True
            except Exception:
                is_owner = False

            if not is_owner and request.user.username.startswith('staff_'):
                parts = request.user.username.split('_')
                if len(parts) >= 2 and parts[1].isdigit():
                    staff_id = int(parts[1])
                    staff = StaffMember.objects.select_related('business').filter(id=staff_id, is_active=True).first()
                    if staff:
                        request.user.business = staff.business
                        request.user.staff_member = staff

        return self.get_response(request)
