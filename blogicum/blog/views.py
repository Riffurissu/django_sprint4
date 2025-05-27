from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import CommentForm, CustomUserChangeForm, PostForm
from .models import Category, Post, User


def filter_published_posts(queryset):
    return queryset.filter(
        is_published=True,
        category__is_published=True,
        pub_date__lte=timezone.now()
    )


def index(request):
    posts = filter_published_posts(
        Post.objects.select_related('category', 'author', 'location')
        .annotate(comment_count=Count('comments'))
    ).order_by('-pub_date',)

    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {'page_obj': page_obj}
    return render(request, 'blog/index.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(
        Post.objects.select_related('category', 'author', 'location'),
        pk=post_id
    )

    if request.user != post.author:
        post = get_object_or_404(
            filter_published_posts(
                Post.objects.select_related('category', 'author', 'location')
            ),
            pk=post_id
        )

    form = CommentForm()
    comments = post.comments.select_related('author').order_by('created_at')

    template = 'blog/detail.html'
    context = {
        'post': post,
        'form': form,
        'comments': comments
    }
    return render(request, template, context)


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category.objects.filter(is_published=True),
        slug=category_slug
    )

    posts = filter_published_posts(
        category.posts.select_related('author', 'category', 'location')
        .annotate(comment_count=Count('comments'))
    ).order_by('-pub_date',)

    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'category': category,
        'page_obj': page_obj
    }
    return render(request, 'blog/category.html', context)


def profile(request, username):
    user_profile = get_object_or_404(User, username=username)

    posts = Post.objects.filter(author=user_profile)
    if request.user != user_profile:
        posts = filter_published_posts(posts)

    posts = posts.annotate(comment_count=Count(
        'comments')).order_by('-pub_date')

    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'profile': user_profile,
        'page_obj': page_obj
    }
    return render(request, 'blog/profile.html', context)


class CustomLoginView(LoginView):
    def get_success_url(self):
        username = self.request.user.username  # type: ignore
        return reverse('blog:profile', kwargs={'username': username})


@login_required
def edit_profile(request):
    form = CustomUserChangeForm(
        request.POST or None,
        instance=request.user
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('blog:profile', username=request.user.username)

    return render(request, 'blog/user.html', {'form': form})


@login_required
def create_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', username=request.user.username)

    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, post_id=None):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post.pk)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post.pk)

    return render(request, 'blog/create.html', {'form': form})


@login_required
def delete_post(request, post_id=None):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post.pk)

    if request.method == 'POST':
        post.delete()
        return redirect('blog:index')

    return render(
        request,
        'blog/create.html',
        {'form': PostForm(instance=post)}
    )


@login_required
def add_comment(request, post_id=None):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        return redirect('blog:post_detail', post_id=post_id)

    return redirect('blog:post_detail', post_id=post_id)


@login_required
def edit_comment(request, post_id=None, comment_id=None):
    post = get_object_or_404(Post, pk=post_id)
    comment = get_object_or_404(post.comments, pk=comment_id)

    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)

    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)

    return render(
        request,
        'blog/comment.html',
        {'form': form, 'post': post, 'comment': comment}
    )


@login_required
def delete_comment(request, post_id=None, comment_id=None):
    post = get_object_or_404(Post, pk=post_id)
    comment = get_object_or_404(post.comments, pk=comment_id)

    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)

    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post_id)

    return render(request, 'blog/comment.html', {'comment': comment})
