import json
import traceback
from collections import defaultdict

import requests
from django.db import models, transaction
from django.db.models import (
    Q, Exists, OuterRef, Subquery, F, Case, When, IntegerField
)
from django.utils import timezone

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import LimitOffsetPagination

from .models import (
    Checklist, ChecklistItem, ChecklistItemOption, ChecklistItemSubmission
)
from .serializers import (
    ChecklistSerializer,
    ChecklistItemSerializer,
    ChecklistItemOptionSerializer,
    ChecklistItemSubmissionSerializer,
    ChecklistWithItemsAndFilteredSubmissionsSerializer,
    ChecklistWithNestedItemsSerializer,
    ChecklistWithItemsAndPendingSubmissionsSerializer,
    ChecklistWithItemsAndSubmissionsSerializer,
    ChecklistWithItemsAndPendingSubmissionsSerializer  # if required
)
from django.db import transaction


# local="192.168.1.14"
local="konstruct.world"
# local="192.168.0.202"

import os
import requests
import weasyprint

from datetime import datetime

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
import weasyprint

from .models import Checklist


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.conf import settings
from django.template.loader import render_to_string
import weasyprint
import requests
import os
from datetime import datetime

class FlatReportAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    BASE_PROJECT_API = "https://konstruct.world/projects"
    BASE_USER_API = "https://konstruct.world/users/users"

    def get(self, request, flat_id):
        token = self._get_token(request)

        # --- Get flat + project details ---
        flat_data = self._get_flat_details(flat_id, token)
        if not flat_data:
            return Response({"error": "Flat not found"}, status=status.HTTP_404_NOT_FOUND)

        # --- Get all checklists for flat ---
        checklists = Checklist.objects.filter(flat_id=flat_id)
        data = {
            "flat": flat_data,
            "summary": self._build_summary(checklists),
            "report_date": self._current_date(),
            "checklists": []
        }

        for checklist in checklists:
            checklist_data = {
                "id": checklist.id,
                "name": checklist.name,
                "is_user_generated": getattr(checklist, "user_generated", False),
                "items": []
            }

            for item in checklist.items.all():
                submissions = []
                for sub in item.submissions.all():
                    submissions.append({
                        "status": sub.status,
                        "maker_name": self._get_user_name(sub.maker_id, token),
                        "supervisor_name": self._get_user_name(sub.supervisor_id, token),
                        "checker_name": self._get_user_name(sub.checker_id, token),
                        "maker_remarks": sub.maker_remarks,
                        "supervisor_remarks": sub.supervisor_remarks,
                        "checker_remarks": sub.checker_remarks,
                        "remarks": sub.remarks,
                        "maker_at": sub.maker_at,
                        "supervised_at": sub.supervised_at,
                        "checked_at": sub.checked_at,
                        "maker_media": self._get_file_url(sub.maker_media),
                        "reviewer_photo": self._get_file_url(sub.reviewer_photo),
                        "inspector_photo": self._get_file_url(sub.inspector_photo),
                    })

                checklist_data["items"].append({
                    "title": item.title,
                    "status": item.status,
                    "submissions": submissions
                })

            data["checklists"].append(checklist_data)

        # --- Generate PDF ---
        pdf_url = self._generate_pdf(flat_id, data)
        data["pdf_url"] = pdf_url
        return Response(data, status=status.HTTP_200_OK)

    # ===================== Helpers =====================

    def _get_token(self, request):
        auth_header = request.headers.get("Authorization")
        return auth_header.split(" ")[1] if auth_header and " " in auth_header else auth_header

    def _get_file_url(self, file_field):
        """
        Ensure all file/media URLs are absolute and contain /checklists/media/
        """
        if not file_field:
            return None

        file_str = str(file_field)

        # If already a full URL
        if file_str.startswith("http"):
            if "checklists/" not in file_str:
                # Fix missing /checklists/
                return file_str.replace("https://konstruct.world/", "https://konstruct.world/checklists/")
            return file_str

        # If it's relative path (e.g. maker_media/filename.jpg)
        return f"https://konstruct.world/checklists/media/{file_str}"

    def _get_flat_details(self, flat_id, token):
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        flat_resp = requests.get(f"{self.BASE_PROJECT_API}/flats/{flat_id}/", headers=headers)
        if flat_resp.status_code != 200:
            return None
        flat = flat_resp.json()

        # --- Resolve names ---
        if flat.get("project"):
            project_resp = requests.get(f"{self.BASE_PROJECT_API}/{flat['project']}/", headers=headers)
            if project_resp.status_code == 200:
                flat["project_name"] = project_resp.json().get("name")

        if flat.get("building"):
            building_resp = requests.get(f"{self.BASE_PROJECT_API}/buildings/{flat['building']}/", headers=headers)
            if building_resp.status_code == 200:
                flat["building_name"] = building_resp.json().get("name")

        if flat.get("level"):
            level_resp = requests.get(f"{self.BASE_PROJECT_API}/levels/{flat['level']}/", headers=headers)
            if level_resp.status_code == 200:
                flat["level_name"] = level_resp.json().get("name")

        if flat.get("flattype"):
            ft_resp = requests.get(f"{self.BASE_PROJECT_API}/flattypes/{flat['flattype']}/", headers=headers)
            if ft_resp.status_code == 200:
                flat["flattype_name"] = ft_resp.json().get("type_name")

        return flat

    def _get_user_name(self, user_id, token):
        if not user_id:
            return None
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            resp = requests.get(f"{self.BASE_USER_API}/{user_id}/", headers=headers)
            if resp.status_code == 200:
                user = resp.json()
                full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                return full_name or user.get("username")
        except Exception:
            pass
        return None

    def _build_summary(self, checklists):
        total = pending = completed = rejected = 0
        for checklist in checklists:
            for item in checklist.items.all():
                total += 1
                if item.status in ["not_started", "pending_for_maker", "pending_for_supervisor"]:
                    pending += 1
                elif item.status == "completed":
                    completed += 1
                elif item.status.startswith("rejected"):
                    rejected += 1
        return {
            "total_checkpoints": total,
            "pending": pending,
            "completed": completed,
            "rejected": rejected
        }

    def _generate_pdf(self, flat_id, data):
        html = render_to_string("reports/flat_report.html", data)
        report_path = os.path.join(settings.MEDIA_ROOT, f"reports/flat_{flat_id}_report.pdf")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        weasyprint.HTML(string=html, base_url=settings.BASE_DIR).write_pdf(report_path)
        return f"https://konstruct.world/checklists/media/reports/flat_{flat_id}_report.pdf"

    def _current_date(self):
        return datetime.now().strftime("%d-%m-%Y")


#class FlatReportAPIView(APIView):
#    permission_classes = [permissions.IsAuthenticated]
#
#    BASE_PROJECT_API = "https://konstruct.world/projects"
#    BASE_USER_API = "https://konstruct.world/users/users"
#
#    def get(self, request, flat_id):
#        token = self._get_token(request)
#
#        flat_data = self._get_flat_details(flat_id, token)
#        if not flat_data:
#            return Response({"error": "Flat not found"}, status=status.HTTP_404_NOT_FOUND)
#
#        checklists = Checklist.objects.filter(flat_id=flat_id)
#        data = {
#            "flat": flat_data,
#            "summary": self._build_summary(checklists),
#            "report_date": self._current_date(),
#            "checklists": []
#        }
#
#        for checklist in checklists:
#            checklist_data = {
#                "id": checklist.id,
#                "name": checklist.name,
#                "is_user_generated": getattr(checklist, "user_generated", False),
#                "items": []
#            }
#
#            for item in checklist.items.all():
#                submissions = []
#                for sub in item.submissions.all():
#                    submissions.append({
#                        "status": sub.status,
#                        "maker_name": self._get_user_name(sub.maker_id, token),
#                        "supervisor_name": self._get_user_name(sub.supervisor_id, token),
#                        "checker_name": self._get_user_name(sub.checker_id, token),
#                        "maker_remarks": sub.maker_remarks,
#                        "supervisor_remarks": sub.supervisor_remarks,
#                        "checker_remarks": sub.checker_remarks,
#                        "remarks": sub.remarks,
#                        "maker_at": sub.maker_at,
#                        "supervised_at": sub.supervised_at,
#                        "checked_at": sub.checked_at,
#                        # Ensure absolute URLs for images
#                        "maker_media": self._get_file_url(request, sub.maker_media),
#                        "reviewer_photo": self._get_file_url(request, sub.reviewer_photo),
#                        "inspector_photo": self._get_file_url(request, sub.inspector_photo),
#                    })
#                checklist_data["items"].append({
#                    "title": item.title,
#                    "status": item.status,
#                    "submissions": submissions
#                })
#
#            data["checklists"].append(checklist_data)
#
#        pdf_url = self._generate_pdf(flat_id, data)
#        data["pdf_url"] = pdf_url
#        return Response(data, status=status.HTTP_200_OK)
#
#    # --- Helper methods ---
#    def _get_file_url(self, request, file_field):
#        if not file_field:
#            return None
#        if str(file_field).startswith("http"):
#            return str(file_field)
#        return request.build_absolute_uri(file_field.url)
#
#    def _get_token(self, request):
#        auth_header = request.headers.get("Authorization")
#        return auth_header.split(" ")[1] if auth_header and " " in auth_header else auth_header
#
#    def _get_flat_details(self, flat_id, token):
#        headers = {"Authorization": f"Bearer {token}"} if token else {}
#
#        flat_resp = requests.get(f"{self.BASE_PROJECT_API}/flats/{flat_id}/", headers=headers)
#        if flat_resp.status_code != 200:
#            return None
#        flat = flat_resp.json()
#
#        if flat.get("project"):
#            project_resp = requests.get(f"{self.BASE_PROJECT_API}/{flat['project']}/", headers=headers)
#            if project_resp.status_code == 200:
#                flat["project_name"] = project_resp.json().get("name")
#
#        if flat.get("building"):
#            building_resp = requests.get(f"{self.BASE_PROJECT_API}/buildings/{flat['building']}/", headers=headers)
#            if building_resp.status_code == 200:
#                flat["building_name"] = building_resp.json().get("name")
#
#        if flat.get("level"):
#            level_resp = requests.get(f"{self.BASE_PROJECT_API}/levels/{flat['level']}/", headers=headers)
#            if level_resp.status_code == 200:
#                flat["level_name"] = level_resp.json().get("name")
#
#        if flat.get("flattype"):
#            ft_resp = requests.get(f"{self.BASE_PROJECT_API}/flattypes/{flat['flattype']}/", headers=headers)
#            if ft_resp.status_code == 200:
#                flat["flattype_name"] = ft_resp.json().get("type_name")
#
#        return flat
#
#    def _get_user_name(self, user_id, token):
#        if not user_id:
#            return None
#        headers = {"Authorization": f"Bearer {token}"} if token else {}
#        try:
#            resp = requests.get(f"{self.BASE_USER_API}/{user_id}/", headers=headers)
#            if resp.status_code == 200:
#                user = resp.json()
#                full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
#                return full_name or user.get("username")
#        except:
#            pass
#        return None
#
#    def _build_summary(self, checklists):
#        total = pending = completed = rejected = 0
#        for checklist in checklists:
#            for item in checklist.items.all():
#                total += 1
#                if item.status in ["not_started", "pending_for_maker", "pending_for_supervisor"]:
#                    pending += 1
#                elif item.status == "completed":
#                    completed += 1
#                elif item.status.startswith("rejected"):
#                    rejected += 1
#        return {"total_checkpoints": total, "pending": pending, "completed": completed, "rejected": rejected}
#
#    def _generate_pdf(self, flat_id, data):
#        html = render_to_string("reports/flat_report.html", data)
#        report_path = os.path.join(settings.MEDIA_ROOT, f"reports/flat_{flat_id}_report.pdf")
#        os.makedirs(os.path.dirname(report_path), exist_ok=True)
#        weasyprint.HTML(string=html, base_url=settings.BASE_DIR).write_pdf(report_path)
#        return f"https://konstruct.world/checklists/media/reports/flat_{flat_id}_report.pdf"
#
#    def _current_date(self):
#        from datetime import datetime
#        return datetime.now().strftime("%d-%m-%Y")
#




class UserGeneratedChecklist(APIView):
    permission_classes = [permissions.IsAuthenticated]
    BASE_ROLE_API = "https://konstruct.world/users/"
    ALLOWED_ROLES = ["CHECKER"]

    def get_user_role(self, request, user_id, project_id):
        url = f"{self.BASE_ROLE_API}/user-role-for-project/?user_id={user_id}&project_id={project_id}"
        headers = {}
        auth_header = request.headers.get("Authorization")
        if auth_header:
            headers["Authorization"] = auth_header
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.json().get("role")
        return None

    def post(self, request):
        data = request.data
        user = request.user

        required_fields = [
            'flat_id', 'project_id', 'name', 'purpose_id'
        ]
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return Response(
                {"error": f"Missing required fields: {', '.join(missing_fields)}"},
                status=400
            )

        flat_id = data['flat_id']
        project_id = data['project_id']

        role = self.get_user_role(request, user.id, project_id)
        if not role or role.upper() not in self.ALLOWED_ROLES:
            return Response(
                {"detail": f"Only users with roles: {', '.join(self.ALLOWED_ROLES)} can create this checklist."},
                status=403
            )

        checklist_fields = {
            'name': data['name'],
            'description': data.get('description', ''),
            'status': data.get('status', 'not_started'),
            'project_id': project_id,
            'flat_id': flat_id,
            'user_generated_id': user.id,
            'purpose_id': data['purpose_id'],
            'phase_id': data.get('phase_id'),
            'stage_id': data.get('stage_id'),
            'category': data.get('category'),
            'category_level1': data.get('category_level1'),
            'category_level2': data.get('category_level2'),
            'category_level3': data.get('category_level3'),
            'category_level4': data.get('category_level4'),
            'category_level5': data.get('category_level5'),
            'category_level6': data.get('category_level6'),
            'remarks': data.get('remarks', ''),
        }

        items = data.get('items')
        if not items or not isinstance(items, list):
            return Response({"error": "At least one item (list) is required."}, status=400)

        for idx, item in enumerate(items):
            if not item.get('title'):
                return Response({"error": f"Item at index {idx} missing 'title'."}, status=400)
            options = item.get('options')
            if not options or not isinstance(options, list):
                return Response({"error": f"Item '{item.get('title', idx)}' must have at least one option."}, status=400)

        try:
            with transaction.atomic():
                checklist = Checklist.objects.create(**checklist_fields)
                for item in items:
                    checklist_item = ChecklistItem.objects.create(
                        checklist=checklist,
                        title=item.get('title'),
                        description=item.get('description', ''),
                        status=item.get('status', 'not_started'),
                        ignore_now=item.get('ignore_now', False),
                        photo_required=item.get('photo_required', False)
                    )

                    for option in item['options']:
                        if not option.get('name'):
                            return Response(
                                {"error": f"Checklist item '{item.get('title')}' option missing 'name'."},
                                status=400
                            )
                        ChecklistItemOption.objects.create(
                            checklist_item=checklist_item,
                            name=option.get('name'),
                            choice=option.get('choice', 'P')
                        )

                # Set checklist status to work_in_progress and save
                checklist.status = "work_in_progress"
                checklist.save(update_fields=["status"])

                for checklist_item in checklist.items.all():
                    # 1. Create the "rejected_by_checker" submission
                    ChecklistItemSubmission.objects.create(
                        checklist_item=checklist_item,
                        status="rejected_by_checker",
                        checker_id=user.id,
                        checker_remarks=data.get("checker_remarks", ""),  # Optionally accept from data
                        checked_at=timezone.now(),
                        inspector_photo=request.FILES.get("inspector_photo"),
                        attempts=1
                    )
                    # 2. Create the new "created" submission (for maker, attempt=2)
                    ChecklistItemSubmission.objects.create(
                        checklist_item=checklist_item,
                        status="created",
                        checker_id=user.id,
                        attempts=2
                    )
        except Exception as e:
            return Response(
                {"error": f"Failed to create checklist: {str(e)}"},
                status=500
            )

        return Response(
            {"message": "Checklist created successfully.", "checklist_id": checklist.id},
            status=201
        )





