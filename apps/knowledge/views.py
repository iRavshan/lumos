"""
Bilimlar bazasi sinxronizatsiya API endpointlari.
Dashboard dan "Hoziroq sinxronlash" tugmasini qo'llab-quvvatlaydi.
"""

import threading
import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


@login_required
@require_POST
def sync_knowledge_view(request):
    """
    AJAX endpoint: Bilimlar bazasini qo'lda sinxronlash.
    Background threadda ishlaydi, shunda HTTP javob tezda qaytadi.
    """
    if not hasattr(request.user, 'business'):
        return JsonResponse({'error': 'Biznes topilmadi'}, status=404)

    business = request.user.business

    has_website = bool(business.website and business.website.strip())
    has_telegram = bool(business.telegram and business.telegram.strip())

    if not has_website and not has_telegram:
        return JsonResponse({
            'error': 'Vebsayt yoki Telegram manba kiritilmagan',
            'status': 'no_source',
        }, status=400)

    # Allaqachon jarayonda bo'lsa, takror boshlashning oldini olish
    from .models import KnowledgeSyncLog
    running = KnowledgeSyncLog.objects.filter(
        business=business,
        status='running',
    ).exists()

    if running:
        return JsonResponse({
            'status': 'already_running',
            'message': 'Sinxronizatsiya allaqachon jarayonda',
        })

    # Background threadda sinxronlash
    def _run_sync():
        try:
            from .tasks import scrape_and_embed
            scrape_and_embed(business, triggered_by='manual')
        except Exception as e:
            logger.error("Manual sync xatolik (%s): %s", business.name, e)

    thread = threading.Thread(target=_run_sync, daemon=True)
    thread.start()

    return JsonResponse({
        'status': 'started',
        'message': 'Sinxronizatsiya boshlandi',
    })


@login_required
def sync_status_view(request):
    """
    AJAX endpoint: Sinxronizatsiya holatini tekshirish.
    Dashboard polling uchun ishlatiladi.
    """
    if not hasattr(request.user, 'business'):
        return JsonResponse({'error': 'Biznes topilmadi'}, status=404)

    business = request.user.business

    from .models import KnowledgeSyncLog, BusinessKnowledge

    # So'nggi log
    last_log = KnowledgeSyncLog.objects.filter(business=business).first()

    # Jami chunklar
    total_chunks = BusinessKnowledge.objects.filter(business=business).count()

    # Noyob sahifalar soni
    unique_pages = (
        BusinessKnowledge.objects
        .filter(business=business)
        .values('source_url')
        .distinct()
        .count()
    )

    data = {
        'total_chunks': total_chunks,
        'unique_pages': unique_pages,
        'has_knowledge': total_chunks > 0,
    }

    if last_log:
        data.update({
            'last_sync': {
                'status': last_log.status,
                'status_display': last_log.get_status_display(),
                'pages_scraped': last_log.pages_scraped,
                'chunks_stored': last_log.chunks_stored,
                'duration': last_log.duration_seconds,
                'triggered_by': last_log.triggered_by,
                'started_at': last_log.started_at.isoformat(),
                'completed_at': last_log.completed_at.isoformat() if last_log.completed_at else None,
            }
        })
    else:
        data['last_sync'] = None

    return JsonResponse(data)
