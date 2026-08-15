import os
import json

import chromadb
from google import genai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DIR = os.path.join(BASE_DIR, 'chroma_db')

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)

# Lazy-loaded singletons
_collection = None


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
Javobni o'zbek tilida bering. Agar hujjatda savolga mos ma'lumot bo'lmasa, shuni aytib o'ting.
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
    try:
        body = json.loads(request.body)
        question = body.get('question', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': "So'rov noto'g'ri formatda"}, status=400)

    if not question:
        return JsonResponse({'error': "Savol bo'sh bo'lmasligi kerak"}, status=400)

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
            return JsonResponse({
                'answer': "Kechirasiz, savolingizga mos ma'lumot topilmadi. Iltimos, savolni boshqacha shaklda bering.",
            })

        # Generate answer using Gemini LLM
        answer = _generate_answer(question, relevant_chunks)

        return JsonResponse({'answer': answer})

    except Exception as e:
        return JsonResponse({
            'error': f"Xatolik yuz berdi: {str(e)}",
        }, status=500)

from google.genai import types

@csrf_exempt
@require_POST
def voice_chat(request):
    """
    Receive an audio file, transcribe it with Gemini, and process the question.
    """
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
            return JsonResponse({
                'question': question,
                'answer': "Kechirasiz, savolingizga mos ma'lumot topilmadi. Iltimos, savolni boshqacha shaklda bering."
            })
            
        answer = _generate_answer(question, relevant_chunks)
        
        return JsonResponse({
            'question': question,
            'answer': answer
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f"Ovozni ishlashda xatolik yuz berdi: {str(e)}",
        }, status=500)