class RoleBasedChecklistAPIView(APIView):
    permission_classes = [IsAuthenticated]

    BASE_ROLE_API = f"http://{local}:8000/api"

    def get_user_role(self, request, user_id, project_id):
        url = f"{self.BASE_ROLE_API}/user-role-for-project/?user_id={user_id}&project_id={project_id}"
        headers = {}
        auth_header = request.headers.get("Authorization")
        if auth_header:
            headers["Authorization"] = auth_header
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.json().get("role")
        return None
    
    def safe_int(self, val):
        if val is None:
            return None
        try:
            return int(str(val).strip("/"))
        except Exception as e:
            print(f"Could not convert {val} to int: {e}")
            return None

    def get(self, request):
        user_id = request.query_params.get("user_id") or request.user.id
        project_id = request.query_params.get("project_id")
        if not user_id or not project_id:
            return Response({"detail": "user_id and project_id required"}, status=400)

        role = self.get_user_role(request, user_id, project_id)
        if not role:
            return Response({"detail": "Could not determine role"}, status=403)

        if role == "Intializer":
            return self.handle_intializer(request, user_id, project_id)
        elif role == "SUPERVISOR":
            return self.handle_supervisor(request, user_id, project_id)
        elif role == "CHECKER":
            return self.handle_checker(request, user_id, project_id)
        elif role == "MAKER":
            return self.handle_maker(request, user_id, project_id)
        else:
            return Response({"detail": f"Role '{role}' not supported"}, status=400)

    def handle_intializer(self, request, user_id, project_id):
        print('FOR INTIALIZER')
        USER_SERVICE_URL = f"http://{local}:8000/api/user-access/"
        ROOM_SERVICE_URL = f"http://{local}:8001/api/rooms/"
        
        user_id = request.user.id
        project_id = request.query_params.get("project_id")
        tower_id = request.query_params.get("tower_id")
        flat_id = request.query_params.get("flat_id")
        zone_id = request.query_params.get("zone_id")

        tower_id = self.safe_nt(tower_id)
        flat_id = self.safe_nt(flat_id)
        zone_id = self.safe_nt(zone_id)
        project_id = self.safe_nt(project_id)
        
        print("Parsed IDs:", tower_id, flat_id, zone_id, project_id)
        
        if not user_id or not project_id:
            return Response({"detail": "user_id and project_id required."}, status=400)

        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        try:
            resp = requests.get(
                USER_SERVICE_URL,
                params={"user_id": user_id, "project_id": project_id},
                timeout=5,
                headers=headers
            )
            if resp.status_code != 200:
                return Response({"detail": "Could not fetch user access"}, status=400)
            accesses = resp.json()
        except Exception as e:
            return Response({"detail": "User service error", "error": str(e)}, status=400)

        # Step 1: Filter by location
        checklist_filter = Q(project_id=project_id)
        if flat_id:
            checklist_filter &= Q(flat_id=flat_id)
        elif zone_id:
            checklist_filter &= Q(zone_id=zone_id, flat_id__isnull=True, room_id__isnull=True)
        elif tower_id:
            checklist_filter &= Q(building_id=tower_id, zone_id__isnull=True, flat_id__isnull=True, room_id__isnull=True)
        else:
            checklist_filter &= Q(building_id__isnull=True, zone_id__isnull=True, flat_id__isnull=True, room_id__isnull=True)

        # Step 2: Filter by category access
        category_filter = Q()
        for access in accesses:
            if access.get('category'):
                category_filter |= self.get_branch_q(access)

        checklists = Checklist.objects.filter(checklist_filter)
        if category_filter:
            checklists = checklists.filter(category_filter).distinct()
        else:
            checklists = Checklist.objects.none()

        # Order by status="not_started" first
        checklists = checklists.annotate(
            status_priority=Case(
                When(status="not_started", then=0),
                default=1,
                output_field=IntegerField()
            )
        ).order_by('status_priority', 'id')

        # Pagination
        paginator = LimitOffsetPagination()
        paginator.default_limit = 10
        paginated_checklists = paginator.paginate_queryset(checklists, request, view=self)

        # Room enrichment for current page only
        room_ids = set([c.room_id for c in paginated_checklists if c.room_id is not None])
        room_details = {}
        for room_id in room_ids:
            try:
                room_resp = requests.get(f"{ROOM_SERVICE_URL}{room_id}", headers=headers, timeout=5)
                if room_resp.status_code == 200:
                    room_details[room_id] = room_resp.json()
            except Exception:
                continue

        serialized_checklists = ChecklistSerializer(paginated_checklists, many=True).data
        
        # Add items and options to each checklist
        for checklist in serialized_checklists:
            checklist_id = checklist['id']
            items = ChecklistItem.objects.filter(checklist=checklist_id)
            checklist['items'] = []
            for item in items:
                item_data = ChecklistItemSerializer(item).data
                options = ChecklistItemOption.objects.filter(checklist_item=item.id)
                item_data['options'] = ChecklistItemOptionSerializer(options, many=True).data
                checklist['items'].append(item_data)

        # Group by room
        grouped = defaultdict(lambda: {"room_id": None, "count": 0, "checklists": []})
        for checklist in serialized_checklists:
            room_id = checklist.get('room_id')
            if room_id and room_id in room_details:
                checklist['room_details'] = room_details[room_id]
            grouped[room_id]["room_id"] = room_id
            grouped[room_id]["checklists"].append(checklist)
            grouped[room_id]["count"] += 1

        response_data = list(grouped.values())
        return paginator.get_paginated_response(response_data)
   
    def handle_checker(self, request, user_id, project_id):
            print('=== FOR CHECKER ===')
            USER_SERVICE_URL = f"http://{local}:8000/api/user-access/"
            ROOM_SERVICE_URL = f"http://{local}:8001/api/rooms/"
            
            user_id = request.user.id
            project_id = request.query_params.get("project_id")
            tower_id = request.query_params.get("tower_id")
            zone_id = request.query_params.get("zone_id")
            flat_id = request.query_params.get("flat_id")

            tower_id = self.safe_nt(tower_id)
            flat_id = self.safe_nt(flat_id)
            zone_id = self.safe_nt(zone_id)
            project_id = self.safe_nt(project_id)
            
            print(f"DEBUG: Parsed IDs - tower_id: {tower_id}, flat_id: {flat_id}, zone_id: {zone_id}, project_id: {project_id}")
            print(f"DEBUG: Current user_id: {user_id}")
            
            if not user_id or not project_id:
                print("ERROR: Missing user_id or project_id")
                return Response({"detail": "user_id and project_id required."}, status=400)

            token = None
            auth_header = request.headers.get("Authorization")
            if auth_header:
                token = auth_header.split(" ")[1] if " " in auth_header else auth_header
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            print(f"DEBUG: Auth headers prepared: {bool(headers)}")

            try:
                print(f"DEBUG: Fetching user access from {USER_SERVICE_URL}")
                resp = requests.get(
                    USER_SERVICE_URL,
                    params={"user_id": user_id, "project_id": project_id},
                    timeout=5,
                    headers=headers
                )
                print(f"DEBUG: User access response status: {resp.status_code}")
                if resp.status_code != 200:
                    print(f"ERROR: Failed to fetch user access: {resp.text}")
                    return Response({"detail": "Could not fetch user access"}, status=400)
                accesses = resp.json()
                print(f"DEBUG: User accesses count: {len(accesses)}")
                for i, access in enumerate(accesses):
                    print(f"  Access {i}: category={access.get('category')}, flat_id={access.get('flat_id')}, zone_id={access.get('zone_id')}")
            except Exception as e:
                print(f"ERROR: User service error: {str(e)}")
                return Response({"detail": "User service error", "error": str(e)}, status=400)

            # Build category access filter
            print("DEBUG: Building category access filter...")
            q = Q()
            for access in accesses:
                cat_q = Q()
                if access.get('category'):
                    cat_q &= Q(category=access['category'])
                    print(f"  Added category filter: {access['category']}")
                    for i in range(1, 7):
                        key = f'CategoryLevel{i}'
                        if access.get(key) is not None:
                            cat_q &= Q(**{f'category_level{i}': access[key]})
                            print(f"    Added level {i}: {access[key]}")
                        else:
                            break
                q |= (cat_q)
            print(f"DEBUG: Final category filter built: {bool(q)}")

            # Apply user filter input
            print("DEBUG: Building location filter...")
            checklist_filter = Q(project_id=project_id)
            if flat_id:
                checklist_filter &= Q(flat_id=flat_id)
                print(f"  Applied flat_id filter: {flat_id}")
            elif zone_id:
                checklist_filter &= Q(zone_id=zone_id, flat_id__isnull=True, room_id__isnull=True)
                print(f"  Applied zone_id filter: {zone_id}")
            elif tower_id:
                checklist_filter &= Q(building_id=tower_id, zone_id__isnull=True, flat_id__isnull=True, room_id__isnull=True)
                print(f"  Applied tower_id filter: {tower_id}")
            else:
                checklist_filter &= Q(building_id__isnull=True, zone_id__isnull=True, flat_id__isnull=True, room_id__isnull=True)
                print("  Applied project-level filter")

            base_qs = Checklist.objects.filter(checklist_filter)
            if q:
                base_qs = base_qs.filter(q).distinct()
            else:
                base_qs = Checklist.objects.none()

            print(f"DEBUG: Base queryset count: {base_qs.count()}")
            
            # Sample some checklists for debugging
            sample_checklists = list(base_qs[:3])
            for i, checklist in enumerate(sample_checklists):
                # print(f"  Sample checklist {i+1}: ID={checklist.id}, title='{checklist.title}', room_id={checklist.room_id}")
                
                # Check items for this checklist
                items = ChecklistItem.objects.filter(checklist=checklist)
                print(f"    Total items: {items.count()}")
                
                pending_items = items.filter(status="pending_for_inspector")
                print(f"    Pending for inspector items: {pending_items.count()}")
                
                for j, item in enumerate(pending_items[:2]):  # Show first 2 items
                    submissions = ChecklistItemSubmission.objects.filter(checklist_item=item)
                    print(f"      Item {j+1}: ID={item.id}, status={item.status}, submissions_count={submissions.count()}")
                    
                    for k, sub in enumerate(submissions[:2]):  # Show first 2 submissions
                        print(f"        Submission {k+1}: checker_id={sub.checker_id}, status={sub.status}")

            print("DEBUG: Getting checklists with pending_for_inspector items...")
            # Simple approach: Get all checklists that have items with pending_for_inspector status
            all_checklists = base_qs.filter(
                items__status="pending_for_inspector"
            ).distinct()

            print(f"Found {all_checklists.count()} checklists with pending_for_inspector items")

            print("DEBUG: Applying pagination...")
            paginator = LimitOffsetPagination()
            paginator.default_limit = 10
            paginated_checklists = paginator.paginate_queryset(all_checklists, request, view=self)
            print(f"DEBUG: Paginated to {len(paginated_checklists) if paginated_checklists else 0} checklists")

            print("DEBUG: Fetching room details...")
            room_ids = set([c.room_id for c in paginated_checklists if c.room_id is not None])
            print(f"DEBUG: Unique room IDs: {room_ids}")
            
            room_details = {}
            for room_id in room_ids:
                try:
                    room_resp = requests.get(f"{ROOM_SERVICE_URL}{room_id}", headers=headers, timeout=5)
                    if room_resp.status_code == 200:
                        room_details[room_id] = room_resp.json()
                        print(f"  Fetched room {room_id}: {room_details[room_id].get('name', 'Unknown')}")
                    else:
                        print(f"  Failed to fetch room {room_id}: {room_resp.status_code}")
                except Exception as e:
                    print(f"  Error fetching room {room_id}: {str(e)}")
                    continue

            print("DEBUG: Serializing checklists...")
            try:
                serialized_checklists = ChecklistWithItemsAndSubmissionsSerializer(paginated_checklists, many=True).data
                print(f"DEBUG: Serialized {len(serialized_checklists)} checklists")
                
                # Debug: Show structure of first checklist
                if serialized_checklists:
                    first_checklist = serialized_checklists[0]
                    print(f"DEBUG: First checklist structure:")
                    print(f"  ID: {first_checklist.get('id')}")
                    print(f"  Keys: {list(first_checklist.keys())}")
                    if 'items' in first_checklist:
                        items = first_checklist['items']
                        print(f"  Items count: {len(items)}")
                        if items:
                            first_item = items[0]
                            print(f"  First item keys: {list(first_item.keys())}")
                            print(f"  First item status: {first_item.get('status')}")
                            print(f"  First item submissions: {first_item.get('submissions', 'NOT_FOUND')}")
                    else:
                        print("  No 'items' key found!")
                        
            except Exception as e:
                print(f"ERROR: Serialization failed: {str(e)}")
                return Response({"detail": f"Serialization error: {str(e)}"}, status=500)

            print("DEBUG: Grouping by room and assignment status...")
            grouped = defaultdict(lambda: {
                "room_id": None,
                "room_details": None,
                "assigned_to_me": [],
                "available_for_me": []
            })

            for i, checklist in enumerate(serialized_checklists):
                room_id = checklist.get('room_id')
                print(f"  Processing checklist {i+1}: ID={checklist.get('id')}, room_id={room_id}")
                
                # Add room details if available
                if room_id and room_id in room_details:
                    checklist['room_details'] = room_details[room_id]
                    grouped[room_id]["room_details"] = room_details[room_id]
                    print(f"    Added room details for room {room_id}")
                
                grouped[room_id]["room_id"] = room_id
                
                # Check if this checklist has assigned items for current user
