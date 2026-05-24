from django.urls import path

from .views import (
    BlogPostCreateView, BlogPostDeleteView, BlogPostDetailView,
    BlogPostListView, BlogPostUpdateView, CommentDeleteView,
)


urlpatterns = [
    path('', BlogPostListView.as_view(), name='blogpost-list'),
    path('new/', BlogPostCreateView.as_view(), name='blogpost-create'),
    path('<int:pk>/', BlogPostDetailView.as_view(), name='blogpost-detail'),
    path('<int:pk>/edit/', BlogPostUpdateView.as_view(), name='blogpost-edit'),
    path('<int:pk>/delete/', BlogPostDeleteView.as_view(), name='blogpost-delete'),
    path('comments/<int:pk>/delete/', CommentDeleteView.as_view(), name='comment-delete'),
]
