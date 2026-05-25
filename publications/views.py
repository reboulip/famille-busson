import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

from annuaire.models import Person
from annuaire.views import StaffRequiredMixin

from .forms import AttachmentFormSet, BlogPostForm, CommentForm
from .models import BlogPost, Comment


def _authors_initial_json(view):
    """Build the JSON payload used by the person-picker to pre-populate authors."""
    request = view.request
    if request.method == 'POST':
        ids = [int(pk) for pk in request.POST.getlist('authors') if pk.isdigit()]
        persons = list(Person.objects.filter(pk__in=ids).order_by('last_name', 'first_name'))
    elif getattr(view, 'object', None) is not None:
        persons = list(view.object.authors.all().order_by('last_name', 'first_name'))
    else:
        profile = getattr(request.user, 'profile', None)
        persons = [profile] if profile is not None else []
    return json.dumps([{'id': p.pk, 'name': str(p)} for p in persons])


class AuthorOrStaffRequiredMixin(LoginRequiredMixin):
    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        user = self.request.user
        if user.is_staff:
            return obj
        profile = getattr(user, 'profile', None)
        if profile is None or not obj.authors.filter(pk=profile.pk).exists():
            raise PermissionDenied("Vous n'êtes pas auteur de cette publication.")
        return obj


class BlogPostListView(LoginRequiredMixin, ListView):
    model = BlogPost
    template_name = 'publications/blogpost_list.html'
    context_object_name = 'posts'
    paginate_by = 20

    def get_queryset(self):
        return (BlogPost.objects
                .prefetch_related('authors', 'attachments')
                .order_by('-created_at'))


class BlogPostDetailView(LoginRequiredMixin, DetailView):
    model = BlogPost
    template_name = 'publications/blogpost_detail.html'
    context_object_name = 'post'

    def _can_edit(self, post):
        user = self.request.user
        if user.is_staff:
            return True
        profile = getattr(user, 'profile', None)
        return profile is not None and post.authors.filter(pk=profile.pk).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault('comment_form', CommentForm())
        context['can_edit'] = self._can_edit(self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        profile = getattr(request.user, 'profile', None)
        if profile is None:
            messages.error(request, "Vous devez compléter votre profil avant de commenter.")
            return redirect('profile-create')
        form = CommentForm(request.POST)
        if form.is_valid():
            Comment.objects.create(
                post=self.object,
                author=profile,
                body=form.cleaned_data['body'],
            )
            return redirect('blogpost-detail', pk=self.object.pk)
        context = self.get_context_data(comment_form=form)
        return self.render_to_response(context)


class BlogPostCreateView(LoginRequiredMixin, CreateView):
    model = BlogPost
    form_class = BlogPostForm
    template_name = 'publications/blogpost_form.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not hasattr(request.user, 'profile'):
            messages.error(request, "Vous devez compléter votre profil avant de publier.")
            return redirect('profile-create')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['current_person'] = getattr(self.request.user, 'profile', None)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formsets'] = [AttachmentFormSet(self.request.POST, self.request.FILES)]
        else:
            context['formsets'] = [AttachmentFormSet()]
        context['authors_initial_json'] = _authors_initial_json(self)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        attachment_formset = context['formsets'][0]
        if not attachment_formset.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            profile = getattr(self.request.user, 'profile', None)
            if profile is not None and not self.object.authors.filter(pk=profile.pk).exists():
                self.object.authors.add(profile)
            attachment_formset.instance = self.object
            attachment_formset.save()
        return redirect('blogpost-detail', pk=self.object.pk)


class BlogPostUpdateView(AuthorOrStaffRequiredMixin, UpdateView):
    model = BlogPost
    form_class = BlogPostForm
    template_name = 'publications/blogpost_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formsets'] = [
                AttachmentFormSet(self.request.POST, self.request.FILES, instance=self.object),
            ]
        else:
            context['formsets'] = [AttachmentFormSet(instance=self.object)]
        context['authors_initial_json'] = _authors_initial_json(self)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        attachment_formset = context['formsets'][0]
        if not attachment_formset.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            attachment_formset.instance = self.object
            attachment_formset.save()
        return redirect('blogpost-detail', pk=self.object.pk)


class BlogPostDeleteView(AuthorOrStaffRequiredMixin, DeleteView):
    model = BlogPost
    template_name = 'publications/blogpost_confirm_delete.html'
    success_url = reverse_lazy('blogpost-list')


class CommentDeleteView(StaffRequiredMixin, DeleteView):
    model = Comment
    template_name = 'publications/comment_confirm_delete.html'

    def get_success_url(self):
        return reverse('blogpost-detail', kwargs={'pk': self.object.post.pk})