# FIXED: Simple logic for items with no submissions
                has_assigned_items = False
                has_available_items = False

                for item in checklist.get('items', []):
                    if item.get('status') == 'pending_for_inspector':
                        item_submissions = item.get('submissions', [])
                        print(f"      Item {item.get('id')}: status={item.get('status')}, submissions={len(item_submissions)}")
                        
                        if len(item_submissions) == 0:
                            # No submissions = Available for me
                            has_available_items = True
                            print(f"      Item {item.get('id')} is AVAILABLE (no submissions)")
                        else:
                            # Has submissions - check if assigned to current user
                            is_assigned_to_me = any(
                                sub.get('checker_id') == user_id
                                for sub in item_submissions
                            )
                            if is_assigned_to_me:
                                has_assigned_items = True
                                print(f"      Item {item.get('id')} is ASSIGNED to me")

                print(f"    Final: has_assigned={has_assigned_items}, has_available={has_available_items}")
                print(f"    has_assigned_items: {has_assigned_items}, has_available_items: {has_available_items}")
                
                if has_assigned_items:
                    grouped[room_id]["assigned_to_me"].append(checklist)
                    print(f"    Added to assigned_to_me for room {room_id}")
                if has_available_items:
                    grouped[room_id]["available_for_me"].append(checklist)
                    print(f"    Added to available_for_me for room {room_id}")

            response_data = list(grouped.values())
            print(f"DEBUG: Final response has {len(response_data)} room groups")
            
            for i, room_group in enumerate(response_data):
                print(f"  Room group {i+1}: room_id={room_group['room_id']}, assigned={len(room_group['assigned_to_me'])}, available={len(room_group['available_for_me'])}")

            print("DEBUG: Returning paginated response")
            return paginator.get_paginated_response(response_data)

    def handle_maker(self, request, user_id, project_id):
        print('FOR MAKER')
        USER_SERVICE_URL = f"http://{local}:8000/api/user-access/"
        ROOM_SERVICE_URL = f"http://{local}:8001/api/rooms/"
        
        user_id = request.user.id
        project_id = request.query_params.get("project_id")
        flat_id = request.query_params.get("flat_id")
        zone_id = request.query_params.get("zone_id")
        tower_id = request.query_params.get("tower_id")

        tower_id = self.safe_nt(tower_id)
        flat_id = self.safe_nt(flat_id)
        zone_id = self.safe_nt(zone_id)
        project_id = self.safe_nt(project_id)
        
        print("Parsed IDs:", tower_id, flat_id, zone_id, project_id)
        
        if not user_id or not project_id:
            return Response({"detail": "user_id and project_id required."}, status=400)

        # Auth headers
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            parts = auth_header.strip().split(" ")
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        try:
            resp = requests.get(
                USER_SERVICE_URL,
                params={"user_id": user_id, "project_id": project_id},
                timeout=5,
                headers=headers
            )
            if resp.status_code != 200:
                return Response({"detail": "Could not fetch user access"}, status=400)
            accesses = resp.json()
        except Exception as e:
            return Response({"detail": "User service error", "error": str(e)}, status=400)

        # Build category/location filter Q
        q = Q()
        for access in accesses:
            cat_q = Q()
            if access.get('category'):
                cat_q &= Q(category=access['category'])
                for i in range(1, 7):
                    key = f'CategoryLevel{i}'
                    if access.get(key) is not None:
                        cat_q &= Q(**{f'category_level{i}': access[key]})
                    else:
                        break


            q |= (cat_q )

        # Direct checklist filter from query params
        checklist_filter = Q(project_id=project_id)
        if flat_id:
            checklist_filter &= Q(flat_id=flat_id)
        elif zone_id:
            checklist_filter &= Q(zone_id=zone_id, flat_id__isnull=True, room_id__isnull=True)
        elif tower_id:
            checklist_filter &= Q(building_id=tower_id, zone_id__isnull=True, flat_id__isnull=True, room_id__isnull=True)
        else:
            checklist_filter &= Q(building_id__isnull=True, zone_id__isnull=True, flat_id__isnull=True, room_id__isnull=True)

        checklist_qs = Checklist.objects.filter(checklist_filter)
        if q:
            checklist_qs = checklist_qs.filter(q).distinct()
        else:
            checklist_qs = Checklist.objects.none()

        # Get latest submission per item
        latest_submission_subq = ChecklistItemSubmission.objects.filter(
            checklist_item=OuterRef('pk')
        ).order_by('-attempts', '-created_at').values('id')[:1]

        base_items = ChecklistItem.objects.filter(
            checklist__in=checklist_qs,
            status="pending_for_maker"
        ).annotate(
            latest_submission_id=Subquery(latest_submission_subq)
        )

        # Get all checklists that have maker items (either assigned or available)
        checklists_with_maker_items = checklist_qs.filter(
            items__in=base_items
        ).distinct()

        # Pagination on checklists
        paginator = LimitOffsetPagination()
        paginator.default_limit = 10
        paginated_checklists = paginator.paginate_queryset(checklists_with_maker_items, request, view=self)

        # Room enrichment for current page only
        room_ids = set([c.room_id for c in paginated_checklists if c.room_id is not None])
        room_details = {}
        for room_id in room_ids:
            try:
                room_resp = requests.get(f"{ROOM_SERVICE_URL}{room_id}", headers=headers, timeout=5)
                if room_resp.status_code == 200:
                    room_details[room_id] = room_resp.json()
            except Exception:
                continue

        # Group by room and split assigned/available within each room
        grouped = defaultdict(lambda: {
            "room_id": None,
            "room_details": None,
            "assigned_to_me": [],
            "available_for_me": []
        })

        for checklist in paginated_checklists:
            room_id = checklist.room_id
            
            # Add room details if available
            if room_id and room_id in room_details:
                grouped[room_id]["room_details"] = room_details[room_id]
            
            grouped[room_id]["room_id"] = room_id
            
            # Get items for this checklist
            checklist_items = base_items.filter(checklist=checklist)
            
            # Assigned to current maker (rework items)
            rework_items = checklist_items.filter(
                submissions__id=F('latest_submission_id'),
                submissions__maker_id=user_id,
                submissions__status="created"
            ).distinct()

            # Not yet assigned to any maker (fresh items)
            fresh_items = checklist_items.filter(
                submissions__id=F('latest_submission_id'),
                submissions__maker_id__isnull=True,
                submissions__status="created"
            ).distinct()

            # Serialize items with submission details
            def serialize_items_with_submission(qs):
                out = []
                for item in qs:
                    item_data = ChecklistItemSerializer(item).data
                    latest_sub = ChecklistItemSubmission.objects.filter(
                        checklist_item=item
                    ).order_by('-attempts', '-created_at').first()
                    item_data["latest_submission"] = (
                        ChecklistItemSubmissionSerializer(latest_sub, context={"request": self.request}).data
                        if latest_sub else None
                    )
                    item_data["checklist_info"] = ChecklistSerializer(checklist).data
                    out.append(item_data)
                return out

            if rework_items.exists():
                grouped[room_id]["assigned_to_me"].extend(serialize_items_with_submission(rework_items))
            if fresh_items.exists():
                grouped[room_id]["available_for_me"].extend(serialize_items_with_submission(fresh_items))

        # Remove empty rooms
        response_data = [room_data for room_data in grouped.values() 
                        if room_data["assigned_to_me"] or room_data["available_for_me"]]
        
        return paginator.get_paginated_response(response_data)

    def handle_supervisor(self, request, user_id, project_id):
        print('FOR SUPERVISOR')
        USER_SERVICE_URL = f"http://{local}:8000/api/user-access/"
        
        user_id = request.user.id
        project_id = request.query_params.get("project_id")
        flat_id = request.query_params.get("flat_id")
        zone_id = request.query_params.get("zone_id")
        tower_id = request.query_params.get("tower_id")

        tower_id = self.safe_nt(tower_id)
        flat_id = self.safe_nt(flat_id)
        zone_id = self.safe_nt(zone_id)
        project_id = self.safe_nt(project_id)
        
        print("Parsed IDs:", tower_id, flat_id, zone_id, project_id)
        
        if not user_id or not project_id:
            return Response({"detail": "user_id and project_id required."}, status=400)

        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        try:
            resp = requests.get(
                USER_SERVICE_URL,
                params={"user_id": user_id, "project_id": project_id},
                timeout=5,
                headers=headers
            )
            if resp.status_code != 200:
                return Response({"detail": "Could not fetch user access"}, status=400)
            accesses = resp.json()
        except Exception as e:
            return Response({"detail": "User service error", "error": str(e)}, status=400)

        # Build Q filter based on user access
        q = Q()
        for access in accesses:
            cat_q = Q()
            if access.get("category"):
                cat_q &= Q(category=access["category"])
                for i in range(1, 7):
                    key = f"CategoryLevel{i}"
                    if access.get(key) is not None:
                        cat_q &= Q(**{f"category_level{i}": access[key]})
                    else:
                        break

            # loc_q = Q()
            # if access.get("flat_id"):
            #     loc_q &= Q(flat_id=access["flat_id"])
            # elif access.get("zone_id"):
            #     loc_q &= Q(zone_id=access["zone_id"], flat_id__isnull=True, room_id__isnull=True)
            # elif access.get("building_id"):
            #     loc_q &= Q(building_id=access["building_id"], zone_id__isnull=True, flat_id__isnull=True, room_id__isnull=True)
            # elif access.get("project_id"):
            #     loc_q &= Q(building_id__isnull=True, zone_id__isnull=True, flat_id__isnull=True, room_id__isnull=True)

            q |= (cat_q )

        # User-applied filtering
        checklist_filter = Q(project_id=project_id)
        if flat_id:
            checklist_filter &= Q(flat_id=flat_id)
        elif zone_id:
            checklist_filter &= Q(zone_id=zone_id, flat_id__isnull=True, room_id__isnull=True)
        elif tower_id:
            checklist_filter &= Q(building_id=tower_id, zone_id__isnull=True, flat_id__isnull=True, room_id__isnull=True)
        else:
            checklist_filter &= Q(building_id__isnull=True, zone_id__isnull=True, flat_id__isnull=True, room_id__isnull=True)

        checklist_qs = Checklist.objects.filter(checklist_filter)
        if q:
            checklist_qs = checklist_qs.filter(q).distinct()
        else:
            checklist_qs = Checklist.objects.none()

        # Subquery to get latest submission
        latest_submission_subq = ChecklistItemSubmission.objects.filter(
            checklist_item=OuterRef("pk")
        ).order_by("-attempts", "-created_at").values("id")[:1]

        base_items = ChecklistItem.objects.filter(
            checklist__in=checklist_qs,
            status="pending_for_supervisor"
        ).annotate(
            latest_submission_id=Subquery(latest_submission_subq)
        )

        # Assigned to supervisor
        assigned_to_me = base_items.filter(
            submissions__id=F("latest_submission_id"),
            submissions__supervisor_id=user_id,
            submissions__status="pending_supervisor"
        ).distinct()

        # Available for supervisor
        available_for_me = base_items.filter(
            submissions__id=F("latest_submission_id"),
            submissions__supervisor_id__isnull=True,
            submissions__status="pending_supervisor"
        ).distinct()

        # Paginate both querysets
        paginator = LimitOffsetPagination()
        paginator.default_limit = 10
        
        assigned_paginated = paginator.paginate_queryset(assigned_to_me, request, view=self)
        available_paginated = paginator.paginate_queryset(available_for_me, request, view=self)

        # Serialize each item + its latest submission + options
        def serialize_items_with_details(qs):
            if not qs:
                return []
            out = []
            for item in qs:
                item_data = ChecklistItemSerializer(item).data

                latest_sub = ChecklistItemSubmission.objects.filter(
                    checklist_item=item
                ).order_by("-attempts", "-created_at").first()

                item_data["latest_submission"] = (
                    ChecklistItemSubmissionSerializer(latest_sub, context={"request": request}).data
                    if latest_sub else None
                )

                options = ChecklistItemOption.objects.filter(checklist_item=item)
                item_data["options"] = ChecklistItemOptionSerializer(options, many=True).data

                out.append(item_data)
            return out

        response = {
            "pending_for_me": serialize_items_with_details(assigned_paginated),
            "available_for_me": serialize_items_with_details(available_paginated),
        }

        return Response(response, status=200)           


ROLE_STATUS_MAP = {
    "checker": ["pending_for_inspector", "completed", "pending_for_maker"],
    "maker": ["pending_for_maker", "completed", "pending_for_supervisor"],
    "supervisor": ["pending_for_supervisor", "completed", "pending_for_inspector"],
}

