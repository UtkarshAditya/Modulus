from django.contrib import admin

from .models import JobPosting


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company_name",
        "submitter",
        "status",
        "version",
        "submitted_at",
        "created_at",
    )
    list_filter = ("status", "employment_type", "salary_disclosed")
    search_fields = ("title", "company_name", "submitter__username", "submitter__email")
    readonly_fields = ("content_hash", "created_at", "updated_at")
    autocomplete_fields = ("submitter",)

    def save_model(self, request, obj, form, change):
        obj.content_hash = obj.compute_content_hash()
        super().save_model(request, obj, form, change)
