import json
import traceback
from collections import defaultdict

import requests
from django.db import models, transaction
from django.db.models import (
    Q, Exists, OuterRef, Subquery, F, Case, When, IntegerField
)
from django.utils import timezone


import requests
from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db import transaction, models
from django.utils import timezone
import requests
from collections import defaultdict

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
from checklists.models import StageHistory
import os
import requests
import weasyprint
from django.conf import settings
from django.template.loader import render_to_string
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import Checklist
from datetime import datetime





from django.utils import timezone


def get_project_flags(project_id, headers=None):
    """
    Return dict like:
        {
            "skip_supervisory": bool,
            "checklist_repoetory": bool
        }
    Defaults to False for both on errors or missing keys.
    """
    try:
        url = f"https://{local}/projects/projects/{project_id}/"
        resp = requests.get(url, headers=headers or {}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "skip_supervisory": bool(data.get("skip_supervisory", False)),
                "checklist_repoetory": bool(data.get("checklist_repoetory", False)),
            }
    except Exception:
        pass
    return {
        "skip_supervisory": False,
        "checklist_repoetory": False,
    }



from collections import defaultdict
from django.db import models
from django.db.models import Q, Exists, OuterRef
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework import status
import requests

# assume these are imported from your app
# from .models import Checklist, ChecklistItem, ChecklistItemOption, ChecklistItemSubmission, StageHistory
# from .serializers import ChecklistSerializer, ChecklistItemSerializer, ChecklistItemOptionSerializer, ChecklistItemSubmissionSerializer

class RoleBasedChecklistTRANSFERRULEAPIView(APIView):
    permission_classes = [IsAuthenticated]

    BASE_ROLE_API = f"https://{local}/users"
    USER_ACCESS_API = f"https://{local}/users/user-access/"

    ROLE_STATUS_MAP = {
        "checker": ["pending_for_inspector", "completed", "pending_for_maker"],
        "maker": ["pending_for_maker", "tetmpory_inspctor", "completed", "pending_for_supervisor"],
        "supervisor": ["tetmpory_inspctor", "pending_for_supervisor", "completed", "tetmpory_Maker"],
    }

    # ---------------------------
    # Project flags / roles / rules
    # ---------------------------

    @staticmethod
    def get_project_skip_supervisory(project_id, headers=None) -> bool:
        try:
            url = f"https://konstruct.world/projects/projects/{project_id}/"
            resp = requests.get(url, headers=headers or {}, timeout=5)
            if resp.status_code == 200:
                return bool(resp.json().get("skip_supervisory", False))
        except Exception:
            pass
        return False

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