class RoleBasedChecklistTRANSFERRULEAPIView(APIView):
    permission_classes = [IsAuthenticated]
    BASE_ROLE_API = f"https://{local}/users"

    ROLE_STATUS_MAP = {
        "checker": ["pending_for_inspector", "completed", "pending_for_maker"],
        "maker": ["pending_for_maker", "tetmpory_inspctor", "completed", "pending_for_supervisor"],
        "supervisor": ["tetmpory_inspctor", "pending_for_supervisor", "completed", "tetmpory_Maker"],
    }

    def get_branch_q(self,access):
        """
        Returns a Q object matching all checklists in the branch described by this access.
        e.g. if access has category=10, category_level1=9, will match all checklists with
        category=10, category_level1=9, regardless of deeper levels.
        """
        q = Q()
        if access.get('category'):
            q &= Q(category=access.get('category'))
        for i in range(1, 7):
            key = f'CategoryLevel{i}'
            val = access.get(key)
            if val is not None:
                q &= Q(**{f'category_level{i}': val})
            else:
                break  # Stop at first missing level
        return q


    def get_user_role(self, request, user_id, project_id):
        url = f"{self.BASE_ROLE_API}/user-role-for-project/?user_id={user_id}&project_id={project_id}"
        headers = {}
        auth_header = request.headers.get("Authorization")
        if auth_header:
            headers["Authorization"] = auth_header
        else:
            print("WARNING: No Authorization header present in incoming request!")
        print("FORWARDED AUTH HEADER:", headers.get("Authorization"))
        resp = requests.get(url, headers=headers)
        print("USER ROLE RESP STATUS:", resp.status_code, resp.text)
        if resp.status_code == 200:
            return resp.json().get("role")
        return None

    def get_true_level(self, project_id):
        TRANSFER_RULE_API = f"https://{local}/projects/transfer-rules/"
        try:
            resp = requests.get(TRANSFER_RULE_API, params={"project_id": project_id})
            if resp.status_code == 200 and resp.json():
                return resp.json()[0].get("true_level")
        except Exception as e:
            print("TransferRule error:", e)
        return None

    def safe_nt(self, val):
        if val is None:
            return None
        try:
            return int(str(val).strip("/"))
        except Exception as e:
            print(f"Could not convert {val} to int: {e}")
            return None

    def paginate_and_group(self, request, checklists, headers):
        paginator = LimitOffsetPagination()
        paginator.default_limit = 10
        paginated_checklists = paginator.paginate_queryset(checklists, request, view=self)

        room_ids = set([c.room_id for c in paginated_checklists if c.room_id is not None])
        room_details = {}
        for room_id in room_ids:
            try:
                room_resp = requests.get(f"https://{local}/projects/rooms/{room_id}", headers=headers, timeout=5)
                if room_resp.status_code == 200:
                    room_details[room_id] = room_resp.json()
            except Exception:
                continue

        serialized_checklists = ChecklistSerializer(paginated_checklists, many=True).data
        for checklist in serialized_checklists:
            checklist_id = checklist['id']
            items = ChecklistItem.objects.filter(checklist=checklist_id)
            checklist['items'] = []
            for item in items:
                item_data = ChecklistItemSerializer(item).data
                options = ChecklistItemOption.objects.filter(checklist_item=item.id)
                item_data['options'] = ChecklistItemOptionSerializer(options, many=True).data
                checklist['items'].append(item_data)

        grouped = defaultdict(lambda: {"room_id": None, "count": 0, "checklists": []})
        for checklist in serialized_checklists:
            room_id = checklist.get('room_id')
            if room_id and room_id in room_details:
                checklist['room_details'] = room_details[room_id]
            grouped[room_id]["room_id"] = room_id
            grouped[room_id]["checklists"].append(checklist)
            grouped[room_id]["count"] += 1

        response_data = list(grouped.values())
        return paginator.get_paginated_response(response_data)

    def all_items_have_status(self, checklists, allowed_statuses):
        filtered = []
        for checklist in checklists:
            items = checklist.items.all()
            item_count = items.count()
            valid_count = items.filter(status__in=allowed_statuses).count()
            print(
                f"[DEBUG] Checklist {checklist.id}: item_count={item_count}, "
                f"valid_count={valid_count}, statuses={[i.status for i in items]}"
            )
            if item_count > 0 and item_count == valid_count:
                filtered.append(checklist)
        return filtered

    def filter_by_level(self, checklists, allowed_statuses, true_level):
        to_send = []

        if true_level == "checklist_level":
            to_send = self.all_items_have_status(checklists, allowed_statuses)

        elif true_level == "flat_level":
            flats = checklists.values_list('flat_id', flat=True).distinct()
            for flat_id in flats:
                if flat_id is None:
                    continue
                project_id = checklists.first().project_id if checklists.exists() else None
                flat_checklists_all = Checklist.objects.filter(flat_id=flat_id, project_id=project_id)
                flat_checklists_filtered = checklists.filter(flat_id=flat_id)
                if len(self.all_items_have_status(flat_checklists_all, allowed_statuses)) == flat_checklists_all.count():
                    to_send.extend(list(flat_checklists_filtered))

        elif true_level == "room_level":
            rooms = checklists.values_list('room_id', flat=True).distinct()
            for room_id in rooms:
                if room_id is None:
                    continue
                project_id = checklists.first().project_id if checklists.exists() else None
                room_checklists_all = Checklist.objects.filter(room_id=room_id, project_id=project_id)
                room_checklists_filtered = checklists.filter(room_id=room_id)
                if len(self.all_items_have_status(room_checklists_all, allowed_statuses)) == room_checklists_all.count():
                    to_send.extend(list(room_checklists_filtered))

        elif true_level == "Zone_level":
            towers = checklists.values_list('building_id', flat=True).distinct()
            for building_id in towers:
                if building_id is None:
                    continue
                project_id = checklists.first().project_id if checklists.exists() else None
                tower_checklists_all = Checklist.objects.filter(building_id=building_id, project_id=project_id)
                tower_checklists_filtered = checklists.filter(building_id=building_id)
                if len(self.all_items_have_status(tower_checklists_all, allowed_statuses)) == tower_checklists_all.count():
                    to_send.extend(list(tower_checklists_filtered))

        elif true_level == "level_id":
            levels = checklists.values_list('level_id', flat=True).distinct()
            for level_id in levels:
                if level_id is None:
                    continue
                project_id = checklists.first().project_id if checklists.exists() else None
                level_checklists_all = Checklist.objects.filter(level_id=level_id, project_id=project_id)
                level_checklists_filtered = checklists.filter(level_id=level_id)
                if len(self.all_items_have_status(level_checklists_all, allowed_statuses)) == level_checklists_all.count():
                    to_send.extend(list(level_checklists_filtered))

        else:
            return Response({"invalid tranfer rule": "Not available"}, status=400)

        return to_send

    def get(self, request):
        user_id = request.user.id
        project_id = request.query_params.get("project_id")
        if not user_id or not project_id:
            return Response({"detail": "user_id and project_id required"}, status=400)

        role = self.get_user_role(request, user_id, project_id)
        if not role:
            return Response({"detail": "Could not determine role"}, status=403)

        print(f"🔍 BACKEND DEBUG - Detected Role: {role} for User: {user_id}")

        if role == "Intializer":
            return self.handle_intializer(request, user_id, project_id)
        elif role.upper() == "SUPERVISOR":
            return self.handle_supervisor(request, user_id, project_id)
        elif role.upper() == "CHECKER":
            return self.handle_checker(request, user_id, project_id)
        elif role.upper() == "MAKER":
            return self.handle_maker(request, user_id, project_id)
        elif role.lower() == "manager":
            return self.handle_manager_client(request, user_id, project_id)
        elif role.lower() == "client":
            return self.handle_manager_client(request, user_id, project_id)
        else:
            return Response({"detail": f"Role '{role}' not supported"}, status=400)

    def handle_manager_client(self, request, user_id, project_id):
        flat_id = request.query_params.get("flat_id")
        flat_id = self.safe_nt(flat_id)

        checklist_filter = Q(project_id=project_id)
        if flat_id:
            checklist_filter &= Q(flat_id=flat_id)

        checklists = Checklist.objects.filter(checklist_filter)

        # PAGINATE!
        paginator = LimitOffsetPagination()
        paginator.default_limit = 10   # or any default
        paginated_checklists = paginator.paginate_queryset(checklists, request, view=self)

        data = []
        for checklist in paginated_checklists:
            checklist_data = {
                "id": checklist.id,
                "title": checklist.name,
                "flat_id": checklist.flat_id,
                "status": checklist.status,
                "items": [],
            }
            items = ChecklistItem.objects.filter(checklist=checklist)
            for item in items:
                item_data = {
                    "id": item.id,
                    "title": item.title,
                    "status": item.status,
                    "description": item.description,
                    "submissions": []
                }
                submissions = ChecklistItemSubmission.objects.filter(checklist_item=item)
                item_data["submissions"] = ChecklistItemSubmissionSerializer(submissions, many=True).data
                checklist_data["items"].append(item_data)
            data.append(checklist_data)
        return paginator.get_paginated_response(data)

    def handle_intializer(self, request, user_id, project_id):
        print('🔍 BACKEND DEBUG - FOR INTIALIZER')
        USER_SERVICE_URL = f"https://{local}/users/user-access/"
        user_id = request.user.id
        project_id = request.query_params.get("project_id")
        tower_id = request.query_params.get("tower_id")
        flat_id = request.query_params.get("flat_id")
        zone_id = request.query_params.get("zone_id")

        tower_id = self.safe_nt(tower_id)
        flat_id = self.safe_nt(flat_id)
        zone_id = self.safe_nt(zone_id)
        project_id = self.safe_nt(project_id)

        if not user_id or not project_id:
            return Response({"detail": "user_id and project_id required."}, status=400)

        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        try:
            resp = requests.get(
                USER_SERVICE_URL,
                params={"user_id": user_id, "project_id": project_id},
                timeout=5,
                headers=headers
            )
            if resp.status_code != 200:
                return Response({"detail": "Could not fetch user access"}, status=400)
            accesses = resp.json()
        except Exception as e:
            return Response({"detail": "User service error", "error": str(e)}, status=400)

        checklist_filter = Q(project_id=project_id)
        if flat_id:
            checklist_filter &= Q(flat_id=flat_id)
        elif zone_id:
            checklist_filter &= Q(zone_id=zone_id, flat_id_isnull=True, room_id_isnull=True)
        elif tower_id:
            checklist_filter &= Q(building_id=tower_id, zone_id_isnull=True, flat_idisnull=True, room_id_isnull=True)
        else:
            checklist_filter &= Q(building_id_isnull=True, zone_idisnull=True, flat_idisnull=True, room_id_isnull=True)

        checklists = Checklist.objects.filter(checklist_filter)

        category_filter = Q()
        for access in accesses:
            if access.get('category'):
                category_filter |= self.get_branch_q(access)

        if category_filter:
            status_param = request.query_params.get("status")
            if status_param:
                if "," in status_param:
                    statuses = [s.strip() for s in status_param.split(",")]
                    checklists = checklists.filter(category_filter, status__in=statuses).distinct()
                else:
                    checklists = checklists.filter(category_filter, status=status_param).distinct()
            else:
                checklists = checklists.filter(category_filter, status="not_started").distinct()
        else:
            checklists = Checklist.objects.none()

        return self.paginate_and_group(request, checklists, headers)

    def handle_checker(self, request, user_id, project_id):
        print('🔍 BACKEND DEBUG - FOR CHECKER')
        USER_SERVICE_URL = f"https://{local}/users/user-access/"
        user_id = request.user.id
        project_id = request.query_params.get("project_id")
        tower_id = request.query_params.get("tower_id")
        zone_id = request.query_params.get("zone_id")
        flat_id = request.query_params.get("flat_id")

        tower_id = self.safe_nt(tower_id)
        flat_id = self.safe_nt(flat_id)
        zone_id = self.safe_nt(zone_id)
        project_id = self.safe_nt(project_id)

        if not user_id or not project_id:
            return Response({"detail": "user_id and project_id required."}, status=400)

        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        try:
            resp = requests.get(
                USER_SERVICE_URL,
                params={"user_id": user_id, "project_id": project_id},
                timeout=5,
                headers=headers
            )
            if resp.status_code != 200:
                return Response({"detail": "Could not fetch user access"}, status=400)
            accesses = resp.json()
        except Exception as e:
            return Response({"detail": "User service error", "error": str(e)}, status=400)

        category_filter = Q()
        for access in accesses:
            if access.get('category'):
                category_filter |= self.get_branch_q(access)

        checklist_filter = Q(project_id=project_id)
        if flat_id:
            checklist_filter &= Q(flat_id=flat_id)
        elif zone_id:
            checklist_filter &= Q(zone_id=zone_id, flat_id_isnull=True, room_id_isnull=True)
        elif tower_id:
            checklist_filter &= Q(building_id=tower_id, zone_id_isnull=True, flat_idisnull=True, room_id_isnull=True)
        else:
            checklist_filter &= Q(building_id_isnull=True, zone_idisnull=True, flat_idisnull=True, room_id_isnull=True)

        base_qs = Checklist.objects.filter(checklist_filter)
        if category_filter:
            base_qs = base_qs.filter(category_filter).distinct()
        else:
            base_qs = Checklist.objects.none()


        assigned_item_exists = ChecklistItem.objects.filter(
            checklist=OuterRef('pk'),
            status="pending_for_inspector",
            submissions__checker_id=user_id,
            submissions__status="pending_checker"
        )

        available_item_exists = ChecklistItem.objects.filter(
            checklist=OuterRef('pk'),
            status="pending_for_inspector",
            submissions__checker_id__isnull=True
        )

        assigned_to_me = base_qs.annotate(has_assigned=Exists(assigned_item_exists)).filter(has_assigned=True)
        available_for_me = base_qs.annotate(has_available=Exists(available_item_exists)).filter(has_available=True)

        true_level = self.get_true_level(project_id)
        if true_level:
            allowed_statuses = self.ROLE_STATUS_MAP["checker"]
            assigned_to_me = self.filter_by_level(assigned_to_me, allowed_statuses, true_level)
            available_for_me = self.filter_by_level(available_for_me, allowed_statuses, true_level)

        return self.paginate_and_group_checker(request, assigned_to_me, available_for_me, headers)

    def paginate_and_group_checker(self, request, assigned_checklists, available_checklists, headers):
        all_checklists = list(assigned_checklists) + list(available_checklists)
        seen = set()
        unique_checklists = []
        for checklist in all_checklists:
            if checklist.id not in seen:
                unique_checklists.append(checklist)
                seen.add(checklist.id)

        paginator = LimitOffsetPagination()
        paginator.default_limit = 10
        paginated_checklists = paginator.paginate_queryset(unique_checklists, request, view=self)

        room_ids = set([c.room_id for c in paginated_checklists if c.room_id is not None])
        room_details = {}
        for room_id in room_ids:
            try:
                room_resp = requests.get(f"https://{local}/projects/rooms/{room_id}", headers=headers, timeout=5)
                if room_resp.status_code == 200:
                    room_details[room_id] = room_resp.json()
            except Exception:
                continue

        grouped = defaultdict(lambda: {
            "room_id": None,
            "room_details": None,
            "assigned_to_me": [],
            "available_for_me": []
        })

        for checklist in paginated_checklists:
            room_id = checklist.room_id
            if room_id and room_id in room_details:
                grouped[room_id]["room_details"] = room_details[room_id]
            grouped[room_id]["room_id"] = room_id

            checklist_data = ChecklistSerializer(checklist).data
            items = ChecklistItem.objects.filter(checklist=checklist.id, status="pending_for_inspector")
            checklist_data['items'] = []
            for item in items:
                item_data = ChecklistItemSerializer(item).data
                options = ChecklistItemOption.objects.filter(checklist_item=item.id)
                item_data['options'] = ChecklistItemOptionSerializer(options, many=True).data
                submissions = ChecklistItemSubmission.objects.filter(checklist_item=item.id)
                item_data['submissions'] = ChecklistItemSubmissionSerializer(
                    submissions, many=True, context={"request": self.request}
                ).data
                checklist_data['items'].append(item_data)
            if checklist in assigned_checklists:
                grouped[room_id]["assigned_to_me"].append(checklist_data)
            if checklist in available_checklists:
                grouped[room_id]["available_for_me"].append(checklist_data)

        response_data = [
            room_data for room_data in grouped.values()
            if room_data["assigned_to_me"] or room_data["available_for_me"]
        ]

        # -------- ADD THIS BLOCK FOR USER-GENERATED CHECKLISTS ----------
        project_id = request.query_params.get("project_id")
        user_generated_qs = Checklist.objects.filter(
            user_generated_id__isnull=False,
            project_id=project_id,
            room_id__isnull=True  # Only those NOT assigned to a room
        )
        user_generated_serialized = []
        for checklist in user_generated_qs:
            checklist_data = ChecklistSerializer(checklist).data
            # Fetch all items (no status filter)
            items = ChecklistItem.objects.filter(checklist=checklist)
            checklist_data['items'] = []
            for item in items:
                item_data = ChecklistItemSerializer(item).data
                options = ChecklistItemOption.objects.filter(checklist_item=item.id)
                item_data['options'] = ChecklistItemOptionSerializer(options, many=True).data
                submissions = ChecklistItemSubmission.objects.filter(checklist_item=item.id)
                item_data['submissions'] = ChecklistItemSubmissionSerializer(
                    submissions, many=True, context={"request": self.request}
                ).data
                checklist_data['items'].append(item_data)
            user_generated_serialized.append(checklist_data)
        # ---------------------------------------------------------------

        response = paginator.get_paginated_response(response_data)
        response.data['user_generated_checklists'] = user_generated_serialized
        return response

    def handle_supervisor(self, request, user_id, project_id):
        print('🔍 BACKEND DEBUG - FOR SUPERVISOR')
        USER_SERVICE_URL = f"https://{local}/users/user-access/"

        user_id = request.user.id
        project_id = request.query_params.get("project_id")
        flat_id = request.query_params.get("flat_id")
        zone_id = request.query_params.get("zone_id")
        tower_id = request.query_params.get("tower_id")

        tower_id = self.safe_nt(tower_id)
        flat_id = self.safe_nt(flat_id)
        zone_id = self.safe_nt(zone_id)
        project_id = self.safe_nt(project_id)

        print(f"🔍 BACKEND DEBUG - SUPERVISOR Query Params: project_id={project_id}, flat_id={flat_id}, user_id={user_id}")

        if not user_id or not project_id:
            return Response({"detail": "user_id and project_id required."}, status=400)

        # Auth headers
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        try:
            resp = requests.get(
                USER_SERVICE_URL,
                params={"user_id": user_id, "project_id": project_id},
                timeout=5,
                headers=headers
            )
            if resp.status_code != 200:
                return Response({"detail": "Could not fetch user access"}, status=400)
            accesses = resp.json()
            print(f"🔍 BACKEND DEBUG - SUPERVISOR User Accesses: {accesses}")
        except Exception as e:
            return Response({"detail": "User service error", "error": str(e)}, status=400)

        # Build category filter
        category_filter = Q()
        for access in accesses:
            if access.get('category'):
                category_filter |= self.get_branch_q(access)

        # Direct checklist filter from query params
        checklist_filter = Q(project_id=project_id)
        if flat_id:
            checklist_filter &= Q(flat_id=flat_id)
        elif zone_id:
            checklist_filter &= Q(
                zone_id=zone_id,
                flat_id__isnull=True,
                room_id__isnull=True)
        elif tower_id:
            checklist_filter &= Q(
                building_id=tower_id,
                zone_id__isnull=True,
                flat_id__isnull=True,
                room_id__isnull=True)
        else:
            checklist_filter &= Q(
                building_id__isnull=True,
                zone_id__isnull=True,
                flat_id__isnull=True,
                room_id__isnull=True)

        base_qs = Checklist.objects.filter(checklist_filter)
        if category_filter:
            base_qs = base_qs.filter(category_filter).distinct()
        else:
            base_qs = Checklist.objects.none()


        print(f"🔍 BACKEND DEBUG - SUPERVISOR Base Checklist Count: {base_qs.count()}")

        assigned_item_exists = ChecklistItem.objects.filter(
            checklist=OuterRef('pk'),
            status="pending_for_supervisor",
            submissions__supervisor_id=user_id,
            submissions__status="pending_supervisor"
        )

        # Check for available items (not assigned to any supervisor)
        available_item_exists = ChecklistItem.objects.filter(
            checklist=OuterRef('pk'),
            status="pending_for_supervisor",
            submissions__supervisor_id__isnull=True
        )

        assigned_to_me = base_qs.annotate(
            has_assigned=Exists(assigned_item_exists)
        ).filter(has_assigned=True)

        available_for_me = base_qs.annotate(
            has_available=Exists(available_item_exists)
        ).filter(has_available=True)

        print(f"🔍 BACKEND DEBUG - SUPERVISOR Assigned Checklists: {assigned_to_me.count()}")
        print(f"🔍 BACKEND DEBUG - SUPERVISOR Available Checklists: {available_for_me.count()}")

        true_level = self.get_true_level(project_id)
        if true_level:
            allowed_statuses = self.ROLE_STATUS_MAP["supervisor"]
            assigned_to_me = self.filter_by_level(assigned_to_me, allowed_statuses, true_level)
            available_for_me = self.filter_by_level(available_for_me, allowed_statuses, true_level)
            print(f"🔍 BACKEND DEBUG - SUPERVISOR After Transfer Rule - Assigned: {len(assigned_to_me)}, Available: {len(available_for_me)}")
        assigned_ids = set(c.id for c in assigned_to_me)
        available_for_me = [c for c in available_for_me if c.id not in assigned_ids]
        print(available_for_me)
        return self.paginate_and_group_supervisor(request, assigned_to_me, available_for_me, headers)

    def paginate_and_group_supervisor(self, request, assigned_checklists, available_checklists, headers):
        all_checklists = list(assigned_checklists) + list(available_checklists)
        seen = set()
        unique_checklists = []
        for checklist in all_checklists:
            if checklist.id not in seen:
                unique_checklists.append(checklist)
                seen.add(checklist.id)

        paginator = LimitOffsetPagination()
        paginator.default_limit = 10
        paginated_checklists = paginator.paginate_queryset(unique_checklists, request, view=self)

        room_ids = set([c.room_id for c in paginated_checklists if c.room_id is not None])
        room_details = {}
        for room_id in room_ids:
            try:
                room_resp = requests.get(f"https://{local}/projects/rooms/{room_id}", headers=headers, timeout=5)
                if room_resp.status_code == 200:
                    room_details[room_id] = room_resp.json()
            except Exception:
                continue

        grouped = defaultdict(lambda: {
            "room_id": None,
            "room_details": None,
            "assigned_to_me": [],
            "available_for_me": []
        })

        for checklist in paginated_checklists:
            room_id = checklist.room_id
            if room_id and room_id in room_details:
                grouped[room_id]["room_details"] = room_details[room_id]
            grouped[room_id]["room_id"] = room_id

            checklist_data = ChecklistSerializer(checklist).data
            items = ChecklistItem.objects.filter(checklist=checklist.id, status="pending_for_supervisor")
            checklist_data['items'] = []
            for item in items:
                item_data = ChecklistItemSerializer(item).data
                options = ChecklistItemOption.objects.filter(checklist_item=item.id)
                item_data['options'] = ChecklistItemOptionSerializer(options, many=True).data
                submissions = ChecklistItemSubmission.objects.filter(checklist_item=item.id)
                item_data['submissions'] = ChecklistItemSubmissionSerializer(
                    submissions, many=True, context={"request": self.request}
                ).data

                checklist_data['items'].append(item_data)

            if checklist in assigned_checklists:
                grouped[room_id]["assigned_to_me"].append(checklist_data)
            if checklist in available_checklists:
                grouped[room_id]["available_for_me"].append(checklist_data)

        response_data = [
            room_data for room_data in grouped.values()
            if room_data["assigned_to_me"] or room_data["available_for_me"]
        ]

        # -------- ADD THIS BLOCK FOR USER-GENERATED CHECKLISTS ----------
        project_id = request.query_params.get("project_id")
        user_generated_qs = Checklist.objects.filter(
            user_generated_id__isnull=False,
            project_id=project_id,
            room_id__isnull=True  # Only those NOT assigned to a room
        )
        user_generated_serialized = []
        for checklist in user_generated_qs:
            checklist_data = ChecklistSerializer(checklist).data
            # Fetch all items (no status filter)
            items = ChecklistItem.objects.filter(checklist=checklist)
            checklist_data['items'] = []
            for item in items:
                item_data = ChecklistItemSerializer(item).data
                options = ChecklistItemOption.objects.filter(checklist_item=item.id)
                item_data['options'] = ChecklistItemOptionSerializer(options, many=True).data
                submissions = ChecklistItemSubmission.objects.filter(checklist_item=item.id)
                item_data['submissions'] = ChecklistItemSubmissionSerializer(
                    submissions, many=True, context={"request": self.request}
                ).data
                checklist_data['items'].append(item_data)
            user_generated_serialized.append(checklist_data)
        # ---------------------------------------------------------------

        response = paginator.get_paginated_response(response_data)
        response.data['user_generated_checklists'] = user_generated_serialized
        return response

    def handle_maker(self, request, user_id, project_id):
        print('🔍 BACKEND DEBUG - FOR MAKER')
        USER_SERVICE_URL = f"https://{local}/users/user-access/"
        ROOM_SERVICE_URL = f"https://{local}/projects/rooms/"

        user_id = request.user.id
        project_id = self.safe_nt(request.query_params.get("project_id"))
        flat_id = self.safe_nt(request.query_params.get("flat_id"))
        zone_id = self.safe_nt(request.query_params.get("zone_id"))
        tower_id = self.safe_nt(request.query_params.get("tower_id"))

        if not user_id or not project_id:
            return Response({"detail": "user_id and project_id required."}, status=400)

        # Auth headers
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            parts = auth_header.strip().split(" ")
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        try:
            resp = requests.get(
                USER_SERVICE_URL,
                params={"user_id": user_id, "project_id": project_id},
                timeout=5,
                headers=headers
            )
            if resp.status_code != 200:
                return Response({"detail": "Could not fetch user access"}, status=400)
            accesses = resp.json()
        except Exception as e:
            return Response({"detail": "User service error", "error": str(e)}, status=400)

        # Build filter
        category_filter = Q()
        for access in accesses:
            if access.get('category'):
                category_filter |= self.get_branch_q(access)

        checklist_filter = Q(project_id=project_id)
        if flat_id:
            checklist_filter &= Q(flat_id=flat_id)
        elif zone_id:
            checklist_filter &= Q(zone_id=zone_id, flat_id_isnull=True, room_id_isnull=True)
        elif tower_id:
            checklist_filter &= Q(building_id=tower_id, zone_id_isnull=True, flat_idisnull=True, room_id_isnull=True)
        else:
            checklist_filter &= Q(building_id_isnull=True, zone_idisnull=True, flat_idisnull=True, room_id_isnull=True)

        checklist_qs = Checklist.objects.filter(checklist_filter)
        if checklist_filter:
            checklist_qs = checklist_qs.filter(checklist_filter).distinct()
        else:
            checklist_qs = Checklist.objects.none()

        print(f"🔍 BACKEND DEBUG - MAKER Base Checklist Count: {checklist_qs.count()}")

        # find checklists that have pending_for_maker items
        latest_submission_subq = ChecklistItemSubmission.objects.filter(
            checklist_item=OuterRef('pk')
        ).order_by('-attempts', '-created_at').values('id')[:1]

        base_items = ChecklistItem.objects.filter(
            checklist__in=checklist_qs,
            status="pending_for_maker"
        ).annotate(
            latest_submission_id=Subquery(latest_submission_subq)
        )

        checklists_with_maker_items = checklist_qs.filter(items__in=base_items).distinct()

        # Apply transfer rule filtering only at the end
        true_level = self.get_true_level(project_id)
        if true_level:
            allowed_statuses = self.ROLE_STATUS_MAP["maker"]
            checklists_with_maker_items = self.filter_by_level(checklists_with_maker_items, allowed_statuses, true_level)

        # Pagination
        paginator = LimitOffsetPagination()
        paginator.default_limit = 10
        paginated_checklists = paginator.paginate_queryset(checklists_with_maker_items, request, view=self)

        # Add room info and group
        room_ids = set([c.room_id for c in paginated_checklists if c.room_id is not None])
        room_details = {}
        for room_id in room_ids:
            try:
                room_resp = requests.get(f"{ROOM_SERVICE_URL}{room_id}", headers=headers, timeout=5)
                if room_resp.status_code == 200:
                    room_details[room_id] = room_resp.json()
            except Exception:
                continue

        grouped = defaultdict(lambda: {
            "room_id": None,
            "room_details": None,
            "assigned_to_me": [],
            "available_for_me": []
        })

        for checklist in paginated_checklists:
            room_id = checklist.room_id

            # Add room details if available
            if room_id and room_id in room_details:
                grouped[room_id]["room_details"] = room_details[room_id]
            grouped[room_id]["room_id"] = room_id

            # Get items for this checklist
            checklist_items = base_items.filter(checklist=checklist)

            # Assigned to current maker (rework items)
            rework_items = checklist_items.filter(
                submissions__id=F('latest_submission_id'),
                submissions__maker_id=user_id,
                submissions__status="created"
            ).distinct()

            # Not yet assigned to any maker (fresh items)
            fresh_items = checklist_items.filter(
                submissions__id=F('latest_submission_id'),
                submissions__maker_id__isnull=True
            ).distinct()

            # Serialize items with submission details
            def serialize_items_with_submission(qs):
                out = []
                for item in qs:
                    item_data = ChecklistItemSerializer(item).data
                    latest_sub = ChecklistItemSubmission.objects.filter(
                        checklist_item=item
                    ).order_by('-attempts', '-created_at').first()
                    item_data["latest_submission"] = (
                        ChecklistItemSubmissionSerializer(latest_sub, context={"request": self.request}).data
                        if latest_sub else None
                    )
                    item_data["checklist_info"] = ChecklistSerializer(checklist).data
                    out.append(item_data)
                return out

            if rework_items.exists():
                serialized_rework = serialize_items_with_submission(rework_items)
                grouped[room_id]["assigned_to_me"].extend(serialized_rework)

            if fresh_items.exists():
                serialized_fresh = serialize_items_with_submission(fresh_items)
                grouped[room_id]["available_for_me"].extend(serialized_fresh)

        response_data = [room_data for room_data in grouped.values()
                         if room_data["assigned_to_me"] or room_data["available_for_me"]]

        user_generated_qs = Checklist.objects.filter(
            user_generated_id__isnull=False,
            project_id=project_id,
            room_id__isnull=True
        )
        user_generated_serialized = []
        for checklist in user_generated_qs:
            checklist_data = ChecklistSerializer(checklist).data
            items = ChecklistItem.objects.filter(checklist=checklist)
            checklist_data['items'] = []
            for item in items:
                item_data = ChecklistItemSerializer(item).data
                options = ChecklistItemOption.objects.filter(checklist_item=item.id)
                item_data['options'] = ChecklistItemOptionSerializer(options, many=True).data
                submissions = ChecklistItemSubmission.objects.filter(checklist_item=item.id)
                item_data['submissions'] = ChecklistItemSubmissionSerializer(
                    submissions, many=True, context={"request": self.request}
                ).data
                checklist_data['items'].append(item_data)
            user_generated_serialized.append(checklist_data)

        response = paginator.get_paginated_response(response_data)
        response.data['user_generated_checklists'] = user_generated_serialized
        return response
   


