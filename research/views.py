from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib import messages
from django.http import HttpResponse
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.html import escape

from .models import Project, ProjectMember, Research

from io import BytesIO
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet


def page(request, template, **context):
    return render(request, template, context)


def register(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            messages.error(request, 'Username and password required.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            login(request, user)
            return redirect('dashboard')

    return page(request, 'app.html', page='register')


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(
            request, username=username, password=password
        )

        if user:
            login(request, user)
            return redirect('dashboard')

        messages.error(request, 'Invalid username or password.')

    return page(request, 'app.html', page='login')


@login_required
def user_logout(request):
    if request.method == 'POST':
        logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    projects = Project.objects.filter(
        members__user=request.user
    ).distinct().order_by('-created_at')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()

        if title:
            with transaction.atomic():
                project = Project.objects.create(
                    title=title,
                    description=description,
                    owner=request.user
                )
                ProjectMember.objects.create(
                    project=project,
                    user=request.user
                )
            return redirect('project', project_id=project.id)

    return page(
        request, 'app.html',
        page='dashboard', projects=projects
    )


def get_member_project(request, project_id):
    return get_object_or_404(
        Project,
        id=project_id,
        members__user=request.user
    )


@login_required
def project_detail(request, project_id):
    project = get_member_project(request, project_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'invite' and project.owner == request.user:
            username = request.POST.get('username', '').strip()
            invited_user = User.objects.filter(
                username=username
            ).first()

            if invited_user:
                ProjectMember.objects.get_or_create(
                    project=project,
                    user=invited_user
                )
                messages.success(request, 'Member added.')
            else:
                messages.error(request, 'User not found.')

        elif action == 'research':
            title = request.POST.get('title', '').strip()
            content = request.POST.get('content', '').strip()

            if title and content:
                research = Research.objects.create(
                    project=project,
                    author=request.user,
                    title=title,
                    content=content,
                    status='submitted'
                )
                return redirect(
                    'research_detail', research_id=research.id
                )

    researches = project.researches.select_related(
        'author', 'reviewer'
    ).order_by('-created_at')

    return page(
        request, 'app.html',
        page='project',
        project=project,
        researches=researches
    )


@login_required
def research_detail(request, research_id):
    research = get_object_or_404(
        Research.objects.select_related('project', 'author'),
        id=research_id,
        project__members__user=request.user
    )

    is_author = research.author_id == request.user.id

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'save' and is_author:
            if research.status in ('draft', 'changes'):
                research.title = request.POST.get(
                    'title', research.title
                ).strip()
                research.content = request.POST.get(
                    'content', research.content
                )
                research.status = 'draft'
                research.reviewer = None
                research.feedback = ''
                research.save()

        elif action == 'submit' and is_author:
            if research.status in ('draft', 'changes'):
                research.status = 'submitted'
                research.reviewer = None
                research.feedback = ''
                research.save()

        elif action in ('approve', 'changes'):
            if not is_author and research.status == 'submitted':
                research.status = (
                    'approved' if action == 'approve' else 'changes'
                )
                research.reviewer = request.user
                research.feedback = request.POST.get(
                    'feedback', ''
                ).strip()
                research.save()

        return redirect(
            'research_detail', research_id=research.id
        )

    return page(
        request, 'app.html',
        page='editor',
        research=research,
        is_author=is_author
    )


@login_required
def combined(request, project_id):
    project = get_member_project(request, project_id)

    researches = project.researches.filter(
        status='approved'
    ).select_related('author').order_by('created_at')

    return page(
        request, 'app.html',
        page='combined',
        project=project,
        researches=researches
    )


@login_required
def export_pdf(request, project_id):
    project = get_member_project(request, project_id)

    researches = project.researches.filter(
        status='approved'
    ).select_related('author').order_by('created_at')

    buffer = BytesIO()
    document = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(escape(project.title), styles['Title']),
        Spacer(1, 20),
        Paragraph(
            escape(project.description),
            styles['Normal']
        ),
        Spacer(1, 20)
    ]

    for research in researches:
        elements.append(
            Paragraph(escape(research.title), styles['Heading2'])
        )
        elements.append(
            Paragraph(
                'Researcher: ' + escape(research.author.username),
                styles['Italic']
            )
        )

        for paragraph in research.content.splitlines():
            if paragraph.strip():
                elements.append(
                    Paragraph(escape(paragraph), styles['BodyText'])
                )
                elements.append(Spacer(1, 6))

        elements.append(Spacer(1, 18))

    document.build(elements)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/pdf'
    )
    response['Content-Disposition'] = (
        'attachment; filename="researchhub.pdf"'
    )
    return response
