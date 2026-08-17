from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from chatbot.models import UnansweredQuestion
from support.models import Profile

def is_operator(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role in ['operator', 'supervisor']

def is_supervisor(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'supervisor'

@login_required
@user_passes_test(is_operator)
def operator_panel(request):
    questions = UnansweredQuestion.objects.filter(status='pending').order_by('timestamp')
    return render(request, 'support/operator.html', {'questions': questions})

@login_required
@user_passes_test(is_operator)
def operator_answer(request, pk):
    question = get_object_or_404(UnansweredQuestion, pk=pk)
    if request.method == 'POST':
        answer = request.POST.get('answer')
        if answer:
            question.answer = answer
            question.status = 'answered'
            question.answered_by = request.user
            question.answered_at = timezone.now()
            question.save()
            return redirect('operator_panel')
    return render(request, 'support/operator_answer.html', {'question': question})

@login_required
@user_passes_test(is_supervisor)
def supervisor_panel(request):
    three_days_ago = timezone.now() - timezone.timedelta(days=3)
    
    # Unanswered > 3 days
    overdue_questions = UnansweredQuestion.objects.filter(
        status='pending', 
        timestamp__lte=three_days_ago
    ).order_by('timestamp')
    
    # Negative feedback
    bad_feedback = UnansweredQuestion.objects.filter(
        feedback__in=['no', 'partially']
    ).order_by('-answered_at')
    
    # Operators stats
    operators = Profile.objects.filter(role='operator')
    
    return render(request, 'support/supervisor.html', {
        'overdue_questions': overdue_questions,
        'bad_feedback': bad_feedback,
        'operators': operators,
    })