class CreateChecklistforUnit(APIView):
    permission_classes = [permissions.IsAuthenticated]
    UNIT_DETAILS_URL = f'https://{local}/projects/units-by-id/'

    def post(self, request):
        data = request.data
        required_fields = ['name', 'project_id', 'created_by_id']
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return Response({"error": f"Missing required fields: {', '.join(missing_fields)}"}, status=400)

        user = request.user
        checklist_fields = {
            'name': data.get('name'),
            'description': data.get('description'),
            'status': data.get('status', 'not_started'),
            'project_id': data.get('project_id'),
            'purpose_id': data.get('purpose_id'),
            'phase_id': data.get('phase_id'),
            'stage_id': data.get('stage_id'),
            'category': data.get('category'),
            'category_level1': data.get('category_level1'),
            'category_level2': data.get('category_level2'),
            'category_level3': data.get('category_level3'),
            'category_level4': data.get('category_level4'),
            'category_level5': data.get('category_level5'),
            'category_level6': data.get('category_level6'),
            'remarks': data.get('remarks'),
            'created_by_id': user.id,
        }

        unit_ids = []
        project_data = {}

        # Detect which unit_ids to process (flat, list, or hierarchy filter)
        if data.get('flat_id'):
            unit_ids = [data['flat_id']]
        elif data.get('unit_ids'):
            unit_ids = data['unit_ids']
        elif any([
            data.get('zone_id'),
            data.get('building_id'),
            data.get('project_id'),
            data.get('level_id'),
            data.get('floor_id'),
            data.get('subzone_id')
        ]):
            params = {}
            if data.get("zone_id"):
                params["zone_id"] = data.get("zone_id")
            if data.get("building_id"):
                params["building_id"] = data.get("building_id")
            if data.get("project_id"):
                params["project_id"] = data.get("project_id")
            if data.get("level_id"):
                params["level_id"] = data.get("level_id")
            if data.get("floor_id"):
                params["level_id"] = data.get("floor_id")  # possible alias!
            if data.get("subzone_id"):
                params["subzone_id"] = data.get("subzone_id")

            try:
                headers = {}
                auth_header = request.headers.get("Authorization")
                if auth_header:
                    headers["Authorization"] = auth_header

                resp = requests.get(self.UNIT_DETAILS_URL, params=params, headers=headers)
                resp.raise_for_status()
                resp_data = resp.json()
                unit_ids = [unit["unit_id"] for unit in resp_data.get("units", [])]
                project_data = {str(unit["unit_id"]): unit for unit in resp_data.get("units", [])}
            except Exception as e:
                return Response({"error": f"Failed to fetch units: {str(e)}"}, status=500)
        else:
            return Response({"error": "No flat_id/unit_ids/zone/building/project/level/subzone provided."}, status=400)

        if not unit_ids:
            return Response({"error": "No unit ids found/provided."}, status=404)

        selected_room_ids = data.get('rooms', [])  # This can be empty list
        created_checklists = []

        for unit_id in unit_ids:
            # This flat_info (unit details) is required for hierarchy/room lookup
            flat_info = project_data.get(str(unit_id)) if project_data else None
            if not flat_info and not data.get('flat_id'):
                continue  # skip if not found in project_data (except direct flat_id create)

            allowed_room_ids = set()
            if flat_info and flat_info.get("rooms"):
                allowed_room_ids = set([r["id"] for r in flat_info["rooms"]])

            # Get all hierarchy info from flat_info if present, else None
            building_id = flat_info.get("building_id") if flat_info else None
            zone_id = flat_info.get("zone_id") if flat_info else None
            subzone_id = flat_info.get("subzone_id") if flat_info else None
            level_id = flat_info.get("level_id") if flat_info else None
            project_id = flat_info.get("project_id") if flat_info else data.get('project_id')

            # Determine target_room_ids:
            if selected_room_ids:
                # Filter to only valid rooms for this flat
                target_room_ids = [int(rid) for rid in selected_room_ids if (not allowed_room_ids or int(rid) in allowed_room_ids)]
            elif allowed_room_ids:
                # All rooms for this unit
                target_room_ids = list(allowed_room_ids)
            else:
                # No rooms at all: create checklist for flat without room
                target_room_ids = [None]

            for room_id in target_room_ids:
                try:
                    with transaction.atomic():
                        fields = checklist_fields.copy()
                        fields['flat_id'] = unit_id
                        fields['room_id'] = room_id
                        fields['building_id'] = building_id
                        fields['zone_id'] = zone_id
                        fields['subzone_id'] = subzone_id
                        fields['level_id'] = level_id
                        fields['project_id'] = project_id

                        checklist_instance = Checklist.objects.create(**fields)

                        for item in data.get('items', []):
                            checklist_item = ChecklistItem.objects.create(
                                checklist=checklist_instance,
                                title=item.get('title'),
                                description=item.get('description'),
                                status=item.get('status', 'not_started'),
                                ignore_now=item.get('ignore_now', False),
                                photo_required=item.get('photo_required', False)
                            )

                            for option in item.get('options', []):
                                ChecklistItemOption.objects.create(
                                    checklist_item=checklist_item,
                                    name=option.get('name'),
                                    choice=option.get('choice', 'P')
                                )

                        created_checklists.append(checklist_instance.id)
                except Exception as e:
                    return Response({"error": f"Failed to create checklist for unit {unit_id}, room {room_id}: {str(e)}"}, status=500)

        return Response({"message": "Checklists created successfully.", "checklist_ids": created_checklists}, status=201)


class ChecklistRoleAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.query_params.get("user_id") or request.user.id
        project_id = request.query_params.get("project_id")
        role = request.query_params.get("role")

        if not user_id or not project_id or not role:
            return Response(
                {"detail": "user_id, project_id, and role are required"}, status=400
            )

        try:
            role_upper = role.upper()
            if role_upper == "SUPERVISOR":
                data = get_supervisor_analytics(user_id, project_id)
            elif role_upper == "MAKER":
                data = get_maker_analytics(user_id, project_id)
            elif role_upper == "CHECKER":
                data = get_checker_analytics(user_id, project_id)
            elif role_upper == "INTIALIZER":
                data = get_intializer_analytics(user_id, project_id, request)
            else:
                return Response(
                    {"detail": f"Role '{role}' not supported"}, status=400
                )
        except Exception as e:
            print("Exception in ChecklistRoleAnalyticsAPIView:", str(e))
            traceback.print_exc()
            return Response(
                {"detail": "Internal Server Error", "error": str(e)},
                status=500
            )

        return Response(data, status=200)


def get_intializer_analytics(user_id, project_id, request):
    USER_SERVICE_URL = "https://konstruct.world/users/user-access/"
#  USER_SERVICE_URL = "https://{local}:8000/api/user-access/"
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header:
        token = auth_header.split(
            " ")[1] if " " in auth_header else auth_header
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(
            USER_SERVICE_URL,
            params={"user_id": user_id, "project_id": project_id},
            timeout=5,
            headers=headers
        )
        if resp.status_code != 200:
            return {"detail": "Could not fetch user access"}
        accesses = resp.json()
    except Exception as e:
        return {"detail": "User service error", "error": str(e)}

    q = Q()
    for access in accesses:
        cat_q = Q()
        if access.get('category'):
            cat_q &= Q(category=access['category'])
            for i in range(1, 7):
                key = f'CategoryLevel{i}'
                if access.get(key) is not None:
                    cat_q &= Q(**{f'category_level{i}': access[key]})
                else:
                    break

        loc_q = Q()
        if access.get('flat_id'):
            loc_q &= Q(flat_id=access['flat_id'])
        elif access.get('zone_id'):
            loc_q &= Q(zone_id=access['zone_id'])
        elif access.get('building_id'):
            loc_q &= Q(building_id=access['building_id'])

        q |= (cat_q & loc_q)

    checklists = Checklist.objects.filter(project_id=project_id)
    if q:
        checklists = checklists.filter(q).distinct()
    else:
        checklists = Checklist.objects.none()

    # Count how many can be initialized (status='not_started')
    not_started_count = checklists.filter(status='not_started').count()
    total_accessible = checklists.count()

    return {
        "not_started_count": not_started_count,
        "total_accessible_checklists": total_accessible,
    }


def get_supervisor_analytics(user_id, project_id):
    latest_submission_subq = ChecklistItemSubmission.objects.filter(
        checklist_item=OuterRef('pk')
    ).order_by('-attempts', '-created_at').values('id')[:1]

    base_items = ChecklistItem.objects.filter(
        checklist__project_id=project_id,
        status="pending_for_supervisor"
    ).annotate(
        latest_submission_id=Subquery(latest_submission_subq)
    )

    assigned_to_me_count = base_items.filter(
        submissions__id=F('latest_submission_id'),
        submissions__supervisor_id=user_id,
        submissions__status="pending_supervisor"
    ).distinct().count()

    available_for_me_count = base_items.filter(
        submissions__id=F('latest_submission_id'),
        submissions__supervisor_id__isnull=True,
        submissions__status="pending_supervisor"
    ).distinct().count()
    return {
        "pending_for_me_count": assigned_to_me_count,
        "available_for_me_count": available_for_me_count,
    }


def get_maker_analytics(user_id, project_id):
    from .models import ChecklistItem, ChecklistItemSubmission

    latest_submission_subq = ChecklistItemSubmission.objects.filter(
        checklist_item=OuterRef('pk')
    ).order_by('-attempts', '-created_at').values('id')[:1]

    base_items = ChecklistItem.objects.filter(
        checklist__project_id=project_id,
        status="pending_for_maker"
    ).annotate(
        latest_submission_id=Subquery(latest_submission_subq)
    )

    assigned_to_me_count = base_items.filter(
        submissions__id=F('latest_submission_id'),
        submissions__maker_id=user_id,
        submissions__status="created"
    ).distinct().count()

    available_for_me_count = base_items.filter(
        submissions__id=F('latest_submission_id'),
        submissions__maker_id__isnull=True,
        submissions__status="created"
    ).distinct().count()

    return {
        "assigned_to_me_count": assigned_to_me_count,
        "available_for_me_count": available_for_me_count,
    }


def get_checker_analytics(user_id, project_id):
    from .models import Checklist, ChecklistItem

    assigned_item_exists = ChecklistItem.objects.filter(
        checklist=OuterRef('pk'),
        status="pending_for_inspector",
        submissions__checker_id=user_id,
        submissions__status="pending_checker"
    )
    available_item_exists = ChecklistItem.objects.filter(
        checklist=OuterRef('pk'),
        status="pending_for_inspector",
        submissions__checker_id__isnull=True
    )

    base_qs = Checklist.objects.filter(project_id=project_id)
    assigned_to_me_count = base_qs.annotate(
        has_assigned=Exists(assigned_item_exists)
    ).filter(has_assigned=True).count()

    available_for_me_count = base_qs.annotate(
        has_available=Exists(available_item_exists)
    ).filter(has_available=True).count()

    return {
        "assigned_to_me_count": assigned_to_me_count,
        "available_for_me_count": available_for_me_count,
    }


