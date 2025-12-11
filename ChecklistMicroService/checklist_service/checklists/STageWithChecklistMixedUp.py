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
from checklists.models import StageHistory
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
from django.utils import timezone
from django.utils import timezone






class RoleBasedChecklistTRANSFERRULEAPIView(APIView):
    permission_classes = [IsAuthenticated]
    BASE_ROLE_API = f"https://{local}/users"
    ROLE_STATUS_MAP = {
        "checker": ["pending_for_inspector", "completed", "pending_for_maker"],
        "maker": ["pending_for_maker", "tetmpory_inspctor", "completed", "pending_for_supervisor"],
        "supervisor": ["tetmpory_inspctor", "pending_for_supervisor", "completed", "tetmpory_Maker"],
    }

    def get_stage_info(self, stage_id):
        try:
            url = f"https://{local}/projects/stages/{stage_id}/info/"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print("Could not fetch stage info:", e)
        return None

    def all_items_have_status(self, checklists, allowed_statuses):
        filtered = []
        for checklist in checklists:
            items = ChecklistItem.objects.filter(checklist=checklist)
            item_count = items.count()
            valid_count = items.filter(status__in=allowed_statuses).count()
            if item_count > 0 and item_count == valid_count:
                filtered.append(checklist)
        return filtered
    
    def filter_by_level(self, checklists, allowed_statuses, true_level, project_id, headers):
        """
        Returns only those checklists at the correct stage/level,
        using Python lists for deduplication and avoiding .union() for compatibility.
        """
        print(f"\n--- filter_by_level CALLED ---")
        print(f"true_level: {true_level}")
        print(f"Allowed statuses: {allowed_statuses}")
        print(f"Total incoming checklists: {checklists.count()}")

        if true_level == "checklist_level":
            keep_ids = []
            for checklist in checklists:
                print(f"\nChecking Checklist ID: {checklist.id}")
                # 1. Find current stage history for this checklist
                stage_history = StageHistory.objects.filter(
                    checklist=checklist, is_current=True
                ).first()
                print(f"StageHistory: {stage_history}")
                current_stage_id = stage_history.stage if stage_history else checklist.stage_id
                print(f"Current stage ID: {current_stage_id}")

                # 2. Are all items in allowed statuses?
                items = ChecklistItem.objects.filter(checklist=checklist)
                item_count = items.count()
                valid_count = items.filter(status__in=allowed_statuses).count()
                print(f"Checklist {checklist.id} has {item_count} items, {valid_count} in allowed statuses.")

                if item_count > 0 and valid_count == item_count:
                    print(f"All items in allowed statuses for checklist {checklist.id}, moving to next stage.")
                    next_stage_id = self.get_next_stage_id(current_stage_id, project_id, headers)
                    print(f"Next stage ID: {next_stage_id}")
                    if next_stage_id:
                        if stage_history:
                            stage_history.is_current = False
                            stage_history.save()
                            print(f"Marked StageHistory {stage_history.id} as not current.")
                        next_history, created = StageHistory.objects.get_or_create(
                            checklist=checklist,
                            stage=next_stage_id,
                            defaults={'is_current': True}
                        )
                        print(f"Next StageHistory for checklist {checklist.id} created: {created}")
                        if not created:
                            next_history.is_current = True
                            next_history.save()
                            print(f"Set existing StageHistory {next_history.id} as current.")

                        # 6. Fetch checklist(s) for next stage for this checklist/flat
                        next_checklists = Checklist.objects.filter(
                            flat_id=checklist.flat_id,
                            stage_id=next_stage_id,
                            project_id=project_id,
                        )
                        print(f"Next checklists found for flat {checklist.flat_id}: {list(next_checklists.values_list('id', flat=True))}")
                        keep_ids.extend(next_checklists.values_list('id', flat=True))
                else:
                    print(f"Checklist {checklist.id} is NOT all in allowed statuses, keeping in current stage.")
                    keep_ids.append(checklist.id)
            keep_ids = list(set(keep_ids))
            print(f"Final keep_ids (checklist_level): {keep_ids}")
            result = Checklist.objects.filter(id__in=keep_ids)
            print(f"Returning {result.count()} checklists at checklist_level.")
            return result

        elif true_level in ["flat_level", "room_level", "zone_level"]:
            location_field = {
                "flat_level": "flat_id",
                "room_level": "room_id",
                "zone_level": "zone_id"
            }.get(true_level)
            print(f"Location field for this level: {location_field}")

            locations = checklists.values_list(location_field, flat=True).distinct()
            print(f"Unique locations to process: {list(locations)}")
            current_purpose = self.get_current_purpose(project_id, headers)
            print(f"Current purpose: {current_purpose}")
            if not current_purpose:
                print(f"No current purpose found for project {project_id}, returning empty queryset")
                return Checklist.objects.none()
            current_purpose_id = current_purpose["id"]

            phases = self.get_phases(project_id, headers)
            print(f"Phases: {phases}")
            stages = self.get_stages(project_id, headers)
            print(f"Stages: {stages}")

            keep_ids = []
            for loc_id_tuple in locations:
                loc_id = loc_id_tuple if isinstance(loc_id_tuple, int) else loc_id_tuple[0]
                print(f"\nProcessing location ID: {loc_id}")
                if loc_id is None:
                    print("loc_id is None, skipping.")
                    continue

                # Get stage history for this location and current purpose
                stage_id = self.get_or_create_stage_history(
                    project_id,
                    phases=phases,
                    stages=stages,
                    zone_id=loc_id if true_level == "zone_level" else None,
                    flat_id=loc_id if true_level == "flat_level" else None,
                    room_id=loc_id if true_level == "room_level" else None,
                    current_purpose_id=current_purpose_id
                )
                print(f"Stage ID for location {loc_id}: {stage_id}")
                if not stage_id:
                    print("No stage ID found, skipping location.")
                    continue

                # Get all checklists at this location and stage
                filters = {
                    location_field: loc_id,
                    "project_id": project_id,
                    "stage_id": stage_id,
                }
                group_checklists = Checklist.objects.filter(**filters)
                print(f"Group checklists for location {loc_id}, stage {stage_id}: {[c.id for c in group_checklists]}")

                # Check if all checklists in this group have all items in allowed_statuses
                completed_count = len(self.all_items_have_status(group_checklists, allowed_statuses))
                group_count = group_checklists.count()
                print(f"{completed_count} of {group_count} checklists at this group are all in allowed statuses.")
                if completed_count == group_count:
                    print(f"Adding group checklist IDs: {list(group_checklists.values_list('id', flat=True))}")
                    keep_ids.extend(list(group_checklists.values_list('id', flat=True)))

            keep_ids = list(set(keep_ids))
            print(f"Final keep_ids ({true_level}): {keep_ids}")
            result = Checklist.objects.filter(id__in=keep_ids)
            print(f"Returning {result.count()} checklists at {true_level}.")
            return result

        else:
            print(f"Unknown true_level: {true_level}, returning empty queryset.")
            return Checklist.objects.none()

    @staticmethod
    def get_branch_q(access):
        q = Q()
        if access.get('category'):
            q &= Q(category=access.get('category'))
        for i in range(1, 7):
            key = f'CategoryLevel{i}'
            val = access.get(key)
            if val is not None:
                q &= Q(**{f'category_level{i}': val})
            else:
                break
        return q

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

    def get_true_level(self, project_id):
        TRANSFER_RULE_API = f"https://{local}/projects/transfer-rules/"
        try:
            resp = requests.get(TRANSFER_RULE_API, params={"project_id": project_id})
            if resp.status_code == 200 and resp.json():
                return resp.json()[0].get("true_level")
        except Exception as e:
            print("TransferRule error:", e)
        return None

    def get_current_purpose(self, project_id, headers):
        try:
            url = f"https://{local}/projects/projects/{project_id}/activate-purpose/"
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                purpose_data = resp.json()
                if purpose_data.get("is_current"):
                    return purpose_data
            return None
        except Exception as e:
            print(f"Error fetching current purpose: {e}")
            return None

    def get_phases(self, project_id, headers):
        try:
            url = f"https://{local}/projects/phases/by-project/{project_id}/"
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            print(f"Error fetching phases: {e}")
            return []

    def get_stages(self, project_id, headers):
        try:
            url = f"https://{local}/projects/get-stage-details-by-project-id/{project_id}/"
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            print(f"Error fetching stages: {e}")
            return []

    def get_or_create_stage_history(
        self, project_id, phases, stages,
        zone_id=None, flat_id=None, room_id=None,
        current_purpose_id=None, checklist_id=None
    ):
        try:
            filters = {"project": project_id, "is_current": True}
            if flat_id is not None:
                filters["flat"] = flat_id
            if room_id is not None:
                filters["room"] = room_id
            if zone_id is not None:
                filters["zone"] = zone_id
            if checklist_id is not None:
                filters["checklist_id"] = checklist_id  # For checklist_level

            stage_history = StageHistory.objects.filter(**filters).first()
            if stage_history:
                return stage_history.stage

            if checklist_id is not None:
                if not phases or not stages:
                    return None
                checklist = Checklist.objects.get(id=checklist_id)
                purpose_id = checklist.purpose_id
                purpose_phases = [p for p in phases if (
                    p.get('purpose') and (
                        p.get('purpose').get('id') if isinstance(p.get('purpose'), dict) else p.get('purpose')
                    ) == purpose_id
                )]
                if not purpose_phases:
                    return None
                lowest_phase = min(purpose_phases, key=lambda x: x.get('sequence', 0))
                phase_stages = [s for s in stages if s.get('phase') == lowest_phase['id']]
                if not phase_stages:
                    return None
                lowest_stage = min(phase_stages, key=lambda x: x.get('sequence', 0))

                new_stage_history = StageHistory.objects.create(
                    project=project_id,
                    phase_id=lowest_phase['id'],
                    stage=lowest_stage['id'],
                    is_current=True,
                    checklist_id=checklist_id
                )
                return new_stage_history.stage
            else:
                if not phases or not stages:
                    return None
                purpose_phases = [p for p in phases if (p.get('purpose') and (
                    p.get('purpose').get('id') if isinstance(p.get('purpose'), dict) else p.get('purpose')) == current_purpose_id)]
                if not purpose_phases:
                    return None
                lowest_phase = min(purpose_phases, key=lambda x: x.get('sequence', 0))
                phase_stages = [s for s in stages if s.get('phase') == lowest_phase['id']]
                if not phase_stages:
                    return None
                lowest_stage = min(phase_stages, key=lambda x: x.get('sequence', 0))
                new_stage_history = StageHistory.objects.create(
                    project=project_id,
                    zone=zone_id,
                    phase_id=lowest_phase['id'],
                    flat=flat_id,
                    room=room_id,
                    stage=lowest_stage['id'],
                    is_current=True
                )
                return new_stage_history.stage
        except Exception as e:
            print(f"Error in get_or_create_stage_history: {e}")
            return None

    def get_next_stage_id(self, current_stage_id, project_id, headers):
        stages = self.get_stages(project_id, headers)
        current = next((s for s in stages if s['id'] == current_stage_id), None)
        if not current:
            return None
        current_seq = current['sequence']
        phase_id = current['phase']
        # Find next stage in the same phase
        candidates = [s for s in stages if s['phase'] == phase_id and s['sequence'] > current_seq]
        if candidates:
            return sorted(candidates, key=lambda x: x['sequence'])[0]['id']
        # (optionally handle next phase logic)
        return None

    def get_checklists_of_current_stage(self, project_id, true_level, headers, request):
        print("\n--- get_checklists_of_current_stage ---")
        if true_level == "checklist_level":
            qs = Checklist.objects.filter(project_id=project_id)
            flat_id = self.safe_nt(request.query_params.get("flat_id"))
            if flat_id:
                qs = qs.filter(flat_id=flat_id)
            result_ids = []
            for checklist in qs:
                # Always ensure StageHistory exists for this checklist/stage
                cur_hist = StageHistory.objects.filter(checklist=checklist, is_current=True).first()
                if not cur_hist:
                    try:
                        cur_hist, created = StageHistory.objects.get_or_create(
                            checklist=checklist,
                            stage=checklist.stage_id,
                            defaults={
                                "is_current": True,
                                "project": checklist.project_id,
                                "phase_id": getattr(checklist, 'phase_id', None),
                                "flat": getattr(checklist, 'flat_id', None),
                                "room": getattr(checklist, 'room_id', None),
                                "zone": getattr(checklist, 'zone_id', None),
                            }
                        )
                        if created:
                            print(f"[PATCH] Created StageHistory for checklist {checklist.id}, stage {checklist.stage_id}")
                    except Exception as e:
                        print(f"[PATCH] Failed to create StageHistory for checklist {checklist.id}: {e}")
                if cur_hist:
                    cur_c = Checklist.objects.filter(id=checklist.id, stage_id=cur_hist.stage).first()
                    if cur_c:
                        result_ids.append(cur_c.id)
                else:
                    result_ids.append(checklist.id)
            print("Checklist-level: result_ids", result_ids)
            return Checklist.objects.filter(id__in=result_ids)
        else:
            current_purpose = self.get_current_purpose(project_id, headers)
            print("Current purpose:", current_purpose)
            if not current_purpose:
                print("No current purpose found!")
                return Checklist.objects.none()
            purpose_id = current_purpose["id"]
            print("Purpose ID being used:", purpose_id)
            phases = self.get_phases(project_id, headers)
            print("Phases:", phases)
            stages = self.get_stages(project_id, headers)
            print("Stages:", stages)
            if not phases or not stages:
                print("No phases or no stages found!")
                return Checklist.objects.none()
            location = {}
            if true_level == "flat_level":
                location["flat_id"] = self.safe_nt(request.query_params.get("flat_id"))
                location["zone_id"] = self.safe_nt(request.query_params.get("zone_id"))
                location["room_id"] = None
            elif true_level == "room_level":
                location["room_id"] = self.safe_nt(request.query_params.get("room_id"))
                location["flat_id"] = self.safe_nt(request.query_params.get("flat_id"))
                location["zone_id"] = self.safe_nt(request.query_params.get("zone_id"))
            elif true_level == "zone_level":
                location["zone_id"] = self.safe_nt(request.query_params.get("zone_id"))
                location["flat_id"] = None
                location["room_id"] = None
            else:
                location = {"flat_id": None, "zone_id": None, "room_id": None}
            print("Location dict:", location)
            stage_id = self.get_or_create_stage_history(
                project_id, phases, stages,
                zone_id=location.get("zone_id"),
                flat_id=location.get("flat_id"),
                room_id=location.get("room_id"),
                current_purpose_id=purpose_id
            )
            print("Stage ID being used:", stage_id)
            if not stage_id:
                print("No stage ID found!")
                return Checklist.objects.none()
            checklist_filter = Q(project_id=project_id, purpose_id=purpose_id, stage_id=stage_id)
            if true_level == "flat_level":
                checklist_filter &= Q(flat_id=location["flat_id"])
            elif true_level == "room_level":
                checklist_filter &= Q(room_id=location["room_id"])
            elif true_level == "zone_level":
                checklist_filter &= Q(zone_id=location["zone_id"])
            print("Checklist Q filter in get_checklists_of_current_stage:", checklist_filter)
            qs = Checklist.objects.filter(checklist_filter)
            print("QS count from get_checklists_of_current_stage:", qs.count())
            for c in qs:
                print("Checklist:", c.id, "flat:", c.flat_id, "purpose:", c.purpose_id, "stage:", c.stage_id)
            return qs

    def safe_nt(self, val):
        if val is None:
            return None
        try:
            return int(str(val).strip("/"))
        except Exception:
            return None
   
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
        """
        Handler for manager/client roles (read-only view, filtered by current purpose and stage).
        """
        true_level = self.get_true_level(project_id)
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        base_qs = self.get_checklists_of_current_stage(project_id, true_level, headers, request)

        paginator = LimitOffsetPagination()
        paginator.default_limit = 10
        paginated_checklists = paginator.paginate_queryset(base_qs, request, view=self)

        data = []
        for checklist in paginated_checklists:
            checklist_data = {
                "id": checklist.id,
                "title": checklist.title,
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

    def paginate_and_group_checker(self, request, assigned_checklists, available_checklists, headers):
        """
        Grouping and pagination for checker response (room-wise).
        """
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
            # ---- FIXED: Add stage_info per checklist, inside the loop ----
            if self.get_true_level(checklist.project_id) == "checklist_level":
                stage_info = self.get_stage_info(checklist.stage_id)
                if stage_info:
                    checklist_data["stage_info"] = stage_info

            if checklist in assigned_checklists:
                grouped[room_id]["assigned_to_me"].append(checklist_data)
            if checklist in available_checklists:
                grouped[room_id]["available_for_me"].append(checklist_data)

        response_data = [
            room_data for room_data in grouped.values()
            if room_data["assigned_to_me"] or room_data["available_for_me"]
        ]

        project_id = request.query_params.get("project_id")

        user_generated_qs = Checklist.objects.filter(
            user_generated_id__isnull=False,
            project_id=project_id,
            room_id__isnull=True  # Only those NOT assigned to a room
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


    def paginate_and_group_supervisor(self, request, assigned_checklists, available_checklists, headers):
        """
        Grouping and pagination for supervisor response (room-wise).
        """
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

            # ---- FIXED: Add stage_info per checklist, inside the loop ----
            if self.get_true_level(checklist.project_id) == "checklist_level":
                stage_info = self.get_stage_info(checklist.stage_id)
                if stage_info:
                    checklist_data["stage_info"] = stage_info

            if checklist in assigned_checklists:
                grouped[room_id]["assigned_to_me"].append(checklist_data)
            if checklist in available_checklists:
                grouped[room_id]["available_for_me"].append(checklist_data)

        response_data = [
            room_data for room_data in grouped.values()
            if room_data["assigned_to_me"] or room_data["available_for_me"]
        ]

        project_id = request.query_params.get("project_id")

        user_generated_qs = Checklist.objects.filter(
            user_generated_id__isnull=False,
            project_id=project_id,
            room_id__isnull=True  # Only those NOT assigned to a room
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

    def handle_checker(self, request, user_id, project_id):
        print("\n======= handle_checker CALLED =======")
        print(f"User ID: {user_id}, Project ID: {project_id}")

        # Get user auth token from headers
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        print(f"Authorization headers set for internal requests: {headers}")

        # Get the true level of the project (flat_level, room_level, zone_level, etc.)
        true_level = self.get_true_level(project_id)
        print(f"True Level obtained for project: {true_level}")

        # Get base queryset of checklists for the current stage, location, purpose, etc.
        base_qs = self.get_checklists_of_current_stage(project_id, true_level, headers, request)
        print(f"Base queryset count from get_checklists_of_current_stage: {base_qs.count()}")

        # Define allowed statuses for the checker role
        allowed_statuses = self.ROLE_STATUS_MAP.get("checker", [])
        print(f"Allowed checklist item statuses for checker role: {allowed_statuses}")

        # Filter checklists by level and allowed statuses
        filtered_checklists = self.filter_by_level(base_qs, allowed_statuses, true_level, project_id, headers)
        print(f"Filtered checklists count after filter_by_level: {filtered_checklists.count()}")

        # Define filters for assigned checklist items
        assigned_item_exists = ChecklistItem.objects.filter(
            checklist=OuterRef('pk'),
            status="pending_for_inspector",
            submissions__checker_id=user_id,
            submissions__status="pending_checker"
        )
        print("Defined assigned_item_exists subquery")

        # Define filters for available checklist items not assigned to any checker yet
        available_item_exists = ChecklistItem.objects.filter(
            checklist=OuterRef('pk'),
            status="pending_for_inspector",
            submissions__checker_id__isnull=True
        )
        print("Defined available_item_exists subquery")

        # Annotate filtered checklists with assigned items for the user
        assigned_to_me = filtered_checklists.annotate(has_assigned=Exists(assigned_item_exists)).filter(has_assigned=True)
        print(f"Checklists assigned to user: {assigned_to_me.count()}")

        # Annotate filtered checklists with available items not assigned yet
        available_for_me = filtered_checklists.annotate(has_available=Exists(available_item_exists)).filter(has_available=True)
        print(f"Available checklists for user: {available_for_me.count()}")

        # Remove checklists already assigned to avoid duplicates
        assigned_ids = set(c.id for c in assigned_to_me)
        available_for_me = [c for c in available_for_me if c.id not in assigned_ids]
        print(f"Available checklists after removing assigned duplicates: {len(available_for_me)}")

        # Finally, paginate and group checklists for response
        response = self.paginate_and_group_checker(request, assigned_to_me, available_for_me, headers)
        print("Returning paginated and grouped response for checker")
        return response

    def get_grouped_checklists_for_role(project_id, purpose_id, stage_id, location_filter, item_status):
        """
        Returns all checklists for this group (flat/zone/room + stage + purpose)
        IF ANY checklist in this group has at least one item with status `item_status`.
        """
        qs = Checklist.objects.filter(
            project_id=project_id,
            purpose_id=purpose_id,
            stage_id=stage_id,
            **location_filter
        )
        any_pending = ChecklistItem.objects.filter(
            checklist__in=qs,
            status=item_status
        ).exists()
        if any_pending:
            return qs
        return Checklist.objects.none()

    def handle_supervisor(self, request, user_id, project_id):
        true_level = self.get_true_level(project_id)
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        base_qs = self.get_checklists_of_current_stage(project_id, true_level, headers, request)
        allowed_statuses = self.ROLE_STATUS_MAP["supervisor"]
        true_level = self.get_true_level(project_id)
        filtered_checklists = self.filter_by_level(base_qs, allowed_statuses, true_level, project_id,headers)
        assigned_item_exists = ChecklistItem.objects.filter(
            checklist=OuterRef('pk'),
            status="pending_for_supervisor",
            submissions__supervisor_id=user_id,
            submissions__status="pending_supervisor"
        )
        available_item_exists = ChecklistItem.objects.filter(
            checklist=OuterRef('pk'),
            status="pending_for_supervisor",
            submissions__supervisor_id__isnull=True
        )
        assigned_to_me = filtered_checklists.annotate(has_assigned=Exists(assigned_item_exists)).filter(has_assigned=True)
        available_for_me = filtered_checklists.annotate(has_available=Exists(available_item_exists)).filter(has_available=True)
        assigned_ids = set(c.id for c in assigned_to_me)
        available_for_me = [c for c in available_for_me if c.id not in assigned_ids]
        return self.paginate_and_group_supervisor(request, assigned_to_me, available_for_me, headers)
    
    def handle_maker(self, request, user_id, project_id):
        true_level = self.get_true_level(project_id)
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        # Only checklists for the current stage and location
        checklist_qs = self.get_checklists_of_current_stage(project_id, true_level, headers, request)

        # 👇 BLOCK group unless all checklists at this true level/stage are in allowed_statuses
        allowed_statuses = self.ROLE_STATUS_MAP["maker"]
        filtered_checklists = self.filter_by_level(checklist_qs, allowed_statuses, true_level,project_id,headers)

        if not filtered_checklists:
            # Block: nothing available for this group at this stage yet
            return self.paginate_and_group_supervisor(request, [], [], headers)  # or a similar empty grouped response

        # The rest of your maker logic—just use filtered_checklists everywhere below!
        latest_submission_subq = ChecklistItemSubmission.objects.filter(
            checklist_item=OuterRef('pk')
        ).order_by('-attempts', '-created_at').values('id')[:1]

        base_items = ChecklistItem.objects.filter(
            checklist__in=filtered_checklists,
            status="pending_for_maker"
        ).annotate(
            latest_submission_id=Subquery(latest_submission_subq)
        )

        checklists_with_maker_items = filtered_checklists.filter(items__in=base_items).distinct()

        paginator = LimitOffsetPagination()
        paginator.default_limit = 10
        paginated_checklists = paginator.paginate_queryset(checklists_with_maker_items, request, view=self)

        # Add room info and group
        ROOM_SERVICE_URL = f"https://{local}/projects/rooms/"
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
            if room_id and room_id in room_details:
                grouped[room_id]["room_details"] = room_details[room_id]
            grouped[room_id]["room_id"] = room_id

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

        # (OPTIONAL) Add user-generated checklists if you use them in your UI
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

    def handle_intializer(self, request, user_id, project_id):
        print("\n======= handle_intializer CALLED =======")
        USER_SERVICE_URL = f"https://{local}/users/user-access/"
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        tower_id = self.safe_nt(request.query_params.get("tower_id"))
        flat_id = self.safe_nt(request.query_params.get("flat_id"))
        zone_id = self.safe_nt(request.query_params.get("zone_id"))
        print("Params - tower_id:", tower_id, "flat_id:", flat_id, "zone_id:", zone_id)

        try:
            resp = requests.get(
                USER_SERVICE_URL,
                params={"user_id": user_id, "project_id": project_id},
                timeout=5,
                headers=headers
            )
            print("User access API response status:", resp.status_code)
            if resp.status_code != 200:
                print("Could not fetch user access")
                return Response({"detail": "Could not fetch user access"}, status=400)
            accesses = resp.json()
            print("Accesses:", accesses)
        except Exception as e:
            print("User service error", str(e))
            return Response({"detail": "User service error", "error": str(e)}, status=400)

        true_level = self.get_true_level(project_id)
        print("True Level:", true_level)
        base_qs = self.get_checklists_of_current_stage(project_id, true_level, headers, request)
        print("Base_qs count after get_checklists_of_current_stage:", base_qs.count())
        for c in base_qs:
            print("Base_qs Checklist: id:", c.id, "flat_id:", c.flat_id, "purpose_id:", c.purpose_id, "stage_id:", c.stage_id)

        checklist_filter = Q()
        if flat_id:
            checklist_filter &= Q(flat_id=flat_id)
        elif zone_id:
            checklist_filter &= Q(zone_id=zone_id, flat_id__isnull=True, room_id__isnull=True)
        elif tower_id:
            checklist_filter &= Q(building_id=tower_id, zone_id__isnull=True, flat_id__isnull=True, room_id__isnull=True)
        print("Checklist filter Q object:", checklist_filter)

        category_filter = Q()
        for access in accesses:
            if access.get('category'):
                category_filter |= self.get_branch_q(access)
        print("Category filter Q object:", category_filter)

        filtered_qs = base_qs.filter(checklist_filter)
        print("Filtered_qs after checklist_filter count:", filtered_qs.count())
        for c in filtered_qs:
            print("Filtered_qs Checklist: id:", c.id, "flat_id:", c.flat_id, "purpose_id:", c.purpose_id, "stage_id:", c.stage_id)

        if category_filter:
            status_param = request.query_params.get("status")
            print("Status param:", status_param)
            if status_param:
                if "," in status_param:
                    statuses = [s.strip() for s in status_param.split(",")]
                    filtered_qs = filtered_qs.filter(category_filter, status__in=statuses).distinct()
                else:
                    filtered_qs = filtered_qs.filter(category_filter, status=status_param).distinct()
            else:
                filtered_qs = filtered_qs.filter(category_filter, status="not_started").distinct()
            print("Filtered_qs after category_filter count:", filtered_qs.count())
            for c in filtered_qs:
                print("Final Checklist after all filters: id:", c.id, "flat_id:", c.flat_id, "purpose_id:", c.purpose_id, "stage_id:", c.stage_id)
        else:
            print("No category filter, returning empty queryset")
            filtered_qs = Checklist.objects.none()

        return self.paginate_and_group(request, filtered_qs, headers)

    def paginate_and_group(self, request, checklists, headers):
        """
        Generic room-wise (RIS) grouping for checklists, with item and submission expansion.
        Adds stage_info inside each checklist if checklist_level,
        or adds current_stage_info at the group (room) level if flat_level.
        """
        paginator = LimitOffsetPagination()
        paginator.default_limit = 10
        paginated_checklists = paginator.paginate_queryset(checklists, request, view=self)

        # Determine project level ONCE (assumes all checklists are from the same project)
        true_level = None
        for c in paginated_checklists:
            true_level = self.get_true_level(c.project_id)
            break

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
            "checklists": []
        })

        # Store the current_stage_info for each group if needed
        group_stage_info = {}

        for checklist in paginated_checklists:
            room_id = checklist.room_id
            if room_id and room_id in room_details:
                grouped[room_id]["room_details"] = room_details[room_id]
            grouped[room_id]["room_id"] = room_id

            checklist_data = ChecklistSerializer(checklist).data

            # ------ PATCH: For checklist_level, add stage_info in each checklist -------
            if true_level == "checklist_level":
                stage_info = self.get_stage_info(checklist.stage_id)
                if stage_info:
                    checklist_data["stage_info"] = stage_info  # Place before items

            # ------ PATCH: For flat_level, collect one stage_info per group ---------
            if true_level == "flat_level":
                if room_id not in group_stage_info:
                    stage_info = self.get_stage_info(checklist.stage_id)
                    if stage_info:
                        group_stage_info[room_id] = stage_info

            # Items/Options/Submissions
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
            grouped[room_id]["checklists"].append(checklist_data)

        # ------- PATCH: For flat_level, inject stage_info at the group level -------
        if true_level == "flat_level":
            for room_id in grouped:
                if room_id in group_stage_info:
                    grouped[room_id]["current_stage_info"] = group_stage_info[room_id]

        response_data = [room_data for room_data in grouped.values() if room_data["checklists"]]
        return paginator.get_paginated_response(response_data)







class VerifyChecklistItemForCheckerNSupervisorAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_active_purpose(self, project_id):
        url = f"https://konstruct.world/projects/projects/{project_id}/activate-purpose/"
        try:
            resp = requests.get(url)
            print(f"[DEBUG] get_active_purpose: status {resp.status_code} for project {project_id}")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("is_current"):
                    print(f"[DEBUG] get_active_purpose: found active purpose id {data['id']}")
                    return data["id"]
            print("[DEBUG] get_active_purpose: no active purpose found or not current")
        except Exception as e:
            print(f"[ERROR] Purpose fetch error: {e}")
        return None

    def get_phases(self, project_id, purpose_id):
        url = f"https://konstruct.world/projects/phases/by-project/{project_id}/"
        try:
            resp = requests.get(url)
            print(f"[DEBUG] get_phases: status {resp.status_code} for project {project_id}, purpose {purpose_id}")
            if resp.status_code == 200:
                data = resp.json()
                phases = [p for p in data if p["purpose"]["id"] == purpose_id and p["is_active"]]
                phases.sort(key=lambda x: x["sequence"])
                print(f"[DEBUG] get_phases: found phases {[p['id'] for p in phases]}")
                return phases
            print(f"[DEBUG] get_phases: failed to get phases or empty list")
        except Exception as e:
            print(f"[ERROR] Phase fetch error: {e}")
        return []

    def get_stages(self, project_id, phase_id):
        url = f"https://konstruct.world/projects/get-stage-details-by-project-id/{project_id}/"
        try:
            resp = requests.get(url)
            print(f"[DEBUG] get_stages: status {resp.status_code} for project {project_id}, phase {phase_id}")
            if resp.status_code == 200:
                data = resp.json()
                stages = [s for s in data if s["phase"] == phase_id and s["is_active"]]
                stages.sort(key=lambda x: x["sequence"])
                print(f"[DEBUG] get_stages: found stages {[s['id'] for s in stages]}")
                return stages
            print(f"[DEBUG] get_stages: failed to get stages or empty list")
        except Exception as e:
            print(f"[ERROR] Stage fetch error: {e}")
        return []

    def get_true_level(self, project_id):
        TRANSFER_RULE_API = f"https://{local}/projects/transfer-rules/"
        try:
            resp = requests.get(TRANSFER_RULE_API, params={"project_id": project_id})
            print(f"[DEBUG] get_true_level: status {resp.status_code} for project {project_id}")
            if resp.status_code == 200 and resp.json():
                true_level = resp.json()[0].get("true_level")
                print(f"[DEBUG] get_true_level: true_level = {true_level}")
                return true_level
            print(f"[DEBUG] get_true_level: no transfer rule found or empty response")
        except Exception as e:
            print(f"[ERROR] TransferRule error: {e}")
        return None

    def advance_stage_if_completed(self, checklist, user_id, true_level):
        print(f"[DEBUG] advance_stage_if_completed called for checklist id={checklist.id} user_id={user_id} true_level={true_level}")

        project_id = checklist.project_id

        # Build filter for current StageHistory row
        filter_kwargs = {
            "project": project_id,
            "is_current": True,
        }
        if true_level == "flat_level":
            filter_kwargs["flat"] = checklist.flat_id
        elif true_level == "room_level":
            filter_kwargs["room"] = checklist.room_id
        elif true_level == "zone_level":
            filter_kwargs["zone"] = checklist.zone_id
        elif true_level == "level_id":
            filter_kwargs["level_id"] = checklist.level_id
        elif true_level == "checklist_level":
            filter_kwargs["checklist"] = checklist.id

        print(f"[DEBUG] advance_stage_if_completed: filter_kwargs = {filter_kwargs}")
        current_stagehistory = StageHistory.objects.filter(**filter_kwargs).first()
        if not current_stagehistory:
            print("[DEBUG] advance_stage_if_completed: No current StageHistory found")
            return False, "No current StageHistory found"

        # Check if all checklists at this true level and stage are completed
        checklists_in_group = Checklist.objects.filter(
            project_id=project_id,
            stage_id=current_stagehistory.stage,
        )
        if true_level == "flat_level":
            checklists_in_group = checklists_in_group.filter(flat_id=checklist.flat_id)
        elif true_level == "room_level":
            checklists_in_group = checklists_in_group.filter(room_id=checklist.room_id)
        elif true_level == "zone_level":
            checklists_in_group = checklists_in_group.filter(zone_id=checklist.zone_id)
        elif true_level == "level_id":
            checklists_in_group = checklists_in_group.filter(level_id=checklist.level_id)
        elif true_level == "checklist_level":
            checklists_in_group = checklists_in_group.filter(id=checklist.id)

        all_completed = not checklists_in_group.exclude(status="completed").exists()
        print(f"[DEBUG] advance_stage_if_completed: all_checklists_completed = {all_completed}")
        if not all_completed:
            return False, "Not all checklists are completed"

        # Mark current StageHistory completed
        current_stagehistory.is_current = False
        current_stagehistory.completed_at = timezone.now()
        current_stagehistory.completed_by = user_id
        current_stagehistory.status = "completed"
        current_stagehistory.save()
        print(f"[DEBUG] advance_stage_if_completed: Marked current StageHistory id={current_stagehistory.id} completed")

        # Fetch phases & stages for project & current phase
        purpose_id = self.get_active_purpose(project_id)
        phases = self.get_phases(project_id, purpose_id)
        if not phases:
            print("[DEBUG] advance_stage_if_completed: No phases found, assuming workflow complete")
            return True, "Phases not found, assuming workflow complete"

        # Find current phase index by matching phase_id in StageHistory (or fallback)
        current_phase_id = getattr(current_stagehistory, "phase_id", None) or checklist.phase_id
        phase_ids = [p["id"] for p in phases]
        try:
            current_phase_idx = phase_ids.index(current_phase_id)
        except ValueError:
            current_phase_idx = 0

        current_phase = phases[current_phase_idx]
        print(f"[DEBUG] advance_stage_if_completed: current_phase id={current_phase['id']}")

        stages = self.get_stages(project_id, current_phase["id"])
        if not stages:
            print("[DEBUG] advance_stage_if_completed: No stages found in current phase, assuming workflow complete")
            return True, "Stages not found, assuming workflow complete"

        stage_ids = [s["id"] for s in stages]
        try:
            current_stage_idx = stage_ids.index(current_stagehistory.stage)
        except ValueError:
            current_stage_idx = 0

        print(f"[DEBUG] advance_stage_if_completed: current_stage_idx={current_stage_idx}")

        current_seq = None
        for s in stages:
            if s["id"] == current_stagehistory.stage:
                current_seq = s["sequence"]
                break

        print(f"[DEBUG] Current stage sequence: {current_seq}")

        next_stage = None
        for s in stages:
            if s["sequence"] > current_seq:
                next_stage = s
                break

        if next_stage:
            next_phase = current_phase
            print(f"[DEBUG] Advancing to next stage {next_stage['id']} in current phase {next_phase['id']}")
        else:
            current_phase_seq = current_phase["sequence"]
            next_phase = None
            phases_sorted = sorted(phases, key=lambda x: x["sequence"])
            for p in phases_sorted:
                if p["sequence"] > current_phase_seq:
                    next_phase = p
                    break

            if not next_phase:
                print("[DEBUG] No further phases. Workflow complete.")
                return True, "Workflow fully completed"

            # Get stages for next phase
            next_stages = self.get_stages(project_id, next_phase["id"])
            if not next_stages:
                print("[DEBUG] No stages in next phase. Workflow complete.")
                return True, "No stages in next phase, workflow complete"

            # Pick lowest sequence stage in next phase
            next_stage = sorted(next_stages, key=lambda x: x["sequence"])[0]
            print(f"[DEBUG] Advancing to first stage {next_stage['id']} in next phase {next_phase['id']}")


        # Create new StageHistory for next stage
        new_stagehistory = StageHistory.objects.create(
            project=project_id,
            phase_id=next_phase["id"],
            stage=next_stage["id"],
            started_at=timezone.now(),
            is_current=True,
            flat=getattr(checklist, "flat_id", None),
            room=getattr(checklist, "room_id", None),
            zone=getattr(checklist, "zone_id", None),
            checklist=checklist if true_level == "checklist_level" else None,
            status="started",
        )
        print(f"[DEBUG] advance_stage_if_completed: Created new StageHistory id={new_stagehistory.id}")

        return True, {
            "new_phase_id": next_phase["id"],
            "new_stage_id": next_stage["id"],
            "msg": "Advanced to next stage"
        }

    def patch(self, request):
        checklist_item_id = request.data.get('checklist_item_id')
        role = request.data.get('role')
        option_id = request.data.get('option_id')

        print(f"[DEBUG] patch called with checklist_item_id={checklist_item_id}, role={role}, option_id={option_id}")

        if not checklist_item_id or not role or not option_id:
            print("[DEBUG] patch: missing required parameters")
            return Response({"detail": "checklist_item_id, role, and option_id are required."}, status=400)

        try:
            item = ChecklistItem.objects.get(id=checklist_item_id)
            print(f"[DEBUG] patch: fetched ChecklistItem id={item.id}")
        except ChecklistItem.DoesNotExist:
            print(f"[DEBUG] patch: ChecklistItem {checklist_item_id} not found")
            return Response({"detail": "ChecklistItem not found."}, status=404)

        try:
            option = ChecklistItemOption.objects.get(id=option_id)
            print(f"[DEBUG] patch: fetched ChecklistItemOption id={option.id}, choice={option.choice}")
        except ChecklistItemOption.DoesNotExist:
            print(f"[DEBUG] patch: ChecklistItemOption {option_id} not found")
            return Response({"detail": "ChecklistItemOption not found."}, status=404)

        checklist = item.checklist
        print(f"[DEBUG] patch: checklist id={checklist.id}")

        if role.lower() == "checker":
            check_remark = request.data.get('check_remark', '')
            check_photo = request.FILES.get('check_photo', None)

            submission = item.submissions.filter(
                checker_id=request.user.id,
                status="pending_checker"
            ).order_by('-attempts', '-created_at').first()

            if not submission:
                max_attempts = item.submissions.aggregate(max_attempts=models.Max('attempts'))['max_attempts'] or 0
                submission = ChecklistItemSubmission.objects.create(
                    checklist_item=item,
                    checker_id=request.user.id,
                    status="pending_checker",
                    attempts=max_attempts + 1
                )
                print(f"[DEBUG] patch: created new submission id={submission.id}")

            submission.checker_remarks = check_remark
            submission.checked_at = timezone.now()
            if check_photo:
                submission.inspector_photo = check_photo

            if option.choice == "P":
                # Mark item and submission completed
                submission.status = "completed"
                item.status = "completed"
                submission.save(update_fields=["checker_remarks", "checked_at", "inspector_photo", "status"])
                item.save(update_fields=["status"])
                print(f"[DEBUG] patch: marked item {item.id} completed")

                # If all checklist items completed, mark checklist completed
                if not checklist.items.exclude(status="completed").exists():
                    checklist.status = "completed"
                    checklist.save(update_fields=["status"])
                    print(f"[DEBUG] patch: checklist {checklist.id} marked completed")

                # Get true_level once and reuse
                true_level = self.get_true_level(checklist.project_id)
                project_id = checklist.project_id
                user_id = request.user.id

                # Build StageHistory filter based on true_level
                stagehistory_filter = {
                    "project": project_id,
                    "is_current": True,
                }
                if true_level == "flat_level":
                    stagehistory_filter["flat"] = checklist.flat_id
                elif true_level == "room_level":
                    stagehistory_filter["room"] = checklist.room_id
                elif true_level == "zone_level":
                    stagehistory_filter["zone"] = checklist.zone_id
                elif true_level == "level_id":
                    stagehistory_filter["level_id"] = checklist.level_id
                elif true_level == "checklist_level":
                    stagehistory_filter["checklist"] = checklist.id

                current_stagehistory = StageHistory.objects.filter(**stagehistory_filter).first()
                if not current_stagehistory:
                    print("[DEBUG] No current StageHistory found for filtering")
                    return Response({"detail": "No current StageHistory found for filtering"}, status=400)

                # Build checklist filter for checklists in current stage/location group
                checklist_filter = {
                    "project_id": project_id,
                    "stage_id": current_stagehistory.stage,
                }
                if true_level == "flat_level":
                    checklist_filter["flat_id"] = checklist.flat_id
                elif true_level == "room_level":
                    checklist_filter["room_id"] = checklist.room_id
                elif true_level == "zone_level":
                    checklist_filter["zone_id"] = checklist.zone_id
                elif true_level == "level_id":
                    checklist_filter["level_id"] = checklist.level_id
                elif true_level == "checklist_level":
                    checklist_filter["id"] = checklist.id

                incomplete_exists = Checklist.objects.filter(**checklist_filter).exclude(status="completed").exists()
                all_checklists_completed = not incomplete_exists
                print(f"[DEBUG] all_checklists_completed = {all_checklists_completed}")

                advanced = False
                advancement_info = None

                if all_checklists_completed:
                    stagehistory_filter = {
                        "project": project_id,
                        "is_current": True,
                    }
                    if true_level == "flat_level":
                        stagehistory_filter["flat"] = checklist.flat_id
                    elif true_level == "room_level":
                        stagehistory_filter["room"] = checklist.room_id
                    elif true_level == "zone_level":
                        stagehistory_filter["zone"] = checklist.zone_id
                    elif true_level == "level_id":
                        stagehistory_filter["level_id"] = checklist.level_id
                    elif true_level == "checklist_level":
                        stagehistory_filter["checklist"] = checklist.id

                    current_stagehistory = StageHistory.objects.filter(**stagehistory_filter).first()
                    if not current_stagehistory:
                        print("[DEBUG] No current StageHistory found")
                        advanced = False
                        advancement_info = "No current StageHistory found"
                    else:
                        next_stage_api = f"https://konstruct.world/projects/stages/{current_stagehistory.stage}/next/"
                        
                        headers = {}
                        auth_header = request.headers.get("Authorization")
                        if auth_header:
                            headers["Authorization"] = auth_header
                        
                        try:
                            print(f"[DEBUG] Calling next stage API: {next_stage_api} with headers: {headers}")
                            resp = requests.get(next_stage_api, headers=headers, timeout=5)
                            print(f"[DEBUG] next stage API response status: {resp.status_code}")
                            print(f"[DEBUG] next stage API response content: {resp.text}")
                            data = resp.json()

                            if data.get("workflow_completed") is True:
                                current_stagehistory.is_current = True
                                current_stagehistory.completed_at = timezone.now()
                                current_stagehistory.completed_by = user_id
                                current_stagehistory.status = "completed"
                                current_stagehistory.save()
                                advanced = True
                                advancement_info = "Workflow fully completed"
                                print("[DEBUG] Workflow fully completed")

                            elif data.get("workflow_completed") is False and "detail" in data:
                                # No stages found in next phase => mark completed
                                current_stagehistory.is_current = False
                                current_stagehistory.completed_at = timezone.now()
                                current_stagehistory.completed_by = user_id
                                current_stagehistory.status = "completed"
                                current_stagehistory.save()
                                advanced = True
                                advancement_info = data["detail"]
                                print(f"[DEBUG] {data['detail']} - Marked current StageHistory completed")

                            elif "next_stage_id" in data and "phase_id" in data:
                                next_stage_id = data["next_stage_id"]
                                next_phase_id = data["phase_id"]

                                # Decide status based on whether phase changed
                                if next_phase_id == current_stagehistory.phase_id:
                                    current_stagehistory.status = "move_to_next_stage"
                                else:
                                    current_stagehistory.status = "move_to_next_phase"

                                current_stagehistory.is_current = False
                                current_stagehistory.completed_at = timezone.now()
                                current_stagehistory.completed_by = user_id
                                current_stagehistory.save()
                                print(f"[DEBUG] Updated StageHistory {current_stagehistory.id} status to {current_stagehistory.status}")

                                try:
                                    new_stagehistory = StageHistory.objects.create(
                                        project=current_stagehistory.project,
                                        phase_id=next_phase_id,
                                        stage=next_stage_id,
                                        started_at=timezone.now(),
                                        is_current=True,
                                        flat=getattr(checklist, "flat_id", None),
                                        room=getattr(checklist, "room_id", None),
                                        zone=getattr(checklist, "zone_id", None),
                                        checklist=checklist if true_level == "checklist_level" else None,
                                        status="started",
                                    )
                                    print(f"[DEBUG] Created new StageHistory id={new_stagehistory.id}")
                                    advanced = True
                                    advancement_info = {
                                        "new_phase_id": next_phase_id,
                                        "new_stage_id": next_stage_id,
                                        "msg": "Advanced to next stage",
                                    }
                                except Exception as e:
                                    print(f"[ERROR] Failed to create new StageHistory: {e}")
                                    advanced = False
                                    advancement_info = f"Failed to create StageHistory: {e}"

                            else:
                                advanced = False
                                advancement_info = data.get("detail", "Invalid next stage/phase data")

                        except Exception as e:
                            advanced = False
                            advancement_info = f"Exception during next stage fetch: {str(e)}"
                            print(f"[ERROR] Exception during next stage fetch: {str(e)}")
                else:
                    advanced = False
                    advancement_info = "Not all checklists are completed"


                # Return response
                return Response({
                    "detail": "Item completed.",
                    "item_id": item.id,
                    "item_status": item.status,
                    "submission_id": submission.id,
                    "submission_status": submission.status,
                    "checklist_status": checklist.status,
                    "stage_advanced": advanced,
                    "advancement_info": advancement_info,
                }, status=200)


            elif option.choice == "N":
                submission.status = "rejected_by_checker"
                submission.save(update_fields=["checker_remarks", "checked_at", "inspector_photo", "status"])
                item.status = "pending_for_maker"
                item.save(update_fields=["status"])
                print(f"[DEBUG] patch: item {item.id} rejected by checker")

                max_attempts = item.submissions.aggregate(max_attempts=models.Max('attempts'))['max_attempts'] or 0
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
                print(f"[DEBUG] patch: checklist {checklist.id} status set to work_in_progress")

                return Response({
                    "detail": "Rejected by checker, sent back to maker.",
                    "item_id": item.id,
                    "item_status": item.status,
                    "checklist_status": checklist.status
                }, status=200)

            else:
                print(f"[DEBUG] patch: invalid option choice for checker: {option.choice}")
                return Response({"detail": "Invalid option value for checker."}, status=400)

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
                print("[DEBUG] patch: no submission found for supervisor action")
                return Response({
                    "detail": (
                        "No submission found for supervisor action. "
                        "This usually means the item hasn't been checked by checker or submitted by maker. "
                        "Please check workflow: Maker must submit, Checker must verify before Supervisor can act."
                    ),
                    "item_id": item.id,
                    "item_status": item.status
                }, status=400)

            if not submission.supervisor_id:
                submission.supervisor_id = request.user.id

            submission.supervisor_remarks = supervisor_remark
            submission.supervised_at = timezone.now()
            if supervisor_photo:
                submission.reviewer_photo = supervisor_photo

            true_level = self.get_true_level(checklist.project_id)
            filter_kwargs = {
                "project_id": checklist.project_id,
                "stage_id": checklist.stage_id,
            }
            if true_level == "flat_level":
                filter_kwargs["flat_id"] = checklist.flat_id
            elif true_level == "room_level":
                filter_kwargs["room_id"] = checklist.room_id
            elif true_level == "zone_level":
                filter_kwargs["zone_id"] = checklist.zone_id
            elif true_level == "level_id":
                filter_kwargs["level_id"] = checklist.level_id
            elif true_level == "checklist_level":
                filter_kwargs["id"] = checklist.id

            print(f"[DEBUG] patch: supervisor filter_kwargs = {filter_kwargs}")

            checklists_in_group = Checklist.objects.filter(**filter_kwargs)

            if option.choice == "P":
                item.status = "tetmpory_inspctor"
                submission.status = "pending_checker"
                item.save(update_fields=["status"])
                submission.save(update_fields=[
                    "supervisor_remarks", "supervised_at", "reviewer_photo", "status", "supervisor_id"
                ])

                group_items = ChecklistItem.objects.filter(checklist__in=checklists_in_group)

                all_ready = all(
                    it.status in ["completed", "tetmpory_inspctor"] for it in group_items
                )
                print(f"[DEBUG] patch: all_ready for inspector = {all_ready}")
                if all_ready:
                    ChecklistItem.objects.filter(
                        checklist__in=checklists_in_group,
                        status="tetmpory_inspctor"
                    ).update(status="pending_for_inspector")

                all_ready = all(
                    it.status in ["completed", "tetmpory_Maker", "tetmpory_inspctor"]
                    for it in group_items
                )
                print(f"[DEBUG] patch: all_ready for maker = {all_ready}")
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

            elif option.choice == "N":
                item.status = "tetmpory_Maker"
                submission.status = "rejected_by_supervisor"
                item.save(update_fields=["status"])
                submission.save(update_fields=[
                    "supervisor_remarks", "supervised_at", "reviewer_photo", "status", "supervisor_id"
                ])

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

                all_ready = all(
                    it.status in ["completed", "tetmpory_inspctor"] for it in group_items
                )
                if all_ready:
                    ChecklistItem.objects.filter(
                        checklist__in=checklists_in_group,
                        status="tetmpory_inspctor"
                    ).update(status="pending_for_inspector")

                all_ready = all(
                    it.status in ["completed", "tetmpory_Maker", "tetmpory_inspctor"]
                    for it in group_items
                )
                if all_ready:
                    ChecklistItem.objects.filter(
                        checklist__in=checklists_in_group,
                        status="tetmpory_Maker"
                    ).update(status="pending_for_maker")

                print(f"[DEBUG] patch: item {item.id} rejected by supervisor and sent back to maker")

                return Response({
                    "detail": "Rejected by supervisor, sent back to maker.",
                    "item_id": item.id,
                    "item_status": item.status,
                    "checklist_status": checklist.status
                }, status=200)

            else:
                print(f"[DEBUG] patch: invalid option value for supervisor: {option.choice}")
                return Response({"detail": "Invalid option value for supervisor."}, status=400)



class FlatReportAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    BASE_PROJECT_API = "https://konstruct.world/projects"
    BASE_USER_API = "https://konstruct.world/users/users"

    def get(self, request, flat_id):
        token = self._get_token(request)

        flat_data = self._get_flat_details(flat_id, token)
        if not flat_data:
            return Response({"error": "Flat not found"}, status=status.HTTP_404_NOT_FOUND)

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









    #             timeout=5,
    #             headers=headers
    #         )
    #         print("User access API response status:", resp.status_code)
    #         if resp.status_code != 200:
    #             print("Could not fetch user access")
    #             return Response({"detail": "Could not fetch user access"}, status=400)
    #         accesses = resp.json()
    #         print("Accesses:", accesses)
    #     except Exception as e:
    #         print("User service error", str(e))
    #         return Response({"detail": "User service error", "error": str(e)}, status=400)

    #     true_level = self.get_true_level(project_id)
    #     print("True Level:", true_level)

    #     base_qs = self.get_checklists_of_current_stage(project_id, true_level, headers, request)
    #     print("Base_qs count after get_checklists_of_current_stage:", base_qs.count())

    #     status_param = request.query_params.get("status")
    #     if status_param:
    #         if "," in status_param:
    #             statuses = [s.strip() for s in status_param.split(",")]
    #             base_qs = base_qs.filter(status__in=statuses)
    #             print(f"Applied status__in filter with: {statuses}")
    #         else:
    #             base_qs = base_qs.filter(status=status_param)
    #             print(f"Applied status filter with: {status_param}")
    #     else:
    #         base_qs = base_qs.filter(status="not_started")
    #         print("No status param provided, filtered by status='not_started'")

    #     print("Base_qs count after status filter:", base_qs.count())

    #     checklist_filter = models.Q()
    #     if flat_id:
    #         checklist_filter &= models.Q(flat_id=flat_id)
    #     elif zone_id:
    #         checklist_filter &= models.Q(zone_id=zone_id, flat_id__isnull=True, room_id__isnull=True)
    #     elif tower_id:
    #         checklist_filter &= models.Q(building_id=tower_id, zone_id__isnull=True, flat_id__isnull=True, room_id__isnull=True)
    #     print("Checklist filter Q object:", checklist_filter)

    #     category_filter = models.Q()
    #     for access in accesses:
    #         if access.get('category'):
    #             category_filter |= self.get_branch_q(access)
    #     print("Category filter Q object:", category_filter)

    #     filtered_qs = base_qs.filter(checklist_filter)
    #     print("Filtered_qs after checklist_filter count:", filtered_qs.count())

    #     if category_filter:
    #         filtered_qs = filtered_qs.filter(category_filter).distinct()
    #         print("Filtered_qs after category_filter count:", filtered_qs.count())
    #     else:
    #         print("No category filter, returning empty queryset")
    #         filtered_qs = Checklist.objects.none()

    #     for c in filtered_qs:
    #         print(f"Final Checklist after all filters: id: {c.id}, flat_id: {c.flat_id}, purpose_id: {c.purpose_id}, stage_id: {c.stage_id}")

    #     return self.paginate_and_group(request, filtered_qs, headers)

    def paginate_and_group(self, request, checklists, headers):
        """
        Generic room-wise (RIS) grouping for checklists, with item and submission expansion.
        """
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

        grouped = defaultdict(lambda: {
            "room_id": None,
            "room_details": None,
            "checklists": []
        })

        for checklist in paginated_checklists:
            room_id = checklist.room_id
            if room_id and room_id in room_details:
                grouped[room_id]["room_details"] = room_details[room_id]
            grouped[room_id]["room_id"] = room_id

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
            grouped[room_id]["checklists"].append(checklist_data)

        response_data = [room_data for room_data in grouped.values() if room_data["checklists"]]
        return paginator.get_paginated_response(response_data)



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

