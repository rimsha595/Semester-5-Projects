from django.contrib import admin

# Register your models here.
from .models import LostItem, FoundItem, Comment

admin.site.register(LostItem)
admin.site.register(FoundItem)
admin.site.register(Comment)
