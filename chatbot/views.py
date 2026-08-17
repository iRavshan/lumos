import os
import json
import traceback
import random
import string

import chromadb
from google import genai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from dotenv import load_dotenv

from django.shortcuts import render
from .models import ChatErrorLog, UnansweredQuestion, ChatRequestLog

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DIR = os.path.join(BASE_DIR, 'chroma_db')

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)

# Lazy-loaded singletons
_collection = None


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip



def _get_collection():
    global _collection
    if _collection is None:
        chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = chroma_client.get_collection("grant_docs")
    return _collection


def _get_embedding(text: str) -> list[float]:
    """Get embedding from Google Gemini API."""
    result = gemini_client.models.embed_content(
        model="models/gemini-embedding-001",
        contents=text,
    )
    return result.embeddings[0].values


def _generate_answer(question: str, context_chunks: list[str]) -> str:
    """Use Gemini to generate a natural language answer based on retrieved chunks."""
    context = "\n\n---\n\n".join(context_chunks)

    prompt = f"""Siz O'zbekiston Respublikasi Oliy ta'lim, fan va innovatsiyalar vazirligi huzuridagi RAG chatbot yordamchisisiz.
Quyidagi hujjat bo'laklari asosida foydalanuvchining savoliga aniq va tushunarli javob bering.
Javobni o'zbek tilida bering. MUHIM SHART: Agar hujjatda savolga mos ma'lumot umuman bo'lmasa, aynan JAVOB_YOQ deb javob bering. Boshqa hech narsa (Afsuski, kechirasiz va h.k.) yozmang.
Javobni qisqa va aniq bering, lekin muhim ma'lumotlarni tushirib qoldirmang.

HUJJAT BO'LAKLARI:
{context}

FOYDALANUVCHI SAVOLI: {question}

JAVOB:"""

    interaction = gemini_client.interactions.create(
        model="gemini-3.6-flash",
        input=prompt,
    )
    return interaction.output_text


@csrf_exempt
@require_POST
def chat(request):
    """
    Receive a user question, search the vector DB for the most relevant chunks,
    then use Gemini to generate a natural language answer.
    """
    platform = 'web'
    user_id = None
    try:
        body = json.loads(request.body)
        question = body.get('question', '').strip()
        platform = body.get('platform', 'web')
        user_id = body.get('user_id')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': "So'rov noto'g'ri formatda"}, status=400)

    if not question:
        return JsonResponse({'error': "Savol bo'sh bo'lmasligi kerak"}, status=400)

    # Log the request
    ChatRequestLog.objects.create(
        question=question,
        platform=platform,
        device=request.META.get('HTTP_USER_AGENT', '')[:255],
        ip_address=get_client_ip(request),
        user_id=user_id
    )

    try:
        collection = _get_collection()

        # Get embedding for the question
        query_embedding = _get_embedding(question)

        # Search vector DB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
        )

        documents = results.get('documents', [[]])[0]
        distances = results.get('distances', [[]])[0]

        if not documents:
            return JsonResponse({
                'answer': "Kechirasiz, savolingizga mos ma'lumot topilmadi. Iltimos, savolni boshqacha shaklda bering.",
            })

        # Filter by relevance
        relevant_chunks = []
        for doc, dist in zip(documents, distances):
            similarity = 1 - dist
            if similarity > 0.2:
                relevant_chunks.append(doc.strip())

        if not relevant_chunks:
            from .models import UnansweredQuestion
            
            # Save without ticket first to get the ID
            unans = UnansweredQuestion.objects.create(question=question, platform=platform)
            unans.ticket_id = f"T-{unans.id:04d}"
            unans.password = ''.join(random.choices(string.digits, k=4))
            unans.save()
            
            msg = (
                f"Kechirasiz, bazadan savolingizga mos ma'lumot topilmadi. Ushbu savol ma'sul xodimga ko'rib chiqish uchun yuborildi. "
                f"Savol ID raqami: {unans.ticket_id}. Javobni ko'rish uchun maxfiy parol: {unans.password}. "
                f"Parolni unutmang! Ma'sul xodimimiz javob berishi bilan sizni xabardor qilamiz."
            )
            return JsonResponse({
                'answer': msg,
                'ticket_id': unans.ticket_id,
                'password': unans.password
            })

        # Generate answer using Gemini LLM
        answer = _generate_answer(question, relevant_chunks)
        
        if 'JAVOB_YOQ' in answer:
            from .models import UnansweredQuestion
            
            unans = UnansweredQuestion.objects.create(question=question, platform=platform)
            unans.ticket_id = f"T-{unans.id:04d}"
            unans.password = ''.join(random.choices(string.digits, k=4))
            unans.save()
            
            msg = (
                f"Kechirasiz, bazadan savolingizga mos ma'lumot topilmadi. Ushbu savol ma'sul xodimga ko'rib chiqish uchun yuborildi. "
                f"Savol ID raqami: {unans.ticket_id}. Javobni ko'rish uchun maxfiy parol: {unans.password}. "
                f"Parolni unutmang! Ma'sul xodimimiz javob berishi bilan sizni xabardor qilamiz."
            )
            return JsonResponse({
                'answer': msg,
                'ticket_id': unans.ticket_id,
                'password': unans.password
            })

        return JsonResponse({'answer': answer})

    except Exception as e:
        ChatErrorLog.objects.create(
            platform=platform,
            endpoint="Text Chat",
            user_input=request.body.decode('utf-8') if request.body else "None",
            error_message=str(e),
            traceback=traceback.format_exc()
        )
        return JsonResponse({
            'error': "⚠️ Texnik xatolik yuz berdi. Mutaxassis xodimlarimiz muammoni ko'rib chiqishmoqda va tez orada hal qilishadi. Iltimos, biroz vaqtdan so'ng qayta urinib ko'ring.",
        }, status=500)