class ChecklistByCreatorAndProjectAPIView(APIView):
    """
    Get all checklists filtered by created_by_id and/or project_id.
    GET params: ?created_by_id=123&project_id=99
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        created_by_id = request.query_params.get("created_by_id")
        project_id = request.query_params.get("project_id")

        qs = Checklist.objects.all()
        if created_by_id:
            qs = qs.filter(created_by_id=created_by_id)
        if project_id:
            qs = qs.filter(project_id=project_id)

        serializer = ChecklistSerializer(qs, many=True)
        return Response(serializer.data, status=200)

class CHecklist_View_FOr_INtializer(APIView):
    permission_classes = [IsAuthenticated]
    # USER_SERVICE_URL = "https://konstruct.world/users/user-access/"
    # ROOM_SERVICE_URL = "https://konstruct.world/project/rooms/"
    USER_SERVICE_URL = f"http://{local}:8000/api/user-access/"
    ROOM_SERVICE_URL = f"http://{local}:8001/api/rooms/"
    def get(self, request):
        user_id = request.user.id
        project_id = request.query_params.get("project_id")
        tower_id = request.query_params.get("tower_id")
        flat_id = request.query_params.get("flat_id")
        zone_id = request.query_params.get("zone_id")

        if not user_id or not project_id:
            return Response(
                {"detail": "user_id and project_id required."}, status=400)

        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(
                " ")[1] if " " in auth_header else auth_header

        headers = {"Authorization": f"Bearer {token}"} if token else {}

        try:
            resp = requests.get(
                self.USER_SERVICE_URL,
                params={"user_id": user_id, "project_id": project_id},
                timeout=5,
                headers=headers
            )
            if resp.status_code != 200:
                return Response(
                    {"detail": "Could not fetch user access"}, status=400)
            accesses = resp.json()
        except Exception as e:
            return Response({"detail": "User service error",
                            "error": str(e)}, status=400)

        # Step 1: Filter by location
        checklist_filter = Q(project_id=project_id)

        if flat_id:
            checklist_filter &= Q(flat_id=flat_id)
        elif zone_id:
            checklist_filter &= Q(
                zone_id=zone_id,
                flat_id__isnull=True,
                room_id__isnull=True)
        elif tower_id:
            checklist_filter &= Q(
                building_id=tower_id,
                zone_id__isnull=True,
                flat_id__isnull=True,
                room_id__isnull=True)
        else:
            checklist_filter &= Q(
                building_id__isnull=True,
                zone_id__isnull=True,
                flat_id__isnull=True,
                room_id__isnull=True)

        checklists = Checklist.objects.filter(checklist_filter)

        category_filter = Q()
        for access in accesses:
            if access.get('category'):
                category_filter |= self.get_branch_q(access)

        if category_filter:
            checklists = checklists.filter(category_filter).distinct()
        else:
            checklists = Checklist.objects.none()

        # Step 3: Room enrichment
        room_ids = checklists.values_list(
            'room_id', flat=True).distinct().exclude(
            room_id__isnull=True)
        room_details = {}

        for room_id in room_ids:
            try:
                room_resp = requests.get(
                    f"{self.ROOM_SERVICE_URL}{room_id}",
                    headers=headers,
                    timeout=5)
                if room_resp.status_code == 200:
                    room_details[room_id] = room_resp.json()
            except Exception:
                continue

        serialized_checklists = ChecklistSerializer(checklists, many=True).data

        grouped = defaultdict(
            lambda: {
                "room_id": None,
                "count": 0,
                "checklists": []})

        for checklist in serialized_checklists:
            room_id = checklist.get('room_id')

            if room_id and room_id in room_details:
                checklist['room_details'] = room_details[room_id]

            grouped[room_id]["room_id"] = room_id
            grouped[room_id]["checklists"].append(checklist)
            grouped[room_id]["count"] += 1

        response_data = list(grouped.values())
        return Response(response_data, status=200)



class IntializeChechklistView(APIView):
    def post(self, request, checklist_id):
        try:
            checklist = Checklist.objects.get(
                id=checklist_id, status="not_started")
        except Checklist.DoesNotExist:
            return Response(
                {"error": "Checklist not found or All ready Offered."},
                status=status.HTTP_404_NOT_FOUND,
            )

        checklist.status = "in_progress"
        checklist.save()

        items_qs = checklist.items.filter(status="not_started")
        updated_count = items_qs.update(status="pending_for_inspector")

        return Response(
            {
                "checklist": ChecklistSerializer(checklist).data,
                "items_updated_count": updated_count,
            },
            status=status.HTTP_200_OK,
        )

# Newwww
class CheckerInprogressAccessibleChecklists(APIView):
    permission_classes = [IsAuthenticated]
    # USER_SERVICE_URL = "https://konstruct.world/users/user-access/"
    USER_SERVICE_URL = "https://{local}:8000/api/user-access/"

    def get(self, request):
        user_id = request.user.id
        project_id = request.query_params.get("project_id")
        tower_id = request.query_params.get("tower_id")
        zone_id = request.query_params.get("zone_id")
        flat_id = request.query_params.get("flat_id")

        if not user_id or not project_id:
            return Response(
                {"detail": "user_id and project_id required."}, status=400)

        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(
                " ")[1] if " " in auth_header else auth_header
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        # Fetch user access
        try:
            resp = requests.get(
                self.USER_SERVICE_URL,
                params={"user_id": user_id, "project_id": project_id},
                timeout=5,
                headers=headers
            )
            if resp.status_code != 200:
                return Response(
                    {"detail": "Could not fetch user access"}, status=400)
            accesses = resp.json()
        except Exception as e:
            return Response({"detail": "User service error",
                            "error": str(e)}, status=400)

        # Build location + category access filter
        q = Q()
        for access in accesses:
            cat_q = Q()
            if access.get('category'):
                cat_q &= Q(category=access['category'])
                for i in range(1, 7):
                    key = f'CategoryLevel{i}'
                    if access.get(key) is not None:
                        cat_q &= Q(**{f'category_level{i}': access[key]})
                    else:
                        break

#            loc_q = Q()
#            if access.get('flat_id'):
#                loc_q &= Q(flat_id=access['flat_id'])
#            elif access.get('zone_id'):
#                loc_q &= Q(zone_id=access['zone_id'], flat_id__isnull=True, room_id__isnull=True)
#            elif access.get('building_id'):
#                loc_q &= Q(building_id=access['building_id'], zone_id__isnull=True, flat_id__isnull=True, room_id__isnull=True)
#            elif access.get('project_id'):
#                loc_q &= Q(building_id__isnull=True, zone_id__isnull=True, flat_id__isnull=True, room_id__isnull=True)

            q |= (cat_q)

        # Apply user filter input (flat_id > zone_id > tower_id > project only)
        checklist_filter = Q(project_id=project_id)
        if flat_id:
            checklist_filter &= Q(flat_id=flat_id)
        elif zone_id:
            checklist_filter &= Q(
                zone_id=zone_id,
                flat_id__isnull=True,
                room_id__isnull=True)
        elif tower_id:
            checklist_filter &= Q(
                building_id=tower_id,
                zone_id__isnull=True,
                flat_id__isnull=True,
                room_id__isnull=True)
        else:
            checklist_filter &= Q(
                building_id__isnull=True,
                zone_id__isnull=True,
                flat_id__isnull=True,
                room_id__isnull=True)

        base_qs = Checklist.objects.filter(checklist_filter)
        if q:
            base_qs = base_qs.filter(q).distinct()
        else:
            base_qs = Checklist.objects.none()

        # Annotate assignment state
        assigned_item_exists = ChecklistItem.objects.filter(
            checklist=OuterRef('pk'),
            status="pending_for_inspector",
            submissions__checker_id=user_id,
            submissions__status="pending_checker"
        )

        available_item_exists = ChecklistItem.objects.filter(
            checklist=OuterRef('pk'),
            status="pending_for_inspector",
            submissions__checker_id__isnull=True
        )

        assigned_to_me = base_qs.annotate(
            has_assigned=Exists(assigned_item_exists)
        ).filter(has_assigned=True)

        available_for_me = base_qs.annotate(
            has_available=Exists(available_item_exists)
        ).filter(has_available=True)

        response = {
            "assigned_to_me": ChecklistWithItemsAndSubmissionsSerializer(
                assigned_to_me,
                many=True).data,
            "available_for_me": ChecklistWithItemsAndSubmissionsSerializer(
                available_for_me,
                many=True).data}

        return Response(response, status=200)


class ChecklistItemsByChecklistAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, checklist_id):
        items = ChecklistItem.objects.filter(checklist_id=checklist_id)
        serializer = ChecklistItemSerializer(items, many=True)
        print(serializer.data, 'this is data')
        return Response(serializer.data, status=status.HTTP_200_OK)



class VerifyChecklistItemForCheckerNSupervisorAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_true_level(self, project_id):
        TRANSFER_RULE_API = f"https://{local}/projects/transfer-rules/"
        try:
            resp = requests.get(TRANSFER_RULE_API, params={"project_id": project_id})
            if resp.status_code == 200 and resp.json():
                return resp.json()[0].get("true_level")
        except Exception as e:
            print("TransferRule error:", e)
        return None

    def patch(self, request):
        checklist_item_id = request.data.get('checklist_item_id')
        role = request.data.get('role')
        option_id = request.data.get('option_id')

        if not checklist_item_id or not role or not option_id:
            return Response({"detail": "checklist_item_id, role, and option_id are required."}, status=400)

        try:
            item = ChecklistItem.objects.get(id=checklist_item_id)
        except ChecklistItem.DoesNotExist:
            return Response({"detail": "ChecklistItem not found."}, status=404)

        try:
            option = ChecklistItemOption.objects.get(id=option_id)
        except ChecklistItemOption.DoesNotExist:
            return Response({"detail": "ChecklistItemOption not found."}, status=404)

        checklist = item.checklist

        # === CHECKER LOGIC ===
        if role.lower() == "checker":
            check_remark = request.data.get('check_remark', '')
            check_photo = request.FILES.get('check_photo', None)
            submission = item.submissions.filter(
                checker_id=request.user.id,
                status="pending_checker"
            ).order_by('-attempts', '-created_at').first()

            if not submission:
                max_attempts = item.submissions.aggregate(
                    max_attempts=models.Max('attempts'))['max_attempts'] or 0
                submission = ChecklistItemSubmission.objects.create(
                    checklist_item=item,
                    checker_id=request.user.id,
                    status="pending_checker",
                    attempts=max_attempts + 1
                )
                print('newwww created')

            # Update checker fields only!
            submission.checker_remarks = check_remark
            submission.checked_at = timezone.now()
            if check_photo:
                submission.inspector_photo = check_photo

            if option.choice == "P":
                submission.status = "completed"
                item.status = "completed"
                submission.save(update_fields=["checker_remarks", "checked_at", "inspector_photo", "status"])
                item.save(update_fields=["status"])
                # Mark checklist as completed if all items done
                if not checklist.items.exclude(status="completed").exists():
                    checklist.status = "completed"
                    checklist.save(update_fields=["status"])
                return Response({
                    "detail": "Item completed.",
                    "item_id": item.id,
                    "item_status": item.status,
                    "submission_id": submission.id,
                    "submission_status": submission.status,
                    "checklist_status": checklist.status
                }, status=200)
            elif option.choice == "N":
                submission.status = "rejected_by_checker"
                submission.save(update_fields=["checker_remarks", "checked_at", "inspector_photo", "status"])
                item.status = "pending_for_maker"
                item.save(update_fields=["status"])
                # New submission for maker
                max_attempts = item.submissions.aggregate(
                    max_attempts=models.Max('attempts'))['max_attempts'] or 0
                ChecklistItemSubmission.objects.create(
                    checklist_item=item,
                    maker_id=submission.maker_id if submission.maker_id else None,
                    checker_id=submission.checker_id,
                    supervisor_id=submission.supervisor_id,
                    attempts=max_attempts + 1,
                    status="created"
                )
                checklist.status = "work_in_progress"
                checklist.save(update_fields=["status"])
                return Response({
                    "detail": "Rejected by checker, sent back to maker.",
                    "item_id": item.id,
                    "item_status": item.status,
                    "checklist_status": checklist.status
                }, status=200)
            else:
                return Response({"detail": "Invalid option value for checker."}, status=400)

        # === SUPERVISOR LOGIC ===
        elif role.lower() == "supervisor":
            supervisor_remark = request.data.get('supervisor_remark', '')
            supervisor_photo = request.FILES.get('supervisor_photo', None)

            submission = item.submissions.filter(
                supervisor_id=request.user.id,
                status="pending_supervisor"
            ).order_by('-attempts', '-created_at').first()

            if not submission:
                submission = item.submissions.filter(
                    checker_id__isnull=False,
                    maker_id__isnull=False,
                    status="pending_supervisor",
                    supervisor_id__isnull=True
                ).order_by('-attempts', '-created_at').first()
            if not submission:
                return Response({
                    "detail": (
                        "No submission found for supervisor action. "
                        "This usually means the item hasn't been checked by checker or submitted by maker. "
                        "Please check workflow: Maker must submit, Checker must verify before Supervisor can act."
                    ),
                    "item_id": item.id,
                    "item_status": item.status
                }, status=400)

            # Assign supervisor_id if not set
            if not submission.supervisor_id:
                submission.supervisor_id = request.user.id

            # Update supervisor fields only!
            submission.supervisor_remarks = supervisor_remark
            submission.supervised_at = timezone.now()
            if supervisor_photo:
                submission.reviewer_photo = supervisor_photo

            true_level = self.get_true_level(checklist.project_id)
            if true_level == "flat_level":
                checklists_in_group = Checklist.objects.filter(flat_id=checklist.flat_id, project_id=checklist.project_id)
            elif true_level == "room_level":
                checklists_in_group = Checklist.objects.filter(room_id=checklist.room_id, project_id=checklist.project_id)
            elif true_level == "Zone_level":
                checklists_in_group = Checklist.objects.filter(building_id=checklist.building_id, project_id=checklist.project_id)
            elif true_level == "level_id":
                checklists_in_group = Checklist.objects.filter(level_id=checklist.level_id, project_id=checklist.project_id)
            elif true_level == "checklist_level":
                checklists_in_group = Checklist.objects.filter(id=checklist.id)
            else:
                checklists_in_group = Checklist.objects.filter(id=checklist.id)

            # === Supervisor Approved ===
            if option.choice == "P":
                item.status = "tetmpory_inspctor"
                submission.status = "pending_checker"
                item.save(update_fields=["status"])
                submission.save(update_fields=[
                    "supervisor_remarks", "supervised_at", "reviewer_photo", "status", "supervisor_id"
                ])

                # Re-fetch group items AFTER current item update
                group_items = ChecklistItem.objects.filter(checklist__in=checklists_in_group)

                # 1️⃣ Promote temp inspector -> pending_for_inspector
                all_ready = all(
                    it.status in ["completed", "tetmpory_inspctor"] for it in group_items
                )
                if all_ready:
                    ChecklistItem.objects.filter(
                        checklist__in=checklists_in_group,
                        status="tetmpory_inspctor"
                    ).update(status="pending_for_inspector")

                # 2️⃣ Promote temp maker -> pending_for_maker
                all_ready = all(
                    it.status in ["completed", "tetmpory_Maker", "tetmpory_inspctor"]
                    for it in group_items
                )
                if all_ready:
                    ChecklistItem.objects.filter(
                        checklist__in=checklists_in_group,
                        status="tetmpory_Maker"
                    ).update(status="pending_for_maker")

                return Response({
                    "detail": "Sent to inspector.",
                    "item_id": item.id,
                    "item_status": item.status,
                    "submission_id": submission.id,
                    "submission_status": submission.status,
                }, status=200)

            # === Supervisor Rejected ===
            elif option.choice == "N":
                item.status = "tetmpory_Maker"
                submission.status = "rejected_by_supervisor"
                item.save(update_fields=["status"])
                submission.save(update_fields=[
                    "supervisor_remarks", "supervised_at", "reviewer_photo", "status", "supervisor_id"
                ])

                # Re-fetch group items AFTER current item update
                group_items = ChecklistItem.objects.filter(checklist__in=checklists_in_group)

                max_attempts = item.submissions.aggregate(
                    max_attempts=models.Max('attempts')
                )['max_attempts'] or 0

                ChecklistItemSubmission.objects.create(
                    checklist_item=item,
                    maker_id=submission.maker_id,
                    checker_id=submission.checker_id,
                    supervisor_id=submission.supervisor_id,
                    attempts=max_attempts + 1,
                    status="created"
                )
                checklist.status = "work_in_progress"
                checklist.save(update_fields=["status"])

                # 1️⃣ Promote temp inspector -> pending_for_inspector
                all_ready = all(
                    it.status in ["completed", "tetmpory_inspctor"] for it in group_items
                )
                if all_ready:
                    ChecklistItem.objects.filter(
                        checklist__in=checklists_in_group,
                        status="tetmpory_inspctor"
                    ).update(status="pending_for_inspector")

                # 2️⃣ Promote temp maker -> pending_for_maker
                all_ready = all(
                    it.status in ["completed", "tetmpory_Maker", "tetmpory_inspctor"]
                    for it in group_items
                )
                if all_ready:
                    ChecklistItem.objects.filter(
                        checklist__in=checklists_in_group,
                        status="tetmpory_Maker"
                    ).update(status="pending_for_maker")

                return Response({
                    "detail": "Rejected by supervisor, sent back to maker.",
                    "item_id": item.id,
                    "item_status": item.status,
                    "checklist_status": checklist.status
                }, status=200)
            else:
                return Response({"detail": "Invalid option value for supervisor."}, status=400)

        else:
            return Response({"detail": "Invalid role. Must be 'checker' or 'supervisor'."}, status=400)


class PendingForMakerItemsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    # USER_SERVICE_URL = "https://konstruct.world/users/user-access/"
    USER_SERVICE_URL = "https://{local}:8000/api/user-access/"
    def get(self, request):
        user_id = request.user.id
        project_id = request.query_params.get("project_id")
        flat_id = request.query_params.get("flat_id")
        zone_id = request.query_params.get("zone_id")
        tower_id = request.query_params.get("tower_id")

        if not user_id or not project_id:
            return Response(
                {"detail": "user_id and project_id required."}, status=400)

        # Auth headers
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            parts = auth_header.strip().split(" ")
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        # Fetch access from user service
        try:
            resp = requests.get(
                self.USER_SERVICE_URL,
                params={"user_id": user_id, "project_id": project_id},
                timeout=5,
                headers=headers
            )
            if resp.status_code != 200:
                return Response(
                    {"detail": "Could not fetch user access"}, status=400)
            accesses = resp.json()
        except Exception as e:
            return Response({"detail": "User service error",
                            "error": str(e)}, status=400)

        # Build category/location filter Q
        q = Q()
        for access in accesses:
            cat_q = Q()
            if access.get('category'):
                cat_q &= Q(category=access['category'])
                for i in range(1, 7):
                    key = f'CategoryLevel{i}'
                    if access.get(key) is not None:
                        cat_q &= Q(**{f'category_level{i}': access[key]})
                    else:
                        break

            loc_q = Q()
            if access.get('flat_id'):
                loc_q &= Q(flat_id=access['flat_id'])
            elif access.get('zone_id'):
                loc_q &= Q(
                    zone_id=access['zone_id'],
                    flat_id__isnull=True,
                    room_id__isnull=True)
            elif access.get('building_id'):
                loc_q &= Q(
                    building_id=access['building_id'],
                    zone_id__isnull=True,
                    flat_id__isnull=True,
                    room_id__isnull=True)
            elif access.get('project_id'):
                loc_q &= Q(
                    building_id__isnull=True,
                    zone_id__isnull=True,
                    flat_id__isnull=True,
                    room_id__isnull=True)

            q |= (cat_q & loc_q)

        # Direct checklist filter from query params (UI)
        checklist_filter = Q(project_id=project_id)
        if flat_id:
            checklist_filter &= Q(flat_id=flat_id)
        elif zone_id:
            checklist_filter &= Q(
                zone_id=zone_id,
                flat_id__isnull=True,
                room_id__isnull=True)
        elif tower_id:
            checklist_filter &= Q(
                building_id=tower_id,
                zone_id__isnull=True,
                flat_id__isnull=True,
                room_id__isnull=True)
        else:
            checklist_filter &= Q(
                building_id__isnull=True,
                zone_id__isnull=True,
                flat_id__isnull=True,
                room_id__isnull=True)

        checklist_qs = Checklist.objects.filter(checklist_filter)
        if q:
            checklist_qs = checklist_qs.filter(q).distinct()
        else:
            checklist_qs = Checklist.objects.none()

        # Get latest submission per item
        latest_submission_subq = ChecklistItemSubmission.objects.filter(
            checklist_item=OuterRef('pk')
        ).order_by('-attempts', '-created_at').values('id')[:1]

        base_items = ChecklistItem.objects.filter(
            checklist__in=checklist_qs,
            status="pending_for_maker"
        ).annotate(
            latest_submission_id=Subquery(latest_submission_subq)
        )

        # Assigned to current maker
        rework_items = base_items.filter(
            submissions__id=F('latest_submission_id'),
            submissions__maker_id=user_id,
            submissions__status="created"
        ).distinct()

        # Not yet assigned to any maker
        fresh_items = base_items.filter(
            submissions__id=F('latest_submission_id'),
            submissions__maker_id__isnull=True,
            submissions__status="created"
        ).distinct()

        # Serialize items
        def serialize_items_with_submission(qs):
            out = []
            for item in qs:
                item_data = ChecklistItemSerializer(item).data
                latest_sub = ChecklistItemSubmission.objects.filter(
                    checklist_item=item
                ).order_by('-attempts', '-created_at').first()

                item_data["latest_submission"] = (
                    ChecklistItemSubmissionSerializer(latest_sub, context={"request": self.request}).data
                    if latest_sub else None
                )
                out.append(item_data)
            return out

        response = {
            "assigned_to_me": serialize_items_with_submission(rework_items),
            "available_for_me": serialize_items_with_submission(fresh_items),
        }

        return Response(response, status=200)


class MAker_DOne_view(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        checklist_item_id = request.data.get("checklist_item_id")
        maker_remark = request.data.get("maker_remark", "")
        maker_media = request.FILES.get("maker_media", None)

        if not checklist_item_id:
            return Response({"detail": "checklist_item_id required."}, status=400)

        # 1. Get item with status pending_for_maker
        try:
            item = ChecklistItem.objects.get(
                id=checklist_item_id, status="pending_for_maker"
            )
        except ChecklistItem.DoesNotExist:
            return Response({
                "detail": "ChecklistItem not found or not pending for maker."
            }, status=404)

        # 2. Find the latest "created" submission for this item assigned to this maker
        latest_submission = (
            ChecklistItemSubmission.objects
            .filter(checklist_item=item, status="created")
            .order_by('-attempts', '-created_at')
            .first()
        )

        if not latest_submission:
            return Response({
                "detail": "No matching submission found for rework."
            }, status=404)

        # Set maker ID if not already set (for backfilled submissions)
        if not latest_submission.maker_id:
            latest_submission.maker_id = request.user.id

        # 3. Update submission with all maker fields
        latest_submission.status = "pending_supervisor"
        latest_submission.maker_remarks = maker_remark
        latest_submission.maker_at = timezone.now()
        if maker_media:
            latest_submission.maker_media = maker_media
        latest_submission.save(update_fields=["status", "maker_id", "maker_remarks", "maker_media", "maker_at"])

        # 4. Update item status
        item.status = "pending_for_supervisor"
        item.save(update_fields=["status"])

        # 5. Respond
        item_data = ChecklistItemSerializer(item).data
        submission_data = {
            "id": latest_submission.id,
            "status": latest_submission.status,
            "maker_remarks": latest_submission.maker_remarks,
            "maker_media": latest_submission.maker_media.url if latest_submission.maker_media else None,
            "maker_at": latest_submission.maker_at,
            "checker_id": latest_submission.checker_id,
            "maker_id": latest_submission.maker_id,
            "supervisor_id": latest_submission.supervisor_id,
        }
        return Response({
            "item": item_data,
            "submission": submission_data,
            "detail": "Checklist item marked as done by maker."
        }, status=200)

    def get(self, request):
        user_id = request.user.id
        queryset = ChecklistItemSubmission.objects.filter(
            status="pending_for_maker",
            maker_id=user_id,
        )
        serializer = ChecklistItemSubmissionSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)


class PendingForSupervisorItemsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    # USER_SERVICE_URL = "https://konstruct.world/users/user-access/"
    USER_SERVICE_URL = "https://{local}:8000/api/user-access/"
    def get(self, request):
        user_id = request.user.id
        project_id = request.query_params.get("project_id")
        flat_id = request.query_params.get("flat_id")
        zone_id = request.query_params.get("zone_id")
        tower_id = request.query_params.get("tower_id")

        if not user_id or not project_id:
            return Response(
                {"detail": "user_id and project_id required."}, status=400)

        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(
                " ")[1] if " " in auth_header else auth_header
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        # --- Fetch user access
        try:
            resp = requests.get(
                self.USER_SERVICE_URL,
                params={"user_id": user_id, "project_id": project_id},
                timeout=5,
                headers=headers
            )
            if resp.status_code != 200:
                return Response(
                    {"detail": "Could not fetch user access"}, status=400)
            accesses = resp.json()
        except Exception as e:
            return Response({"detail": "User service error",
                            "error": str(e)}, status=400)

        # --- Build Q filter based on user access
        q = Q()
        for access in accesses:
            cat_q = Q()
            if access.get("category"):
                cat_q &= Q(category=access["category"])
                for i in range(1, 7):
                    key = f"CategoryLevel{i}"
                    if access.get(key) is not None:
                        cat_q &= Q(**{f"category_level{i}": access[key]})
                    else:
                        break

            loc_q = Q()
            if access.get("flat_id"):
                loc_q &= Q(flat_id=access["flat_id"])
            elif access.get("zone_id"):
                loc_q &= Q(
                    zone_id=access["zone_id"],
                    flat_id__isnull=True,
                    room_id__isnull=True)
            elif access.get("building_id"):
                loc_q &= Q(
                    building_id=access["building_id"],
                    zone_id__isnull=True,
                    flat_id__isnull=True,
                    room_id__isnull=True)
            elif access.get("project_id"):
                loc_q &= Q(
                    building_id__isnull=True,
                    zone_id__isnull=True,
                    flat_id__isnull=True,
                    room_id__isnull=True)

            q |= (cat_q & loc_q)

        # --- User-applied filtering (UI dropdowns)
        checklist_filter = Q(project_id=project_id)
        if flat_id:
            checklist_filter &= Q(flat_id=flat_id)
        elif zone_id:
            checklist_filter &= Q(
                zone_id=zone_id,
                flat_id__isnull=True,
                room_id__isnull=True)
        elif tower_id:
            checklist_filter &= Q(
                building_id=tower_id,
                zone_id__isnull=True,
                flat_id__isnull=True,
                room_id__isnull=True)
        else:
            checklist_filter &= Q(
                building_id__isnull=True,
                zone_id__isnull=True,
                flat_id__isnull=True,
                room_id__isnull=True)

        checklist_qs = Checklist.objects.filter(checklist_filter)
        if q:
            checklist_qs = checklist_qs.filter(q).distinct()
        else:
            checklist_qs = Checklist.objects.none()

        # --- Subquery to get latest submission
        latest_submission_subq = ChecklistItemSubmission.objects.filter(
            checklist_item=OuterRef("pk")
        ).order_by("-attempts", "-created_at").values("id")[:1]

        base_items = ChecklistItem.objects.filter(
            checklist__in=checklist_qs,
            status="pending_for_supervisor"
        ).annotate(
            latest_submission_id=Subquery(latest_submission_subq)
        )

        # Assigned to supervisor
        assigned_to_me = base_items.filter(
            submissions__id=F("latest_submission_id"),
            submissions__supervisor_id=user_id,
            submissions__status="pending_supervisor"
        ).distinct()

        # Available for supervisor
        available_for_me = base_items.filter(
            submissions__id=F("latest_submission_id"),
            submissions__supervisor_id__isnull=True,
            submissions__status="pending_supervisor"
        ).distinct()

        # --- Serialize each item + its latest submission + options
        def serialize_items_with_details(qs):
            out = []
            for item in qs:
                item_data = ChecklistItemSerializer(item).data

                latest_sub = ChecklistItemSubmission.objects.filter(
                    checklist_item=item
                ).order_by("-attempts", "-created_at").first()

                item_data["latest_submission"] = (
                    ChecklistItemSubmissionSerializer(latest_sub).data if latest_sub else None)

                options = ChecklistItemOption.objects.filter(
                    checklist_item=item)
                item_data["options"] = ChecklistItemOptionSerializer(
                    options, many=True).data

                out.append(item_data)
            return out

        response = {
            "pending_for_me": serialize_items_with_details(assigned_to_me),
            "available_for_me": serialize_items_with_details(available_for_me),
        }

        return Response(response, status=200)

class StartChecklistItemAPIView(APIView):
    def post(self, request, item_id):
        try:
            item = ChecklistItem.objects.get(id=item_id, status='NOT_STARTED')
        except ChecklistItem.DoesNotExist:
            return Response(
                {'error': 'ChecklistItem not found or not in NOT_STARTED status.'}, status=404)

        item.status = 'IN_PROGRESS'
        item.save()

        # submission = ChecklistItemSubmission.objects.create(
        #     checklist_item=item,
        #     status='IN_PROGRESS',
        #     user=user_id
        # )

        return Response({
            'item': ChecklistItemSerializer(item).data,
            # 'submission': ChecklistItemSubmissionSerializer(submission).data
        }, status=201)


class ChecklistItemOptionViewSet(viewsets.ModelViewSet):
    queryset = ChecklistItemOption.objects.all()
    serializer_class = ChecklistItemOptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        print("Creating ChecklistItemOption with data:", request.data)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("ChecklistItemOption Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=400)
        self.perform_create(serializer)
        print("ChecklistItemOption created successfully:", serializer.data)
        return Response(serializer.data, status=201)


class ChecklistViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Checklist.objects.all()
    serializer_class = ChecklistSerializer

    def perform_create(self, serializer):
        serializer.save(created_by_id=self.request.user.id)

    def create(self, request, *args, **kwargs):
        not_initialized = request.data.get('not_initialized', False)
        print(
            "Received not_initialized:",
            not_initialized,
            type(not_initialized))
        print("Creating Checklist with data:", request.data)

        for field in ['project_id', 'purpose_id', 'category', 'name']:
            if not request.data.get(field):
                return Response(
                    {field: [f"This field is required."]}, status=400)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Checklist Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=400)

        instance = serializer.save(created_by_id=self.request.user.id)

        if not_initialized in [True, "true", "True", 1, "1"]:
            instance.status = "in_progress"
            instance.save(update_fields=["status"])
            print("Checklist status updated to in_progress")

        out_serializer = self.get_serializer(instance)
        print("Checklist created successfully:", out_serializer.data)
        return Response(out_serializer.data, status=201)

    def get_queryset(self):
        queryset = super().get_queryset()
        project_id = self.request.query_params.get("project")
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset

    @action(detail=False, methods=["get"], url_path="my-checklists")
    def my_checklists(self, request):
        user_id = request.user.id
        checklists = self.get_queryset().filter(created_by_id=user_id)
        serializer = self.get_serializer(checklists, many=True)
        return Response(serializer.data)


class ChecklistItemViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = ChecklistItem.objects.all()
    serializer_class = ChecklistItemSerializer

    def create(self, request, *args, **kwargs):
        print("Creating ChecklistItem with data:", request.data)

        if not request.data.get('checklist'):
            return Response(
                {"checklist": ["This field is required."]}, status=400)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("ChecklistItem Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=400)

        # Get the parent checklist instance
        checklist_id = request.data.get('checklist')
        try:
            checklist = Checklist.objects.get(id=checklist_id)
        except Checklist.DoesNotExist:
            return Response(
                {"checklist": ["Invalid checklist ID."]}, status=400)

        # Save the item first (so you get an instance)
        item = serializer.save()

        # Set status if parent checklist is in_progress
        if checklist.status == "in_progress":
            item.status = "pending_for_inspector"
            item.save(update_fields=["status"])

        out_serializer = self.get_serializer(item)
        print("ChecklistItem created successfully:", out_serializer.data)
        return Response(out_serializer.data, status=201)

    @action(detail=False, methods=['get'])
    def by_checklist(self, request):
        checklist_id = request.query_params.get('checklist_id')
        if not checklist_id:
            return Response({"error": "checklist_id is required"}, status=400)
        items = self.get_queryset().filter(checklist_id=checklist_id)
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        print("PATCH data:", request.data)
        instance = self.get_object()
        print(
            "PATCH for ChecklistItem ID:",
            instance.id,
            "Current status:",
            instance.status)

        serializer = self.get_serializer(
            instance, data=request.data, partial=True)
        if not serializer.is_valid():
            print("PATCH Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=400)

        updated_item = serializer.save()
        print(
            "PATCH successful for ChecklistItem ID:",
            updated_item.id,
            "Updated status:",
            updated_item.status)
        return Response(self.get_serializer(updated_item).data)


class ChecklistItemSubmissionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = ChecklistItemSubmission.objects.all()
    serializer_class = ChecklistItemSubmissionSerializer

    def create(self, request, *args, **kwargs):
        # print("Creating ChecklistItemSubmission with data:", request.data)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print(
                "ChecklistItemSubmission Validation Errors:",
                serializer.errors)
            return Response(serializer.errors, status=400)
        self.perform_create(serializer)
        # print("ChecklistItemSubmission created successfully:", serializer.data)
        return Response(serializer.data, status=201)

    @action(detail=False, methods=['get'])
    def All_Checklist_Record(self, request):
        check_listItem_id = request.query_params.get('check_listItem_id')
        if not check_listItem_id:
            return Response(
                {"error": "checklistItem_id is required"}, status=400)
        items = self.get_queryset().filter(checklist_item_id=check_listItem_id)
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)


class StartChecklistItemAPIView(APIView):
    def post(self, request, user_id, item_id):
        try:
            item = ChecklistItem.objects.get(id=item_id, status='NOT_STARTED')
        except ChecklistItem.DoesNotExist:
            return Response(
                {'error': 'ChecklistItem not found or not in NOT_STARTED status.'}, status=404)

        item.status = 'IN_PROGRESS'
        item.save()

        submission = ChecklistItemSubmission.objects.create(
            checklist_item=item,
            status='IN_PROGRESS',
            user=user_id
        )

        return Response({
            'item': ChecklistItemSerializer(item, context={"request": request}).data,
            'submission': ChecklistItemSubmissionSerializer(submission, context={"request": request}).data
        }, status=201)



class ChecklistItemInProgressByUserView(APIView):
    def get(self, request, user_id):
        submissions = ChecklistItemSubmission.objects.filter(
            status='IN_PROGRESS', user=user_id)
        serializer = ChecklistItemSubmissionSerializer(
            submissions, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChecklistItemCompletedByUserView(APIView):
    def get(self, request, user_id):
        submissions = ChecklistItemSubmission.objects.filter(
            status='COMPLETED', user=user_id)
        serializer = ChecklistItemSubmissionSerializer(
        submissions, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChecklistItemByCategoryStatusView(APIView):
    def get(self, request, cat_or_subcat_id):
        checklist_ids = Checklist.objects.filter(
            status='NOT_STARTED'
        ).filter(
            Q(category=cat_or_subcat_id) | Q(category_level1=cat_or_subcat_id)
        ).values_list('id', flat=True)
        items = ChecklistItem.objects.filter(
            checklist_id__in=checklist_ids, status='NOT_STARTED')
        serializer = ChecklistItemSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AccessibleChecklistsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    # USER_SERVICE_URL = "https://konstruct.world/users/user-access/"
    USER_SERVICE_URL = "https://{local}:8000/api/user-access/"
    def get(self, request):
        user_id = request.user.id
        project_id = request.query_params.get("project_id")

        if not user_id or not project_id:
            return Response(
                {"detail": "user_id and project_id required."}, status=400)

        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(
                " ")[1] if " " in auth_header else auth_header

        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            resp = requests.get(
                self.USER_SERVICE_URL,
                params={"user_id": user_id, "project_id": project_id},
                timeout=5,
                headers=headers
            )
            if resp.status_code != 200:
                return Response(
                    {"detail": "Could not fetch user access"}, status=400)
            accesses = resp.json()
        except Exception as e:
            return Response({"detail": "User service error",
                            "error": str(e)}, status=400)

        q = Q()
        for access in accesses:
            # Category containment logic
            cat_q = Q()
            if access.get('category'):
                cat_q &= Q(category=access['category'])
                for i in range(1, 7):
                    key = f'CategoryLevel{i}'
                    if access.get(key) is not None:
                        cat_q &= Q(**{f'category_level{i}': access[key]})
                    else:
                        break

            # Location containment logic
            loc_q = Q()
            if access.get('flat_id'):
                loc_q &= Q(flat_id=access['flat_id'])
            elif access.get('zone_id'):
                loc_q &= Q(zone_id=access['zone_id'])
            elif access.get('building_id'):
                loc_q &= Q(building_id=access['building_id'])
            # If only project-level access, don't filter further (loc_q empty =
            # all)

            q |= (cat_q & loc_q)

        checklists = Checklist.objects.filter(
            project_id=project_id, status='NOT_STARTED')
        if q:  # Only apply if any access was provided
            checklists = checklists.filter(q).distinct()
        else:
            checklists = Checklist.objects.none()

        serializer = ChecklistSerializer(checklists, many=True)
        print(serializer.data)
        return Response(serializer.data, status=200)


# class MyInProgressChecklistItemSubmissions(APIView):
class AccessibleChecklistsWithPendingCheckerSubmissionsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    # USER_SERVICE_URL = "https://konstruct.world/users/user-access/"
    USER_SERVICE_URL = "https://{local}:8000/api/user-access/"
    def get(self, request):
        user_id = request.user.id
        project_id = request.query_params.get("project_id")

        if not user_id or not project_id:
            return Response(
                {"detail": "user_id and project_id required."}, status=400)

        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(
                " ")[1] if " " in auth_header else auth_header

        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            resp = requests.get(
                self.USER_SERVICE_URL,
                params={"user_id": user_id, "project_id": project_id},
                timeout=5,
                headers=headers
            )
            if resp.status_code != 200:
                return Response(
                    {"detail": "Could not fetch user access"}, status=400)
            accesses = resp.json()
        except Exception as e:
            return Response({"detail": "User service error",
                            "error": str(e)}, status=400)

        q = Q()
        for access in accesses:
            cat_q = Q()
            if access.get('category'):
                cat_q &= Q(category=access['category'])
                for i in range(1, 7):
                    key = f'CategoryLevel{i}'
                    if access.get(key) is not None:
                        cat_q &= Q(**{f'category_level{i}': access[key]})
                    else:
                        break
            loc_q = Q()
            if access.get('flat_id'):
                loc_q &= Q(flat_id=access['flat_id'])
            elif access.get('zone_id'):
                loc_q &= Q(zone_id=access['zone_id'])
            elif access.get('building_id'):
                loc_q &= Q(building_id=access['building_id'])
            q |= (cat_q & loc_q)

        checklists = Checklist.objects.filter(
            project_id=project_id, status='IN_PROGRESS')
        if q:
            checklists = checklists.filter(q).distinct()
        else:
            checklists = Checklist.objects.none()

        serializer = ChecklistWithItemsAndPendingSubmissionsSerializer(
            checklists, many=True)
        data = serializer.data

        # Filter out checklists with no items or where all items have no
        # pending submissions
        filtered_data = []
        for cl in data:
            items_with_pending = [
                item for item in cl.get(
                    "items", []) if item.get("submissions")]
            if items_with_pending:
                cl["items"] = items_with_pending
                filtered_data.append(cl)
        print(filtered_data)
        return Response(filtered_data, status=200)


class CreateSubmissionsForChecklistItemsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        checklist_id = request.data.get('checklist_id')
        user_id = request.user.id

        if not checklist_id:
            return Response(
                {"detail": "checklist_id is required."}, status=400)
        checklist = Checklist.objects.get(id=checklist_id)
        checklist.status = 'IN_PROGRESS'
        checklist.save()

        items = ChecklistItem.objects.filter(checklist_id=checklist_id)
        created = []
        for item in items:
            obj, created_flag = ChecklistItemSubmission.objects.get_or_create(
                checklist_item=item,
                user=user_id,
            )
            item.status = "IN_PROGRESS"
            item.save()
            created.append(obj.id)

        return Response({
            "message": f"Submissions created for checklist {checklist_id}",
            "submission_ids": created
        }, status=status.HTTP_201_CREATED)


class PatchChecklistItemSubmissionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        submission_id = request.data.get("submission_id")
        maker_photo = request.FILES.get("maker_photo")

        if not submission_id:
            return Response(
                {"detail": "submission_id is required."}, status=400)

        try:
            submission = ChecklistItemSubmission.objects.get(id=submission_id)
        except ChecklistItemSubmission.DoesNotExist:
            return Response(
                {"detail": "ChecklistItemSubmission not found."}, status=404)

        submission.status = "COMPLETED"
        submission.save()
        if maker_photo:
            submission.maker_photo = maker_photo

            submission.save(update_fields=["maker_photo"])
            item = submission.checklist_item
            item.status = "DONE"
            item.save(update_fields=["status"])
            return Response({
                "message": "Photo uploaded to ChecklistItemSubmission.",
                "submission_id": submission.id,
                "maker_photo": submission.maker_photo.url if submission.maker_photo else None,
            }, status=200)
        else:
            item = submission.checklist_item
            item.status = "DONE"
            item.save(update_fields=["status"])
            return Response({
                "message": "ChecklistItem marked as DONE.",
                "checklist_item_id": item.id,
                "status": item.status,
            }, status=200)


class MyHierarchicalVerificationsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        print(f"🔍 Fetching verifications for checker user_id: {user_id}")

        try:
            # Method 1: Try direct ORM query first
            print("🔄 Attempting direct ORM query...")

            try:
                checklists = Checklist.objects.filter(
                    items_submissions_checked_by_id=user_id,
                    items_submissionsselected_option_isnull=True
                ).distinct()
                print(f"📊 Direct query found {checklists.count()} checklists")
            except Exception as orm_error:
                print(f"⚠ Direct ORM query failed: {orm_error}")
                checklists = Checklist.objects.none()

            # Method 2: Fallback to submission-based lookup
            if checklists.count() == 0:
                print("🔄 Using fallback method: submission-based lookup...")

                # Get all pending submissions for this checker
                pending_submissions = ChecklistItemSubmission.objects.filter(
                    checked_by_id=user_id,
                    selected_option__isnull=True
                )

                print(
                    f"📝 Found {pending_submissions.count()} pending submissions for checker {user_id}")

                if pending_submissions.exists():
                    # Get checklist IDs from those submissions
                    checklist_ids = set()
                    for submission in pending_submissions:
                        if submission.checklist_item and submission.checklist_item.checklist:
                            checklist_ids.add(
                                submission.checklist_item.checklist.id)

                    print(f"📋 Found checklist IDs: {list(checklist_ids)}")

                    # Get the checklists
                    checklists = Checklist.objects.filter(id__in=checklist_ids)
                    print(
                        f"📊 Fallback method found {checklists.count()} checklists")

            if checklists.count() == 0:
                print("ℹ No checklists found needing verification")
                return Response([], status=200)

            # Serialize the checklists
            serializer = ChecklistWithNestedItemsSerializer(
                checklists,
                many=True,
                context={"request": request}
            )

            print(f"📦 Serialized {len(serializer.data)} checklists")

            # Filter to only include items with pending submissions
            data = []
            for checklist in serializer.data:
                items_with_pending_subs = []

                for item in checklist["items"]:
                    # Only include items that have submissions needing
                    # verification
                    pending_subs = [
                        sub for sub in item["submissions"]
                        if (sub["selected_option"] is None and
                            sub["checked_by_id"] == user_id)
                    ]

                    if pending_subs:
                        # Create a copy of the item with only pending
                        # submissions
                        item_copy = item.copy()
                        item_copy["submissions"] = pending_subs
                        items_with_pending_subs.append(item_copy)
                        print(
                            f"  📝 Item {item['id']}: {len(pending_subs)} pending submissions")

                if items_with_pending_subs:
                    checklist_copy = checklist.copy()
                    checklist_copy["items"] = items_with_pending_subs
                    checklist_copy["total_pending_verifications"] = sum(
                        len(item["submissions"]) for item in items_with_pending_subs
                    )
                    data.append(checklist_copy)
                    print(
                        f"✅ Checklist {checklist['id']}: {checklist['name']} has {len(items_with_pending_subs)} items to verify")

            print(f"🎯 Returning {len(data)} checklists for verification")

            # Debug: Print sample data structure
            if data:
                sample_checklist = data[0]
                print(f"📋 Sample checklist structure:")
                print(f"  - ID: {sample_checklist.get('id')}")
                print(f"  - Name: {sample_checklist.get('name')}")
                print(
                    f"  - Items count: {len(sample_checklist.get('items', []))}")
                if sample_checklist.get('items'):
                    sample_item = sample_checklist['items'][0]
                    print(
                        f"  - Sample item submissions: {len(sample_item.get('submissions', []))}")

            return Response(data, status=200)

        except Exception as e:
            print(f"❌ Error in MyHierarchicalVerificationsAPIView: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Failed to fetch verifications: {str(e)}"},
                status=500
            )


class BulkVerifyChecklistItemSubmissionsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        ids = request.data.get("submission_ids")
        user_id = request.user.id

        if not ids or not isinstance(ids, list):
            return Response(
                {"detail": "submission_ids (list) required."}, status=400)

        updated = []
        for submission_id in ids:
            try:
                submission = ChecklistItemSubmission.objects.get(
                    id=submission_id)
            except ChecklistItemSubmission.DoesNotExist:
                continue  # skip if not found

            # Update submission
            submission.checked_by_id = user_id
            submission.checked_at = timezone.now()
            submission.save(update_fields=["checked_by_id", "checked_at"])

            # Update related item
            item = submission.checklist_item
            # item.status = "VERIFYING"
            item.save(update_fields=["status"])

            updated.append(submission_id)

        return Response({
            "message": "Submissions verified and checklist items set to VERIFYING.",
            "verified_submission_ids": updated
        }, status=200)


class VerifyChecklistItemSubmissionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        # Print the whole request.data and request.FILES for debugging
        # print("PATCH DATA:", request.data)
        # print("PATCH FILES:", request.FILES)

        submission_id = request.data.get('submission_id')
        role = request.data.get('role')  # "checker" or "inspector"
        option_id = request.data.get('option_id')
        check_remark = request.data.get('check_remark', '')
        check_photo = request.FILES.get('check_photo', None)

        # Print parsed values
        print("submission_id:", submission_id)
        print("role:", role)
        print("option_id:", option_id)
        print("check_remark:", check_remark)
        print("check_photo:", check_photo)

        if not submission_id or not role or not option_id:
            print("❌ Required field missing in request")
            return Response(
                {"detail": "submission_id, role, and option_id are required."}, status=400)

        # Get objects
        try:
            submission = ChecklistItemSubmission.objects.select_related(
                'checklist_item').get(id=submission_id)
        except ChecklistItemSubmission.DoesNotExist:
            print("❌ Submission not found")
            return Response(
                {"detail": "ChecklistItemSubmission not found."}, status=404)

        try:
            option = ChecklistItemOption.objects.get(id=option_id)
        except ChecklistItemOption.DoesNotExist:
            print("❌ Option not found")
            return Response(
                {"detail": "ChecklistItemOption not found."}, status=404)

        item = submission.checklist_item
        print('item', item.status)
        print('item', item.id)
        # --- Checker Logic ---
        if role == "checker":
            print("Checker logic triggered. Current item.status:", item.status)
            if item.status not in ["DONE", "IN_PROGRESS"]:
                print("❌ Item status is not DONE (it's %s)" % item.status)
                return Response(
                    {"detail": "Item must be DONE before checker can act."}, status=400)
            submission.check_remark = check_remark
            submission.checked_by_id = request.user.id
            submission.checked_at = timezone.now()
            # submission.selected_option = option

            if option.value == "N":
                # Mark the current submission as rejected and item not started
                item.status = "NOT_STARTED"
                submission.status = "REJECTED"
                item.save(update_fields=["status"])
                submission.save(
                    update_fields=[
                        "check_remark",
                        "checked_by_id",
                        "checked_at",
                        "status"])
                item.status = "IN_PROGRESS"
                item.save(update_fields=["status"])
                new_submission = ChecklistItemSubmission.objects.create(
                    checklist_item=item,
                    status="IN_PROGRESS",
                    user=submission.user  # reassign to the original maker
                )

                print(
                    f"Reopened item {item.id} for Maker {submission.user}, new submission {new_submission.id}")

            elif option.value == "P":
                item.status = "VERIFIED"
            else:
                print("❌ Invalid option value for checker:", option.value)
                return Response(
                    {"detail": "Invalid option for checker."}, status=400)

            item.save(update_fields=["status"])
            submission.save(
                update_fields=[
                    "check_remark",
                    "checked_by_id",
                    "checked_at",
                    "status"])

        # --- Inspector Logic ---
        elif role == "SUPERVISOR":
            print("Supervisor logic triggered. Current item.status:", item.status)
            if item.status != "VERIFIED":
                print("❌ Item status is not VERIFIED (it's %s)" % item.status)
                return Response(
                    {"detail": "Item must be VERIFIED before supervisor can act."}, status=400)
            if check_photo:
                submission.check_photo = check_photo
            submission.check_remark = check_remark
            submission.inspected_by_id = request.user.id
            submission.inspected_at = timezone.now()
            # submission.selected_option = option

            if option.value == "P":
                item.status = "COMPLETED"
                submission.status = "COMPLETED"
                item.save(update_fields=["status"])
                submission.save(
                    update_fields=[
                        "check_photo",
                        "check_remark",
                        "inspected_by_id",
                        "inspected_at",
                        "status"])
            elif option.value == "N":
                # Supervisor rejected: restart for maker
                item.status = "NOT_STARTED"
                submission.status = "REJECTED"
                item.save(update_fields=["status"])
                submission.save(
                    update_fields=[
                        "check_photo",
                        "check_remark",
                        "inspected_by_id",
                        "inspected_at",
                        "status"])
                # Mark item as IN_PROGRESS for new submission
                item.status = "IN_PROGRESS"
                item.save(update_fields=["status"])
                new_submission = ChecklistItemSubmission.objects.create(
                    checklist_item=item,
                    status="IN_PROGRESS",
                    user=submission.user  # original maker
                )
                print(
                    f"Reopened item {item.id} for Maker {submission.user}, new submission {new_submission.id}")
            else:
                print("❌ Invalid option value for supervisor:", option.value)
                return Response(
                    {"detail": "Invalid option for supervisor."}, status=400)


            item.save(update_fields=["status"])
            submission.save(
                update_fields=[
                    "check_photo",
                    "check_remark",
                    "inspected_by_id",
                    "inspected_at",
                    "status"])
        else:
            print("❌ Invalid role:", role)
            return Response(
                {"detail": "Invalid role. Must be 'checker' or 'inspector'."}, status=400)

        print("✅ Success! Item and submission updated.")
        return Response({
            "item_id": item.id,
            "item_status": item.status,
            "submission_id": submission.id,
            "submission_status": submission.status,
        }, status=200)


class VerifiedByCheckerPendingInspectorAPIView(APIView):
    permission_classes = [IsAuthenticated]
    USER_SERVICE_URL = "http://192.168.23.214:8000/api/user-access/"

    def get(self, request):
        user_id = request.user.id
        project_id = request.query_params.get("project_id")

        if not user_id or not project_id:
            return Response(
                {"detail": "user_id and project_id required."}, status=400)

        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(
                " ")[1] if " " in auth_header else auth_header

        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            resp = requests.get(
                self.USER_SERVICE_URL,
                params={"user_id": user_id, "project_id": project_id},
                timeout=5,
                headers=headers
            )
            if resp.status_code != 200:
                return Response(
                    {"detail": "Could not fetch user access"}, status=400)
            accesses = resp.json()

        except Exception as e:
            return Response({"detail": "User service error",
                            "error": str(e)}, status=400)
        print(accesses)
        print(Checklist.objects.filter(project_id=34))
        q = Q()
        for access in accesses:
            cat_q = Q()
            if access.get('category'):
                cat_q &= Q(checklist__category=access['category'])
                for i in range(1, 7):
                    key = f'CategoryLevel{i}'
                    if access.get(key) is not None:
                        cat_q &= Q(
                            **{f'checklist__category_level{i}': access[key]})
                    else:
                        break

            loc_q = Q()
            if access.get('flat_id'):
                loc_q &= Q(checklist__flat_id=access['flat_id'])
            elif access.get('zone_id'):
                loc_q &= Q(checklist__zone_id=access['zone_id'])
            elif access.get('building_id'):
                loc_q &= Q(checklist__building_id=access['building_id'])

            q |= (cat_q & loc_q)

        checklist_items = ChecklistItem.objects.filter(status="VERIFIED")

        submissions = ChecklistItemSubmission.objects.filter(
            checklist_item__in=checklist_items,
            status="COMPLETED",
            checked_by_id__isnull=False,
            checked_at__isnull=False,
            inspected_by_id__isnull=True,
            inspected_at__isnull=True,
            # selected_option__isnull=True,
        ).order_by("-accepted_at")

        serializer = ChecklistItemSubmissionSerializer(
            submissions, many=True, context={"request": request}
        )

        print("🔍 Submissions Data:", serializer.data)

        return Response(serializer.data, status=200)


class MyChecklistItemSubmissions(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        submissions = ChecklistItemSubmission.objects.filter(user=user_id)
        serializer = ChecklistItemSubmissionSerializer(
            submissions, many=True, context={"request": request}
        )
        return Response(serializer.data)


class PendingVerificationsForCheckerAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        # Find all checklists where this user is a checker
        checklists = Checklist.objects.filter(
            roles_json__checker__contains=[user_id])
        submissions = ChecklistItemSubmission.objects.filter(
            checklist_item__checklist__in=checklists,
            checked_by_id__isnull=True,  # Not yet checked
            status="DONE"
        )
        serializer = ChecklistItemSubmissionSerializer(
            submissions, many=True, context={"request": request}
        )
        return Response(serializer.data)


class PendingVerificationsForSupervisorAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        checklists = Checklist.objects.filter(
            roles_json__supervisor__contains=[user_id])
        submissions = ChecklistItemSubmission.objects.filter(
            checklist_item__checklist__in=checklists,
            inspected_by_id__isnull=True,
            status="VERIFIED"
        )
        serializer = ChecklistItemSubmissionSerializer(
            submissions, many=True, context={"request": request}
        )
        return Response(serializer.data)


class PatchChecklistRolesJsonAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, checklist_id):
        # Accept roles_json as a dict or string
        roles_json = request.data.get('roles_json')
        if not roles_json:
            return Response(
                {'roles_json': 'This field is required.'}, status=400)
        # Parse JSON if sent as a string
        if isinstance(roles_json, str):
            try:
                roles_json = json.loads(roles_json)
            except Exception as e:
                return Response(
                    {'roles_json': 'Invalid JSON format.'}, status=400)
        # Get the checklist
        try:
            checklist = Checklist.objects.get(id=checklist_id)
        except Checklist.DoesNotExist:
            return Response({'error': 'Checklist not found.'}, status=404)
        # Update and save
        checklist.roles_json = roles_json
        checklist.save(update_fields=['roles_json'])
        return Response({'message': 'roles_json updated.',
                        'roles_json': checklist.roles_json}, status=200)

