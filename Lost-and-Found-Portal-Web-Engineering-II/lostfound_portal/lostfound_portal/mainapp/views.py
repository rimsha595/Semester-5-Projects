from django.shortcuts import render

# Create your views here.
from django.shortcuts import redirect, get_object_or_404
from .models import LostItem, FoundItem, Comment
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import views as auth_views
from django.db.models import Q

@login_required
def update_status(request, id):
    item = get_object_or_404(LostItem, id=id, user=request.user)
    if item.user == request.user and item.status != 'Found':
        item.status = 'Found'
        item.save()
    return redirect('item_detail', type='Lost', id=id)

@login_required
def post_found(request):
    if request.method == 'POST':
        # Create the found item
        found_item = FoundItem.objects.create(
            user=request.user,
            title=request.POST['title'],
            description=request.POST['description'],
            category=request.POST['category'],
            location=request.POST['location'],
            photo=request.FILES.get('photo')
        )

        # Check for matching lost items
        lost_items = LostItem.objects.filter(status='Pending')
        for lost in lost_items:
            # Simple matching logic: same category + title or description contains keywords
            if (lost.category == found_item.category and
                (found_item.title.lower() in lost.title.lower() or
                 found_item.description.lower() in lost.description.lower() or
                 lost.title.lower() in found_item.title.lower() or
                 lost.description.lower() in found_item.description.lower())):
                
                lost.status = 'Matched'
                lost.save()

        return redirect('found_list')
    
    return render(request, 'post_form.html', {'type': 'Found'})
# Register view
def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

# Login view
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

# Logout view
def logout_view(request):
    logout(request)
    return redirect('home')

def home(request):
    lost_items = LostItem.objects.all().order_by('-date_lost')[:5]
    found_items = FoundItem.objects.all().order_by('-date_found')[:5]
    return render(request, 'home.html', {'lost_items': lost_items, 'found_items': found_items})

def lost_list(request):
    items = LostItem.objects.all().order_by('-date_lost')
    return render(request, 'lost_list.html', {'items': items})

def found_list(request):
    items = FoundItem.objects.all().order_by('-date_found')
    return render(request, 'found_list.html', {'items': items})

@login_required
def post_lost(request):
    if request.method == 'POST':
        LostItem.objects.create(
            user=request.user,
            title=request.POST['title'],
            description=request.POST['description'],
            category=request.POST['category'],
            location=request.POST['location'],
            photo=request.FILES.get('photo')
        )
        return redirect('lost_list')
    return render(request, 'post_form.html', {'type': 'Lost'})

@login_required
def post_found(request):
    if request.method == 'POST':
        FoundItem.objects.create(
            user=request.user,
            title=request.POST['title'],
            description=request.POST['description'],
            category=request.POST['category'],
            location=request.POST['location'],
            photo=request.FILES.get('photo')
        )
        return redirect('found_list')
    return render(request, 'post_form.html', {'type': 'Found'})
@login_required
def delete_item(request, type, id):
    if type == 'Lost':
        item = get_object_or_404(LostItem, id=id, user=request.user)
    else:
        item = get_object_or_404(FoundItem, id=id, user=request.user)

    if request.method == "POST":
        item.delete()
        if type == "Lost":
            return redirect('lost_list')
        else:
            return redirect('found_list')

    return render(request, 'confirm_delete.html', {'item': item, 'type': type})

@login_required
def item_detail(request, type, id):
    item = None
    if type == 'Lost':
        item = get_object_or_404(LostItem, id=id)
        found_items = FoundItem.objects.filter(status='Pending', category=item.category)
        # Filter by matching title OR description
        suggested_items = found_items.filter(
            Q(title__icontains=item.title) | Q(description__icontains=item.description)
        )
    else:
        item = get_object_or_404(FoundItem, id=id)
        suggested_items = []

    comments = Comment.objects.filter(item_type=type, item_id=id).order_by('-timestamp')

    if request.method == 'POST'and request.user.is_authenticated:
        Comment.objects.create(
            user=request.user,
            item_type=type,
            item_id=id,
            text=request.POST['comment']
        )
        return redirect('item_detail', type=type, id=id)
    return render(request, 'item_detail.html', {
        'item': item,
        'comments': comments,
        'type': type,
        'suggested_items': suggested_items
    })
