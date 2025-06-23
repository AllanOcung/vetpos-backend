from django.contrib import admin
from .models import Supplier, Product, RestockHistory, Sale, Setting

# Register your models here.
admin.site.register(Supplier)
admin.site.register(Product)
admin.site.register(RestockHistory)
admin.site.register(Sale)
# Register the new Setting model
admin.site.register(Setting)