from google.genai import types

@csrf_exempt
@require_POST
def voice_chat(request):
    """
    Receive an audio file, transcribe it with Gemini, and process the question.
    """
    platform = request.POST.get('platform', 'web')
    user_id = request.POST.get('user_id')
    if 'audio' not in request.FILES:
        return JsonResponse({'error': "Audio fayl topilmadi"}, status=400)
        
    audio_file = request.FILES['audio']
    audio_bytes = audio_file.read()
    
    try:
        # Transcribe audio using Gemini
        transcribe_prompt = "Iltimos, ushbu audioda nima deyilganini aniq matnga o'giring. Faqatgina aytilgan gapni qaytaring, boshqa hech narsa qo'shmang. O'zbek tilida yozing."
        response = gemini_client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type='audio/webm'),
                transcribe_prompt
            ]
        )
        question = response.text.strip()
        
        if not question:
             return JsonResponse({'error': "Audiodan matn ajratib olinmadi"}, status=400)
             
        # Log the request
        ChatRequestLog.objects.create(
            question=question,
            platform=platform,
            device=request.META.get('HTTP_USER_AGENT', '')[:255],
            ip_address=get_client_ip(request),
            user_id=user_id
        )
             
        # Now do the RAG flow with the transcribed text
        collection = _get_collection()
        query_embedding = _get_embedding(question)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
        )
        
        documents = results.get('documents', [[]])[0]
        distances = results.get('distances', [[]])[0]
        
        relevant_chunks = []
        if documents:
            for doc, dist in zip(documents, distances):
                similarity = 1 - dist
                if similarity > 0.2:
                    relevant_chunks.append(doc.strip())
                
        if not relevant_chunks:
            from .models import UnansweredQuestion
            
            unans = UnansweredQuestion.objects.create(question=question, platform=platform)
            unans.ticket_id = f"T-{unans.id:04d}"
            unans.password = ''.join(random.choices(string.digits, k=4))
            unans.save()
            
            msg = (
                f"Kechirasiz, bazadan savolingizga mos ma'lumot topilmadi. Ushbu savol ma'sul xodimga ko'rib chiqish uchun yuborildi. "
                f"Savol ID raqami: {unans.ticket_id}. Javobni ko'rish uchun maxfiy parol: {unans.password}. "
                f"Parolni unutmang! Ma'sul xodimimiz javob berishi bilan sizni xabardor qilamiz."
            )
            return JsonResponse({
                'question': question,
                'answer': msg,
                'ticket_id': unans.ticket_id,
                'password': unans.password
            })
            
        answer = _generate_answer(question, relevant_chunks)
        
        if 'JAVOB_YOQ' in answer:
            from .models import UnansweredQuestion
            
            unans = UnansweredQuestion.objects.create(question=question, platform=platform)
            unans.ticket_id = f"T-{unans.id:04d}"
            unans.password = ''.join(random.choices(string.digits, k=4))
            unans.save()
            
            msg = (
                f"Kechirasiz, bazadan savolingizga mos ma'lumot topilmadi. Ushbu savol ma'sul xodimga ko'rib chiqish uchun yuborildi. "
                f"Savol ID raqami: {unans.ticket_id}. Javobni ko'rish uchun maxfiy parol: {unans.password}. "
                f"Parolni unutmang! Ma'sul xodimimiz javob berishi bilan sizni xabardor qilamiz."
            )
            return JsonResponse({
                'question': question,
                'answer': msg,
                'ticket_id': unans.ticket_id,
                'password': unans.password
            })
        
        return JsonResponse({
            'question': question,
            'answer': answer
        })
        
    except Exception as e:
        ChatErrorLog.objects.create(
            platform=platform,
            endpoint="Voice Chat",
            user_input="Audio file received",
            error_message=str(e),
            traceback=traceback.format_exc()
        )
        return JsonResponse({
            'error': "⚠️ Texnik xatolik yuz berdi. Mutaxassis xodimlarimiz muammoni ko'rib chiqishmoqda va tez orada hal qilishadi. Iltimos, biroz vaqtdan so'ng qayta urinib ko'ring.",
        }, status=500)

from django.views.decorators.http import require_GET

