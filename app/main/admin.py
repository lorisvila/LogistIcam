from django.contrib import admin
from .models import Stock, Transaction

admin.site.register(Stock)
admin.site.register(Transaction)