from django.contrib import admin
from .models import User, UserAccess, UserAccessRole 
# Register your models here.
admin.site.register([User,UserAccess,UserAccessRole])