from django.contrib.auth.models import AbstractUser
from django.db import models

USER_ROLE_CHOICES = (
    ('ADMIN', 'Admin'),
    ('INITIALIZER', 'Initializer'),
    ('SUPERVISOR', 'Supervisor'),
    ('CHECKER', 'Checker'),
    ('MAKER', 'Maker'),
    
)

class User(AbstractUser):
    phone_number = models.CharField(max_length=15, blank=True)
    gender = models.CharField(max_length=10, blank=True)
    address = models.TextField(blank=True)
    has_access = models.BooleanField(default=True)
    is_client = models.BooleanField(default=False)
    is_manager = models.BooleanField(default=False)
    org = models.IntegerField(null=True, blank=True)
    company = models.IntegerField(null=True, blank=True)
    entity = models.IntegerField(null=True, blank=True)
    created_by = models.ForeignKey('self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_users'
    )

    def __str__(self):
        return self.username


class UserAccess(models.Model):  
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='accesses')
    project_id = models.IntegerField(null=True, blank=True)
    building_id = models.IntegerField(null=True, blank=True)
    zone_id = models.IntegerField(null=True, blank=True)
    flat_id = models.IntegerField(null=True, blank=True)
    All_checklist = models.BooleanField(default=False)
    purpose_id = models.IntegerField(null=True, blank=True, db_index=True)
    phase_id = models.IntegerField(null=True, blank=True, db_index=True)
    stage_id = models.IntegerField(null=True, blank=True, db_index=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    all_cat = models.BooleanField(default=False)
    category = models.IntegerField(null=True, blank=True)
    CategoryLevel1 = models.IntegerField(null=True, blank=True)
    CategoryLevel2 = models.IntegerField(null=True, blank=True)
    CategoryLevel3 = models.IntegerField(null=True, blank=True)
    CategoryLevel4 = models.IntegerField(null=True, blank=True)
    CategoryLevel5 = models.IntegerField(null=True, blank=True)
    CategoryLevel6 = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} Access to Project {self.project_id}"


class UserAccessRole(models.Model):
    user_access = models.ForeignKey(UserAccess, on_delete=models.CASCADE, related_name='roles')
    role = models.CharField(max_length=50, choices=USER_ROLE_CHOICES)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_access', 'role')



from django.db import models
from django.contrib.auth.hashers import make_password

class StaffRegistration(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    gender = models.CharField(max_length=10)
    address = models.TextField()
    project_id = models.CharField(max_length=50)
    role= models.CharField(max_length=50)
    password = models.CharField(max_length=255)
    profile_photo = models.ImageField(upload_to='staff_photos/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):

        if not self.pk or 'password' in self.get_dirty_fields():
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


'''
from django.db import models
from django.contrib.auth.hashers import make_password

class StaffRegistration(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    gender = models.CharField(max_length=10)
    address = models.TextField()
    project_id = models.CharField()
    role = models.CharField(max_length=50)
    password = models.CharField(max_length=128)  
    is_active = models.BooleanField(default=False)
    image = models.ImageField(upload_to='image/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # password encryption
        self.password = make_password(self.password)
        super(StaffRegistration, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}" '''

class StaffAttendance(models.Model):
    staff = models.ForeignKey(StaffRegistration, on_delete=models.CASCADE, related_name="attendances")
    staff_image = models.ImageField(upload_to="staff_images/", null=True, blank=True)
    check_in = models.TimeField()
    check_out = models.TimeField(null=True, blank=True)
    date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.staff.first_name} - {self.date}"