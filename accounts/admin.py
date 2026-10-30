from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import (
    CareConsultation,
    CareSchedule,
    Order,
    OrderItem,
    Product,
    Profile,
    SharedSiteContent,
    SharedUser,
    ShopProfile,
)


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fields = ("name", "phone", "role", "status")


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Profile)


@admin.register(SharedUser)
class SharedUserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "name", "phone", "role", "age_14_agreed", "created_at")
    search_fields = ("username", "email", "name", "phone")
    list_filter = ("role",)


@admin.register(SharedSiteContent)
class SharedSiteContentAdmin(admin.ModelAdmin):
    list_display = ("content_key", "title", "updated_at")
    search_fields = ("content_key", "title")


@admin.register(CareConsultation)
class CareConsultationAdmin(admin.ModelAdmin):
    list_display = ("applicant_name", "applicant_phone", "care_level", "mobility_status", "status", "created_at")
    list_filter = ("status", "care_level", "mobility_status")
    search_fields = ("applicant_name", "applicant_phone")


@admin.register(CareSchedule)
class CareScheduleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "start_datetime", "end_datetime")
    list_filter = ("category",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "sale_price", "stock", "is_hygiene_product", "is_active")
    list_filter = ("is_hygiene_product", "is_active")
    search_fields = ("name", "category")


@admin.register(ShopProfile)
class ShopProfileAdmin(admin.ModelAdmin):
    list_display = ("user_id", "recipient_name", "recipient_phone", "zipcode")
    search_fields = ("recipient_name", "recipient_phone", "user_id")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "name", "total", "status", "payment_key", "tracking_number", "created_at")
    search_fields = ("number", "name", "phone", "payment_key")
    list_filter = ("status",)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("product_name", "order_id", "unit_price", "quantity")
    search_fields = ("product_name", "order_id")
