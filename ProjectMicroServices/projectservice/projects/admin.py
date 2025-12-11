from django.contrib import admin
from .models import *

admin.site.register([Project,Purpose,Phase,Category,Stage,Building,Level,Zone,Subzone,Flat,Flattype,Rooms,TransferRule])