@csrf_exempt
@require_GET
def get_errors(request):
    """
    Retrieve the latest 50 chatbot errors.
    """
    try:
        errors = ChatErrorLog.objects.all().order_by('-timestamp')[:50]
        error_list = []
        for err in errors:
            error_list.append({
                'id': err.id,
                'timestamp': err.timestamp.isoformat(),
                'platform': err.platform,
                'endpoint': err.endpoint,
                'user_input': err.user_input,
                'error_message': err.error_message,
                'traceback': err.traceback,
            })
        return JsonResponse({'errors': error_list})
    except Exception as e:
        return JsonResponse({'error': f"Xatoliklarni olishda muammo yuz berdi: {str(e)}"}, status=500)

@csrf_exempt
@require_POST
def log_error(request):
    """
    Allow external applications to report an error to the central ChatErrorLog.
    """
    try:
        body = json.loads(request.body)
        error_message = body.get('error_message')
        
        if not error_message:
            return JsonResponse({'error': "Xatolik xabari (error_message) majburiy"}, status=400)
            
        ChatErrorLog.objects.create(
            platform=body.get('platform', 'unknown'),
            endpoint=body.get('endpoint', 'External API'),
            user_input=body.get('user_input', ''),
            error_message=error_message,
            traceback=body.get('traceback', '')
        )
        return JsonResponse({'status': 'success', 'message': "Xatolik saqlandi"})
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': "So'rov noto'g'ri formatda (JSON kutilmoqda)"}, status=400)
    except Exception as e:
        return JsonResponse({'error': f"Xatolikni saqlashda muammo yuz berdi: {str(e)}"}, status=500)

@require_GET
def statistics_dashboard(request):
    """
    Render a dashboard with chat statistics.
    """
    from django.db.models import Count
    
    total_requests = ChatRequestLog.objects.count()
    
    # Calculate unique users based on user_id if present, else ip_address
    unique_ips = ChatRequestLog.objects.exclude(ip_address__isnull=True).values('ip_address').distinct().count()
    unique_user_ids = ChatRequestLog.objects.exclude(user_id__isnull=True).values('user_id').distinct().count()
    # Simple heuristic: total unique is the sum of unique user_ids + unique ips that don't have user_ids
    unique_ips_no_user = ChatRequestLog.objects.filter(user_id__isnull=True).exclude(ip_address__isnull=True).values('ip_address').distinct().count()
    total_unique_users = unique_user_ids + unique_ips_no_user
    
    # Platform distribution
    platform_data = ChatRequestLog.objects.values('platform').annotate(count=Count('id'))
    platforms = [item['platform'] for item in platform_data]
    platform_counts = [item['count'] for item in platform_data]
    
    context = {
        'total_requests': total_requests,
        'total_unique_users': total_unique_users,
        'platforms': platforms,
        'platform_counts': platform_counts,
    }
    return render(request, 'statistics.html', context)

@csrf_exempt
@require_POST
def log_request(request):
    """
    Allow external applications to manually log a request for statistics, 
    without invoking the Gemini AI/RAG model.
    """
    try:
        body = json.loads(request.body)
        question = body.get('question')
        
        if not question:
            return JsonResponse({'error': "Savol matni (question) majburiy"}, status=400)
            
        ChatRequestLog.objects.create(
            question=question,
            platform=body.get('platform', 'unknown'),
            device=body.get('device', 'External API'),
            ip_address=get_client_ip(request),
            user_id=body.get('user_id')
        )
        return JsonResponse({'status': 'success', 'message': "So'rov statistikaga qo'shildi"})
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': "So'rov noto'g'ri formatda (JSON kutilmoqda)"}, status=400)
    except Exception as e:
        return JsonResponse({'error': f"So'rovni saqlashda muammo yuz berdi: {str(e)}"}, status=500)

@csrf_exempt
@require_POST
def check_ticket(request):
    """
    Check the status and answer of a ticket using ticket_id and password.
    """
    try:
        body = json.loads(request.body)
        ticket_id = body.get('ticket_id')
        password = body.get('password')
        
        from .models import UnansweredQuestion
        ticket = UnansweredQuestion.objects.filter(ticket_id=ticket_id, password=password).first()
        if not ticket:
            return JsonResponse({'error': "Ticket topilmadi yoki parol xato."}, status=404)
            
        return JsonResponse({
            'status': ticket.status,
            'answer': ticket.answer,
            'feedback': ticket.feedback
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_POST
def submit_feedback(request):
    """
    Submit feedback (yes/partially/no) for an answered ticket.
    """
    try:
        body = json.loads(request.body)
        ticket_id = body.get('ticket_id')
        password = body.get('password')
        feedback = body.get('feedback')
        
        if feedback not in ['yes', 'partially', 'no']:
            return JsonResponse({'error': "Noto'g'ri feedback qiymati."}, status=400)
            
        from .models import UnansweredQuestion
        ticket = UnansweredQuestion.objects.filter(ticket_id=ticket_id, password=password).first()
        if not ticket:
            return JsonResponse({'error': "Ticket topilmadi yoki parol xato."}, status=404)
            
        ticket.feedback = feedback
        ticket.save()
        
        return JsonResponse({'status': 'success', 'message': "Rahmat, bahoingiz qabul qilindi!"})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
