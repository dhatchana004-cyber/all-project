from django.contrib import admin
from .models import (
    Checklist, ChecklistItem, ChecklistItemOption, ChecklistItemSubmission
)

from django.contrib import admin
from .models import Checklist, ChecklistItem, ChecklistItemOption, ChecklistItemSubmission

# Inline for Checklist Items


class ChecklistItemInline(admin.TabularInline):
    model = ChecklistItem
    extra = 0
    show_change_link = True

# Inline for ChecklistItemOptions


class ChecklistItemOptionInline(admin.TabularInline):
    model = ChecklistItemOption
    extra = 0

# Inline for Submissions


class ChecklistItemSubmissionInline(admin.TabularInline):
    model = ChecklistItemSubmission
    extra = 0


@admin.register(Checklist)
class ChecklistAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'name',
        'project_id',
        'status',
        'created_by_id',
        'created_at',
        'updated_at']
    search_fields = [
        'id',
        'name',
        'description',
        'project_id',
        'building_id',
        'flat_id',
        'zone_id']
    list_filter = [
        'status',
        'project_id',
        'purpose_id',
        'building_id',
        'zone_id',
        'flat_id',
        'category',
        'category_level1',
        'category_level2',
        'category_level3',
        'category_level4',
        'category_level5',
        'category_level6']
    inlines = [ChecklistItemInline]
    ordering = ['-created_at']


@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'title', 'checklist', 'status', 'photo_required'
    ]
    search_fields = [
        'id', 'title', 'description', 'checklist__name'
    ]
    list_filter = [
        'status',
        'checklist__project_id',
        'checklist__status',
        'photo_required']
    inlines = [ChecklistItemOptionInline, ChecklistItemSubmissionInline]
    ordering = ['checklist', 'id']


@admin.register(ChecklistItemOption)
class ChecklistItemOptionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'name', 'choice', 'checklist_item'
    ]
    search_fields = [
        'id', 'name', 'choice', 'checklist_item__title'
    ]
    list_filter = [
        'choice', 'checklist_item'
    ]


@admin.register(ChecklistItemSubmission)
class ChecklistItemSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'checklist_item',
        'status',
        'maker_id',
        'supervisor_id',
        'checker_id',
        'created_at',
        "maker_remarks",
        'maker_media',
        'supervisor_remarks',
        "reviewer_photo",
        "checker_remarks",
        "inspector_photo",
        'attempts']
    search_fields = [
        'id',
        'checklist_item__title',
        'maker_id',
        'supervisor_id',
        'checker_id']
    list_filter = [
        'status', 'maker_id', 'supervisor_id', 'checker_id'
    ]
    ordering = ['-created_at']


# @admin.register(Checklist)
# class ChecklistAdmin(admin.ModelAdmin):
#     list_display = (
#         "id", "name", "project_id", "status", "purpose_id",
#         "building_id", "zone_id", "flat_id", "category", "created_at"
#     )
#     list_filter = (
#         "status", "project_id", "building_id", "zone_id", "flat_id",
#         "category", "purpose_id", "phase_id", "stage_id", "created_at"
#     )
#     search_fields = ("name", "project_id", "building_id", "zone_id", "flat_id", "remarks")
#     date_hierarchy = "created_at"
#     ordering = ("-created_at",)


# @admin.register(ChecklistItem)
# class ChecklistItemAdmin(admin.ModelAdmin):
#     list_display = (
#         "id", "checklist", "description", "status", "sequence", "is_done"
#     )
#     list_filter = (
#         "status", "is_done", "checklist",
#     )
#     search_fields = ("description", "checklist__name")
#     ordering = ("checklist", "sequence")


# @admin.register(ChecklistItemOption)
# class ChecklistItemOptionAdmin(admin.ModelAdmin):
#     list_display = (
#         "id", "checklist_item", "label", "value"
#     )
#     search_fields = ("label", "value", "checklist_item__description")


# @admin.register(ChecklistItemSubmission)
# class ChecklistItemSubmissionAdmin(admin.ModelAdmin):
#     list_display = (
#         "id", "checklist_item", "user", "status", "accepted_at",
#         "selected_option", "checked_by_id", "checked_at"
#     )
#     list_filter = (
#         "status", "selected_option", "checked_by_id", "checked_at"
#     )
#     search_fields = (
#         "checklist_item__description", "user", "check_remark"
#     )
#     date_hierarchy = "accepted_at"
#     ordering = ("-accepted_at",)
