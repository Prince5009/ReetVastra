from django.contrib import admin
from .models import Section, Category, Product, ProductImage, Stock, Customer, Order, Cart, Size, Color, ContactSubmission

class LowStockFilter(admin.SimpleListFilter):
    title = 'stock status'
    parameter_name = 'stock_status'

    def lookups(self, request, model_admin):
        return (
            ('low', 'Low Stock'),
            ('normal', 'Normal Stock'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'low':
            return queryset.filter(quantity__lt=5)
        if self.value() == 'normal':
            return queryset.filter(quantity__gte=5)

class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name',)

class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'quantity', 'is_low_stock')
    list_filter = (LowStockFilter, 'catid', 'colors')
    search_fields = ('title', 'description')
    filter_horizontal = ('sizes', 'colors')

class OrderAdmin(admin.ModelAdmin):
    list_display = ('orderid', 'pid', 'custid', 'amount', 'quantity', 'size', 'color', 'status')
    list_filter = ('status', 'date', 'color')
    search_fields = ('orderid', 'custid__custname')

class CartAdmin(admin.ModelAdmin):
    list_display = ('cartid', 'custid', 'pid', 'quantity', 'size', 'color')
    list_filter = ('color',)
    search_fields = ('custid__custname', 'pid__title')

admin.site.register(Section)
admin.site.register(Category)
admin.site.register(Size)
admin.site.register(Color, ColorAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductImage)
admin.site.register(Stock)
admin.site.register(Customer)
admin.site.register(Order, OrderAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(ContactSubmission)
