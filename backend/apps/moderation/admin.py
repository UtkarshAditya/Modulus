from django.contrib import admin

from .models import Decision, Flag, ModerationRun, ReviewClaim


class FlagInline(admin.TabularInline):
    model = Flag
    extra = 0
    fields = (
        "category",
        "severity",
        "source",
        "confidence",
        "rule_id",
        "reason",
        "is_false_positive",
    )
    readonly_fields = ("category", "severity", "source", "confidence", "rule_id", "reason")


class DecisionInline(admin.TabularInline):
    model = Decision
    extra = 0
    fields = ("moderator", "action", "reason_code", "notes", "created_at")
    readonly_fields = ("created_at",)


@admin.register(ModerationRun)
class ModerationRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "posting",
        "posting_version",
        "status",
        "routing",
        "risk_score",
        "started_at",
        "finished_at",
    )
    list_filter = ("status", "routing")
    search_fields = ("posting__title", "posting__company_name")
    inlines = [FlagInline, DecisionInline]


@admin.register(Flag)
class FlagAdmin(admin.ModelAdmin):
    list_display = ("run", "category", "severity", "source", "confidence", "is_false_positive")
    list_filter = ("category", "severity", "source", "is_false_positive")
    search_fields = ("rule_id", "reason")


@admin.register(ReviewClaim)
class ReviewClaimAdmin(admin.ModelAdmin):
    list_display = ("posting", "moderator", "claimed_at", "expires_at", "released_at")
    list_filter = ("moderator",)
    autocomplete_fields = ("moderator",)


@admin.register(Decision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ("run", "moderator", "action", "reason_code", "created_at")
    list_filter = ("action",)
    autocomplete_fields = ("moderator",)