class MAker_DOne_view(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_true_level(self, project_id):
        try:
            resp = requests.get(
                f"https://{local}/projects/transfer-rules/",
                params={"project_id": project_id},
                timeout=5,
            )
            if resp.status_code == 200 and resp.json():
                return resp.json()[0].get("true_level")
        except Exception:
            pass
        return None

    def _group_filters_for_checklist(self, checklist, true_level):
        fk = {"project_id": checklist.project_id, "stage_id": checklist.stage_id}
        if true_level == "flat_level":
            fk["flat_id"] = checklist.flat_id
        elif true_level == "room_level":
            fk["room_id"] = checklist.room_id
        elif true_level == "zone_level":
            fk["zone_id"] = checklist.zone_id
        elif true_level == "level_id":
            fk["level_id"] = checklist.level_id
        elif true_level == "checklist_level":
            fk["id"] = checklist.id
        return fk

    @transaction.atomic
    def post(self, request):
        checklist_item_id = request.data.get("checklist_item_id")
        maker_remark = request.data.get("maker_remark", "")
        maker_media = request.FILES.get("maker_media", None)

        if not checklist_item_id:
            return Response({"detail": "checklist_item_id required."}, status=400)

        # 1) Item must be pending_for_maker
        try:
            item = ChecklistItem.objects.select_related("checklist").get(
                id=checklist_item_id, status="pending_for_maker"
            )
        except ChecklistItem.DoesNotExist:
            return Response(
                {"detail": "ChecklistItem not found or not pending for maker."},
                status=404,
            )

        checklist = item.checklist
        project_id = checklist.project_id

        latest_submission = (
            ChecklistItemSubmission.objects
            .filter(checklist_item=item, status="created")
            .order_by("-attempts", "-created_at")
            .first()
        )
        if not latest_submission:
            return Response(
                {"detail": "No matching submission found for rework."},
                status=404,
            )

        if not latest_submission.maker_id:
            latest_submission.maker_id = request.user.id

        # 3) Decide path based on project flag
        headers = {}
        auth_header = request.headers.get("Authorization")
        if auth_header:
            headers["Authorization"] = auth_header  # keep full "Bearer ..." as-is

        flags = get_project_flags(project_id, headers=headers)
        skip_super = flags.get("skip_supervisory", False)

        if skip_super:
            # Bypass supervisor → go straight to checker
            latest_submission.status = "pending_checker"
            # keep item temp until the (category) slice is ready
            item.status = "tetmpory_inspctor"
        else:
            # Normal flow (Supervisor step)
            latest_submission.status = "pending_supervisor"
            item.status = "pending_for_supervisor"

        # 4) Update maker fields
        latest_submission.maker_remarks = maker_remark
        latest_submission.maker_at = timezone.now()
        if maker_media:
            latest_submission.maker_media = maker_media

        latest_submission.save(
            update_fields=[
                "status", "maker_id", "maker_remarks", "maker_media", "maker_at"
            ]
        )
        item.save(update_fields=["status"])

        # 5) When skipping supervisor, promote ONLY the same-category slice
        if skip_super:
            true_level = self._get_true_level(project_id)
            group_fk = self._group_filters_for_checklist(checklist, true_level)

            # Build category branch Q from the current checklist
            branch_q = Q(category=checklist.category)
            for i in range(1, 7):
                lvl = getattr(checklist, f"category_level{i}", None)
                if lvl is not None:
                    branch_q &= Q(**{f"category_level{i}": lvl})
                else:
                    break

            # Limit group to the same location + same category branch
            checklists_in_group = Checklist.objects.filter(**group_fk).filter(branch_q)

            # If ALL items in this category-slice are either completed or temp-inspector,
            # flip all temp-inspector to pending_for_inspector (visible to checker).
            not_ready_for_inspector_exists = ChecklistItem.objects.filter(
                checklist__in=checklists_in_group
            ).exclude(status__in=["completed", "tetmpory_inspctor"]).exists()

            if not not_ready_for_inspector_exists:
                ChecklistItem.objects.filter(
                    checklist__in=checklists_in_group,
                    status="tetmpory_inspctor"
                ).update(status="pending_for_inspector")

            # Similarly, re-open temp maker slice only when all others are in allowed temp states
            not_ready_for_maker_exists = ChecklistItem.objects.filter(
                checklist__in=checklists_in_group
            ).exclude(status__in=["completed", "tetmpory_Maker", "tetmpory_inspctor"]).exists()

            if not not_ready_for_maker_exists:
                ChecklistItem.objects.filter(
                    checklist__in=checklists_in_group,
                    status="tetmpory_Maker"
                ).update(status="pending_for_maker")

        # 6) Response
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
        return Response(
            {
                "item": item_data,
                "submission": submission_data,
                "detail": "Checklist item marked as done by maker."
            },
            status=200
        )

    def get(self, request):
        """
        Optional: list the maker's submissions (open and recently submitted).
        """
        user_id = request.user.id
        queryset = ChecklistItemSubmission.objects.filter(
            maker_id=user_id,
            status__in=["created", "pending_supervisor", "pending_checker"]
        ).order_by("-created_at")
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

