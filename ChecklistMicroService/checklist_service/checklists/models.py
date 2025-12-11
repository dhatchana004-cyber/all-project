from django.db import models

class Checklist(models.Model):
    STATUS_CHOICES = [
        ("not_started", "Not Started"),
        ("in_progress", "In Progress"),
        ("work_in_progress", "Work in Progress"),
        ("completed", "Completed"),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="not_started")
    user_generated_id = models.IntegerField(null=True, blank=True, help_text="User ID from the User microservice who generated this checklist")
    project_id = models.IntegerField()
    building_id = models.IntegerField(null=True, blank=True)
    zone_id = models.IntegerField(null=True, blank=True)
    room_id = models.IntegerField(null=True, blank=True)
    flat_id = models.IntegerField(null=True, blank=True)
    subzone_id = models.IntegerField(null=True, blank=True)   # <-- add this
    level_id = models.IntegerField(null=True, blank=True)     # <-- add this (floor)

    purpose_id = models.IntegerField()
    phase_id = models.IntegerField(null=True, blank=True)
    stage_id = models.IntegerField(null=True, blank=True)

    category = models.IntegerField()
    category_level1 = models.IntegerField(null=True, blank=True)
    category_level2 = models.IntegerField(null=True, blank=True)
    category_level3 = models.IntegerField(null=True, blank=True)
    category_level4 = models.IntegerField(null=True, blank=True)
    category_level5 = models.IntegerField(null=True, blank=True)
    category_level6 = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    created_by_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ChecklistItem(models.Model):
    checklist = models.ForeignKey(
        Checklist,
        on_delete=models.CASCADE,
        related_name="items")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    STATUS_CHOICES = [
        ("not_started", "Not Started"),
        # ("in_progress", "In Progress"),
        ("pending_for_inspector", "Pending for Inspector"),
        ("tetmpory_inspctor","tetmpory_inspctor"),
        ("tetmpory_Maker","tetmpory_Maker"),
        ("pending_for_maker", "Pending for Maker"),
        ("pending_for_supervisor", "Pending for Supervisor"),

        ("completed", "Completed"),
    ]
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="not_started")
    ignore_now = models.BooleanField(default=False)
    photo_required = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} ({self.checklist.name})"


class ChecklistItemOption(models.Model):
    checklist_item = models.ForeignKey(
        ChecklistItem,
        on_delete=models.CASCADE,
        related_name="options")
    name = models.CharField(max_length=255)
    choice = models.CharField(
        max_length=20, choices=[
            ("P", "Positive"), ("N", "Negative")])

    def __str__(self):
        return f"{self.name} ({self.choice})"


class ChecklistItemSubmission(models.Model):
    STATUS_CHOICES = [
        ("created", "Created"),
        ("completed", "Completed"),

        ("Pending for Maker", "Pending for Maker"),
        ("pending_supervisor", "Pending Supervisor"),
        ("pending_checker", "Pending Checker"),

        ("rejected_by_supervisor", "Rejected by Supervisor"),
        ("rejected_by_checker", "Rejected by Checker"),
    ]
    attempts = models.IntegerField(default=0)
    checklist_item = models.ForeignKey(
        ChecklistItem,
        on_delete=models.CASCADE,
        related_name="submissions")
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="created")

    maker_id = models.IntegerField(null=True, blank=True)
    maker_remarks = models.TextField(blank=True, null=True)
    maker_media = models.ImageField(upload_to='maker_media/', null=True, blank=True)
    maker_at = models.DateTimeField(null=True, blank=True)

    supervisor_id = models.IntegerField(null=True, blank=True)
    supervisor_remarks = models.TextField(blank=True, null=True)
    reviewer_photo = models.ImageField(upload_to='reviewer_photos/', null=True, blank=True)
    supervised_at = models.DateTimeField(null=True, blank=True)

    inspector_photo = models.ImageField(upload_to='inspector_photos/', null=True, blank=True)
    checker_id = models.IntegerField(null=True, blank=True)
    checked_at = models.DateTimeField(null=True, blank=True)
    checker_remarks = models.TextField(blank=True, null=True)

    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Submission for {self.checklist_item.title} - {self.status}"





