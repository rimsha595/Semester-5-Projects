from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

CATEGORY_CHOICES = [
    ('Electronics', 'Electronics'),
    ('Documents', 'Documents'),
    ('Clothing', 'Clothing'),
    ('Accessories', 'Accessories'),
    ('Others', 'Others')
]

STATUS_CHOICES = [
    ('Pending', 'Pending'),
    ('Matched', 'Matched'),
    ('Found', 'Found')
]

class LostItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    location = models.CharField(max_length=100)
    photo = models.ImageField(upload_to='lost_photos/', blank=True, null=True)
    date_lost = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return self.title

class FoundItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    location = models.CharField(max_length=100)
    photo = models.ImageField(upload_to='found_photos/', blank=True, null=True)
    date_found = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return self.title

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    item_type = models.CharField(max_length=10)  # Lost or Found
    item_id = models.IntegerField()
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} comment"
