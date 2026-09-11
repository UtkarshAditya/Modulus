from django.contrib import admin

from .models import Policy


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ("version", "is_active", "created_by", "created_at")
    list_filter = ("is_active",)
    readonly_fields = ("version", "created_at")
    actions = ["activate_policy"]

    @admin.action(description="Activate selected policy")
    def activate_policy(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Select exactly one policy to activate.")
            return
        Policy.objects.activate(queryset.first())