class StageHistory(models.Model):
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('move_to_next_stage', 'Move to Next Stage'),
        ('move_to_next_phase', 'Move to Next Phase'),
        ('completed', 'Completed'),
    ]

    project = models.IntegerField(null=True, blank=True)
    zone = models.IntegerField(null=True, blank=True)
    flat = models.IntegerField(null=True, blank=True)
    room = models.IntegerField(null=True, blank=True)
    checklist = models.ForeignKey('Checklist', on_delete=models.CASCADE, null=True, blank=True)

    phase_id = models.IntegerField(null=True, blank=True)
    stage = models.IntegerField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='started')
    completed_by_name=models.CharField(null=True,blank=True,max_length=40)
    crm_completed_by_name=models.CharField(null=True,blank=True,max_length=40)
    crm_completed_by = models.IntegerField(null=True, blank=True)
    crm_hoto=models.BooleanField(default=False)
    crm_date=models.DateTimeField(null=True,blank=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        unique_together = ('project', 'stage', 'zone', 'flat', 'room', 'checklist')
        indexes = [
            models.Index(fields=['project', 'zone', 'flat', 'room', 'checklist', 'is_current'], name='ix_stage_history_lookup')
        ]

    def __str__(self):
        idents = []
        if self.zone:
            idents.append(f"Zone:{self.zone}")
        if self.flat:
            idents.append(f"Flat:{self.flat}")
        if self.room:
            idents.append(f"Room:{self.room}")
        return f"StageHistory[{self.project}, {self.stage}] - {'/'.join(idents)} - Status: {self.status}"





def submission_image_upload_to(instance, filename):
    return f"submission_images/s{instance.submission_id}/{filename}"

SUBMISSION_MEDIA_ROLE = [
    ("maker", "Maker"),
    ("supervisor", "Supervisor"),
    ("checker", "Checker"),
    ("inspector", "Inspector"),
]

class ChecklistItemSubmissionImage(models.Model):
    """
    Extra images attached to a ChecklistItemSubmission.
    Does NOT replace existing single image fields; purely additive.
    """
    submission = models.ForeignKey(
        'ChecklistItemSubmission',
        on_delete=models.CASCADE,
        related_name='extra_images'
    )
    image = models.ImageField(upload_to=submission_image_upload_to)
    who_did = models.CharField(max_length=20, choices=SUBMISSION_MEDIA_ROLE)
    uploaded_by_id = models.IntegerField(null=True, blank=True)  # user id from your Users service
    remarks = models.TextField(blank=True, null=True)
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['submission', 'who_did', '-captured_at'], name='ix_subm_img_lookup')
        ]
        ordering = ['-captured_at']

    def __str__(self):
        return f"Image[{self.id}] for Sub#{self.submission_id} by {self.who_did}"


def all_media(self):
    """
    Returns a unified list of all media (legacy single-image fields + extra_images).
    Useful for read-only display in APIs.
    """
    items = []
    if self.maker_media:
        items.append({"role": "maker", "source": "legacy", "field": "maker_media", "url": getattr(self.maker_media, "url", None)})
    if self.reviewer_photo:
        items.append({"role": "supervisor", "source": "legacy", "field": "reviewer_photo", "url": getattr(self.reviewer_photo, "url", None)})
    if self.inspector_photo:
        items.append({"role": "inspector", "source": "legacy", "field": "inspector_photo", "url": getattr(self.inspector_photo, "url", None)})
    for im in self.extra_images.all():
        items.append({
            "role": im.who_did,
            "source": "extra",
            "id": im.id,
            "url": getattr(im.image, "url", None),
            "remarks": im.remarks,
            "uploaded_by_id": im.uploaded_by_id,
            "captured_at": im.captured_at,
        })
    return items


