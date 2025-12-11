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
    ChecklistWithItemsAndPendingSubmissionsSerializer  
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
from collections import defaultdict
from django.db import models
from django.db.models import Q, Exists, OuterRef
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework import status
import requests

from urllib.parse import urlparse, urlunparse


from .models import (
    StageHistory,
    Checklist,
    ChecklistItem,
    ChecklistItemOption,
    ChecklistItemSubmission,
)
from .serializers import (
    ChecklistSerializer,
    ChecklistItemSerializer,
    ChecklistItemOptionSerializer,
    ChecklistItemSubmissionSerializer,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView

from .models import StageHistory
from .serializers import StageHistorySerializer




from django.utils import timezone

# utils.py (or wherever you keep shared helpers)
import requests

def get_project_flags(project_id, headers=None):
    """
    Fetch and normalize project flags from project-service.

    Always returns:
        {
            "skip_supervisory": bool,
            "checklist_repoetory": bool,
            "maker_to_checker": bool,        # <- normalized (handles 'maker_to_chechker' typo)
            "maker_to_chechker": bool,       # mirror for legacy callers (optional)
        }
    """
    def _to_bool(v, default=False):
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return v != 0
        if isinstance(v, str):
            return v.strip().lower() in {"1", "true", "yes", "y", "on"}
        return default

    try:
        url = f"https://{local}/projects/projects/{project_id}/"
        resp = requests.get(url, headers=headers or {}, timeout=5)
        if resp.status_code == 200:
            data = resp.json() or {}

            # Handle multiple spellings (including the API’s typo)
            maker_keys = (
                "maker_to_chechker",   # API response you showed
                "maker_to_checker",
                "Maker_to_chechker",
                "Maker_to_checker",
            )
            maker_val = False
            for k in maker_keys:
                if k in data:
                    maker_val = _to_bool(data.get(k), False)
                    break

            return {
                "skip_supervisory": _to_bool(data.get("skip_supervisory", False)),
                "checklist_repoetory": _to_bool(data.get("checklist_repoetory", False)),
                "maker_to_checker": maker_val,     # normalized
                "maker_to_chechker": maker_val,    # legacy mirror (optional)
            }
    except Exception:
        pass

    return {
        "skip_supervisory": False,
        "checklist_repoetory": False,
        "maker_to_checker": False,
        "maker_to_chechker": False,
    }



# views.py
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
import requests


# class MAker_DOne_view(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     USER_ACCESS_API = f"https://{local}/users/user-access/"

#     # ---------------------------
#     # helpers
#     # ---------------------------
#     def _get_true_level(self, project_id):
#         try:
#             resp = requests.get(
#                 f"https://{local}/projects/transfer-rules/",
#                 params={"project_id": project_id},
#                 timeout=5,
#             )
#             if resp.status_code == 200 and resp.json():
#                 return resp.json()[0].get("true_level")
#         except Exception:
#             pass
#         return None

#     def _group_filters_for_checklist(self, checklist, true_level):
#         """
#         Stage/location filter (project + stage + true_level location).
#         Category gets added via Q in _category_branch_q_from_checklist.
#         """
#         fk = {"project_id": checklist.project_id, "stage_id": checklist.stage_id}
#         if true_level == "flat_level":
#             fk["flat_id"] = checklist.flat_id
#         elif true_level == "room_level":
#             fk["room_id"] = checklist.room_id
#         elif true_level == "zone_level":
#             fk["zone_id"] = checklist.zone_id
#         elif true_level == "level_id":
#             fk["level_id"] = checklist.level_id
#         elif true_level == "checklist_level":
#             fk["id"] = checklist.id
#         return fk

#     def _category_branch_q_from_checklist(self, checklist):
#         """
#         Build a category branch Q using the checklist's own category + levels.
#         """
#         q = Q(category=checklist.category)
#         for i in range(1, 7):
#             v = getattr(checklist, f"category_level{i}", None)
#             if v is not None:
#                 q &= Q(**{f"category_level{i}": v})
#             else:
#                 break
#         return q

#     def _has_all_cat(self, request, user_id, project_id, headers) -> bool:
#         """
#         Return True if any of the user's accesses for this project has all_cat=true.
#         """
#         try:
#             resp = requests.get(
#                 self.USER_ACCESS_API,
#                 params={"user_id": user_id, "project_id": project_id},
#                 headers=headers,
#                 timeout=5,
#             )
#             if resp.status_code == 200:
#                 data = resp.json() or []
#                 # Be tolerant to casing or alternate keys if they ever appear
#                 return any(bool(a.get("all_cat") or a.get("ALL_CAT")) for a in data)
#         except Exception:
#             pass
#         return False

#     # ---------------------------
#     # POST
#     # ---------------------------
#     @transaction.atomic
#     def post(self, request):
#         checklist_item_id = request.data.get("checklist_item_id")
#         maker_remark = request.data.get("maker_remark", "")
#         maker_media = request.FILES.get("maker_media", None)

#         if not checklist_item_id:
#             return Response({"detail": "checklist_item_id required."}, status=400)

#         # 1) Item must be pending_for_maker
#         try:
#             item = ChecklistItem.objects.select_related("checklist").get(
#                 id=checklist_item_id, status="pending_for_maker"
#             )
#         except ChecklistItem.DoesNotExist:
#             return Response(
#                 {"detail": "ChecklistItem not found or not pending for maker."},
#                 status=404,
#             )

#         checklist = item.checklist
#         project_id = checklist.project_id

#         latest_submission = (
#             ChecklistItemSubmission.objects
#             .filter(checklist_item=item, status="created")
#             .order_by("-attempts", "-created_at")
#             .first()
#         )
#         if not latest_submission:
#             return Response(
#                 {"detail": "No matching submission found for rework."},
#                 status=404,
#             )

#         if not latest_submission.maker_id:
#             latest_submission.maker_id = request.user.id

#         headers = {}
#         auth_header = request.headers.get("Authorization")
#         if auth_header:
#             headers["Authorization"] = auth_header  # keep full header as-is

#         # --- flags (normalized)
#         flags = get_project_flags(project_id, headers=headers)
#         skip_super = flags.get("skip_supervisory", False)
#         repo_on = flags.get("checklist_repoetory", False)
#         maker_to_checker = flags.get("maker_to_checker", False)

#         # 2) Update submission + item (immediate statuses)
#         if skip_super:
#             latest_submission.status = "pending_checker"
#             item.status = "tetmpory_inspctor"
#         else:
#             latest_submission.status = "pending_supervisor"
#             item.status = "pending_for_supervisor"

#         latest_submission.maker_remarks = maker_remark
#         latest_submission.maker_at = timezone.now()
#         if maker_media:
#             latest_submission.maker_media = maker_media

#         latest_submission.save(
#             update_fields=["status", "maker_id", "maker_remarks", "maker_media", "maker_at"]
#         )
#         item.save(update_fields=["status"])

#         # 3) Flip to inspector visibility only when BOTH flags are true.
#         #    Scope:
#         #      - If user has all_cat=True ⇒ wait for WHOLE true-level group (all categories)
#         #      - Else ⇒ per-category slice only
#         if skip_super and maker_to_checker:
#             true_level = self._get_true_level(project_id)
#             group_fk = self._group_filters_for_checklist(checklist, true_level)

#             has_all_cat = self._has_all_cat(request, request.user.id, project_id, headers)
#             if has_all_cat:
#                 group_checklists = Checklist.objects.filter(**group_fk)
#             else:
#                 branch_q = self._category_branch_q_from_checklist(checklist)
#                 group_checklists = Checklist.objects.filter(**group_fk).filter(branch_q)

#             # Only expose to checker when the whole scope is ready
#             group_not_ready_for_inspector = ChecklistItem.objects.filter(
#                 checklist__in=group_checklists
#             ).exclude(status__in=["completed", "tetmpory_inspctor"]).exists()

#             if not group_not_ready_for_inspector:
#                 ChecklistItem.objects.filter(
#                     checklist__in=group_checklists,
#                     status="tetmpory_inspctor"
#                 ).update(status="pending_for_inspector")

#             # Re-open temp maker items only when whole scope is in allowed states
#             group_not_ready_for_maker = ChecklistItem.objects.filter(
#                 checklist__in=group_checklists
#             ).exclude(status__in=["completed", "tetmpory_Maker", "tetmpory_inspctor"]).exists()

#             if not group_not_ready_for_maker:
#                 ChecklistItem.objects.filter(
#                     checklist__in=group_checklists,
#                     status="tetmpory_Maker"
#                 ).update(status="pending_for_maker")

#         # 4) Maker_to_checker advancement (true-level scope only)
#         stage_advanced = False
#         advancement_info = None

#         if skip_super and maker_to_checker:
#             try:
#                 true_level = self._get_true_level(project_id)
#                 group_fk_full = self._group_filters_for_checklist(checklist, true_level)

#                 # TRUE-LEVEL scope across ALL categories
#                 group_checklists = Checklist.objects.filter(**group_fk_full)

#                 # condition: no items left in pending_for_maker anywhere in this true-level group
#                 maker_open_exists = ChecklistItem.objects.filter(
#                     checklist__in=group_checklists,
#                     status="pending_for_maker"
#                 ).exists()

#                 if not maker_open_exists:
#                     # resolve current StageHistory row for this location
#                     sh_filter = {"project": project_id, "is_current": True}
#                     if true_level == "flat_level":
#                         sh_filter["flat"] = checklist.flat_id
#                     elif true_level == "room_level":
#                         sh_filter["room"] = checklist.room_id
#                     elif true_level == "zone_level":
#                         sh_filter["zone"] = checklist.zone_id
#                     elif true_level == "level_id":
#                         sh_filter["level_id"] = checklist.level_id
#                     elif true_level == "checklist_level":
#                         sh_filter["checklist"] = checklist.id

#                     current_sh = StageHistory.objects.filter(**sh_filter).first()
#                     if not current_sh:
#                         advancement_info = "No current StageHistory found"
#                     else:
#                         # ask project-service for next stage/phase
#                         next_stage_api = f"https://konstruct.world/projects/stages/{current_sh.stage}/next/"
#                         try:
#                             resp = requests.get(next_stage_api, headers=headers, timeout=5)
#                             data = resp.json()
#                         except Exception as e:
#                             data = {}
#                             advancement_info = f"Exception during next stage fetch: {e}"

#                         if data.get("workflow_completed") is True:
#                             current_sh.is_current = False
#                             current_sh.completed_at = timezone.now()
#                             current_sh.completed_by = request.user.id
#                             current_sh.status = "completed"
#                             current_sh.save()
#                             stage_advanced = True
#                             advancement_info = "Workflow fully completed"

#                         elif "next_stage_id" in data and "phase_id" in data:
#                             next_stage_id = data["next_stage_id"]
#                             next_phase_id = data["phase_id"]

#                             # close current
#                             if next_phase_id == current_sh.phase_id:
#                                 current_sh.status = "move_to_next_stage"
#                             else:
#                                 current_sh.status = "move_to_next_phase"
#                             current_sh.is_current = False
#                             current_sh.completed_at = timezone.now()
#                             current_sh.completed_by = request.user.id
#                             current_sh.save()

#                             # open next
#                             StageHistory.objects.create(
#                                 project=current_sh.project,
#                                 phase_id=next_phase_id,
#                                 stage=next_stage_id,
#                                 started_at=timezone.now(),
#                                 is_current=True,
#                                 flat=getattr(checklist, "flat_id", None),
#                                 room=getattr(checklist, "room_id", None),
#                                 zone=getattr(checklist, "zone_id", None),
#                                 checklist=checklist if true_level == "checklist_level" else None,
#                                 status="started",
#                             )
#                             stage_advanced = True
#                             advancement_info = {
#                                 "new_phase_id": next_phase_id,
#                                 "new_stage_id": next_stage_id,
#                                 "msg": "Advanced to next stage (maker path)",
#                             }

#                             # clone repository for the TRUE-LEVEL group
#                             if repo_on:
#                                 source_group_qs = group_checklists
#                                 if source_group_qs.exists():
#                                     VerifyChecklistItemForCheckerNSupervisorAPIView._clone_group_to_next_stage(
#                                         source_group_qs=source_group_qs,
#                                         next_phase_id=next_phase_id,
#                                         next_stage_id=next_stage_id,
#                                     )
#                         elif data.get("workflow_completed") is False and "detail" in data:
#                             current_sh.is_current = False
#                             current_sh.completed_at = timezone.now()
#                             current_sh.completed_by = request.user.id
#                             current_sh.status = "completed"
#                             current_sh.save()
#                             stage_advanced = True
#                             advancement_info = data["detail"]
#                         else:
#                             advancement_info = data.get("detail", "Invalid next stage/phase data")
#                 else:
#                     advancement_info = "Maker group not complete yet (true-level scope)"
#             except Exception as e:
#                 advancement_info = f"Maker-to-checker advance failed: {e}"

#         # 5) Response
#         item_data = ChecklistItemSerializer(item).data
#         submission_data = {
#             "id": latest_submission.id,
#             "status": latest_submission.status,
#             "maker_remarks": latest_submission.maker_remarks,
#             "maker_media": latest_submission.maker_media.url if latest_submission.maker_media else None,
#             "maker_at": latest_submission.maker_at,
#             "checker_id": latest_submission.checker_id,
#             "maker_id": latest_submission.maker_id,
#             "supervisor_id": latest_submission.supervisor_id,
#         }
#         return Response(
#             {
#                 "item": item_data,
#                 "submission": submission_data,
#                 "detail": "Checklist item marked as done by maker.",
#                 "stage_advanced": stage_advanced,
#                 "advancement_info": advancement_info,
#             },
#             status=200
#         )

#     # ---------------------------
#     # GET (optional)
#     # ---------------------------
#     def get(self, request):
#         user_id = request.user.id
#         queryset = ChecklistItemSubmission.objects.filter(
#             maker_id=user_id,
#             status__in=["created", "pending_supervisor", "pending_checker"]
#         ).order_by("-created_at")
#         serializer = ChecklistItemSubmissionSerializer(
#             queryset, many=True, context={"request": request}
#         )
#         return Response(serializer.data)


class RoleBasedChecklistTRANSFERRULEAPIView(APIView):
    permission_classes = [IsAuthenticated]

    BASE_ROLE_API = f"https://{local}/users"
    USER_ACCESS_API = f"https://{local}/users/user-access/"
    STAGE_HISTORY_API = "https://konstruct.world/checklists/stage-history/"

    ROLE_STATUS_MAP = {
        "checker": ["pending_for_inspector", "completed", "pending_for_maker"],
        "maker": ["pending_for_maker", "tetmpory_inspctor", "completed", "pending_for_supervisor"],
        "supervisor": ["tetmpory_inspctor", "pending_for_supervisor", "completed", "tetmpory_Maker"],
    }

    # ---------------------------
    # Simple debug helper
    # ---------------------------
    def dbg(self, msg, **kw):
        kv = " ".join(f"{k}={repr(v)}" for k, v in kw.items())
        print(f"🟨 RBCTR | {msg} | {kv}")

    # ---------------------------
    # Project flags / roles / rules
    # ---------------------------

    def _compute_stage_note_and_history(self, request, project_id, headers, true_level=None):
        """
        Returns (note:str|None, stage_history:list[dict])

        Logic:
        - Try current row (is_current=True). If it's completed, compute CRM-aware note.
        - If NO current row exists, fall back to the most recent row for this location
        (usually the just-completed one), and compute the same CRM-aware note.
        - If not completed but no next stage ⇒ "Last Stage".
        """
        try:
            if not true_level:
                true_level = self.get_true_level(project_id)

            key, loc_id = self.get_location_for_true_level(request, true_level)
            if not key or not loc_id:
                return (None, [])

            # 1) current row first
            current_rows = self.fetch_stage_history(project_id, headers, key=key, loc_id=loc_id, is_current=True)
            active = None
            rows_out = []

            if current_rows:
                active = current_rows[0]
                rows_out = current_rows
            else:
                # 2) fallback: last completed (or just most recent) row for this location
                last_rows = self.fetch_stage_history(
                    project_id, headers, key=key, loc_id=loc_id, is_current=None, ordering="-completed_at"
                )
                if last_rows:
                    active = last_rows[0]
                    rows_out = [active]
                else:
                    return (None, [])

            status = (active.get("status") or "").lower()
            stage_id = active.get("stage")

            # ---- CRM-aware note for completed rows
            if status == "completed":
                completed_name = (active.get("completed_by_name") or "").strip() or (
                    f"User {active.get('completed_by')}" if active.get("completed_by") else "Someone"
                )
                crm_name = (active.get("crm_completed_by_name") or "").strip()
                crm_by   = active.get("crm_completed_by")
                crm_hoto = active.get("crm_hoto")
                crm_date = active.get("crm_date")

                crm_done = bool(crm_hoto or crm_date or crm_name or crm_by)

                if crm_done:
                    who = crm_name or (f"User {crm_by}" if crm_by else "Someone")
                    if crm_date:
                        return (f"Completed by {completed_name} — Handover done by {who} on {crm_date}", rows_out)
                    return (f"Completed by {completed_name} — Handover done by {who}", rows_out)

                # no CRM yet
                return (f"Completed by {completed_name} — Handover not done", rows_out)

            # ---- Not completed: check if there's a next stage to decide "Last Stage"
            try:
                next_stage_api = f"https://konstruct.world/projects/stages/{int(stage_id)}/next/"
                resp = requests.get(next_stage_api, headers=headers or {}, timeout=5)
                data = resp.json() if resp.status_code == 200 else {}
            except Exception:
                data = {}

            if data.get("workflow_completed") is True or ("next_stage_id" not in data and "phase_id" not in data):
                return ("Last Stage", rows_out)

            return (None, rows_out)

        except Exception:
            return (None, [])

    def _crm_gate(self, request, sh: dict) -> bool:
        """
        Only the finisher sees a non-null crm_stagehistory_id
        while CRM is still empty on the completed StageHistory row.
        """
        status = (sh.get("status") or "").lower()
        crm_empty = not (sh.get("crm_hoto") or sh.get("crm_date") or sh.get("crm_completed_by"))
        return (
            status == "completed"
            and crm_empty
            and sh.get("completed_by") == getattr(request.user, "id", None)
        )

    def _attach_crm_meta(self, response, request, note=None, sh_rows=None):
        """
        Adds:
        response.data["stagehistory_meta"] = {
            "current_id": <id or None>,
            "last_id":    <id or None>,
            "last_status": "...",
            "completed_by": <user_id or None>,
            "completed_by_name": "...",
            "crm": {
            "done": <bool>,
            "by": <user_id or None>,
            "by_name": "...",
            "date": <ISO or None>,
            "hoto": <bool or None>
            },
            "my_completed_stagehistory_id": <id only if request.user completed the last row>
        }
        And, if `note` is empty and we can deduce one, sets a sensible CRM/“handover” note.
        """
        try:
            project_id = int(request.query_params.get("project_id"))
            true_level = self.get_true_level(project_id)
            key, loc_id = self.get_location_for_true_level(request, true_level)
            if not key or not loc_id:
                return response

            # find current and last rows for this location
            current_rows = self.fetch_stage_history(project_id, key=key, loc_id=loc_id, is_current=True)
            last_rows = self.fetch_stage_history(project_id, key=key, loc_id=loc_id,
                                                is_current=None, ordering=("-completed_at",))
            current = current_rows[0] if current_rows else None
            last = last_rows[0] if last_rows else None

            meta = {
                "current_id": current.get("id") if current else None,
                "last_id": last.get("id") if last else None,
                "last_status": (last.get("status") if last else None),
                "completed_by": (last.get("completed_by") if last else None),
                "completed_by_name": (last.get("completed_by_name") if last else None),
                "crm": {
                    "done": bool(last and (last.get("crm_hoto") or last.get("crm_date") or
                                        last.get("crm_completed_by") or (last.get("crm_completed_by_name") or "").strip())),
                    "by": (last.get("crm_completed_by") if last else None),
                    "by_name": (last.get("crm_completed_by_name") if last else None),
                    "date": (last.get("crm_date") if last else None),
                    "hoto": (last.get("crm_hoto") if last else None),
                },
            }

            # Only the user who completed sees the concrete id for “their” completion
            if last and last.get("completed_by") == request.user.id:
                meta["my_completed_stagehistory_id"] = last["id"]

            response.data["stagehistory_meta"] = meta

            # If caller didn’t set a note, fill a good one from last row
            if not response.data.get("note") and last and (last.get("status") or "").lower() == "completed":
                completed_name = (last.get("completed_by_name") or f"User {last.get('completed_by')}" if last.get("completed_by") else "Someone")
                if meta["crm"]["done"]:
                    who = meta["crm"]["by_name"] or (f"User {meta['crm']['by']}" if meta["crm"]["by"] else "Someone")
                    if meta["crm"]["date"]:
                        response.data["note"] = f"Completed by {completed_name} — Handover done by {who} on {meta['crm']['date']}"
                    else:
                        response.data["note"] = f"Completed by {completed_name} — Handover done by {who}"
                else:
                    response.data["note"] = f"Completed by {completed_name} — Handover not done"

        except Exception as e:
            self.dbg("_attach_crm_meta_err", err=str(e))
        return response

    def _rewrite_paginator_links(self, response):
        """
        Force https + /checklists base for DRF pagination links.
        Only touches 'next' and 'previous'; preserves the querystring.
        """
        def _fix(url):
            if not url:
                return url
            u = urlparse(url)
            desired_path = "/checklists/Transafer-Rule-getchchklist/"
            return urlunparse(("https", "konstruct.world", desired_path, u.params, u.query, u.fragment))

        try:
            if isinstance(response.data, dict):
                if "next" in response.data:
                    response.data["next"] = _fix(response.data["next"])
                if "previous" in response.data:
                    response.data["previous"] = _fix(response.data["previous"])
        except Exception as e:
            self.dbg("paginate_rewrite_err", err=str(e))
        return response

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
            role = resp.json().get("role")
            self.dbg("get_user_role", role=role)
            return role
        self.dbg("get_user_role_failed", status=resp.status_code, text=resp.text[:200])
        return None

    def get_true_level(self, project_id):
        TRANSFER_RULE_API = f"https://{local}/projects/transfer-rules/"
        try:
            resp = requests.get(TRANSFER_RULE_API, params={"project_id": project_id}, timeout=5)
            if resp.status_code == 200 and resp.json():
                tl = resp.json()[0].get("true_level")
                self.dbg("get_true_level", project_id=project_id, true_level=tl)
                return tl
        except Exception as e:
            print("TransferRule error:", e)
        self.dbg("get_true_level_none", project_id=project_id)
        return None

    # ---------------------------
    # Purpose / Phases / Stages
    # ---------------------------

    def get_current_purpose(self, project_id, headers):
        try:
            url = f"https://{local}/projects/projects/{project_id}/activate-purpose/"
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                purpose_data = resp.json()
                self.dbg("get_current_purpose_resp",
                         status=resp.status_code,
                         purpose_id=purpose_data.get("id"),
                         is_current=purpose_data.get("is_current"))
                if purpose_data.get("is_current"):
                    return purpose_data
            self.dbg("get_current_purpose_not_current", status=resp.status_code)
            return None
        except Exception as e:
            print(f"Error fetching current purpose: {e}")
            return None

    def get_phases(self, project_id, headers):
        try:
            url = f"https://{local}/projects/phases/by-project/{project_id}/"
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                self.dbg("get_phases_ok", count=len(data))
                return data
            self.dbg("get_phases_fail", status=resp.status_code)
            return []
        except Exception as e:
            print(f"Error fetching phases: {e}")
            return []

    def get_stages(self, project_id, headers):
        try:
            url = f"https://{local}/projects/get-stage-details-by-project-id/{project_id}/"
            resp = requests.get(url, headers=headers, timeout=5)
        # NOTE: no change needed to stages for gate
            if resp.status_code == 200:
                data = resp.json()
                self.dbg("get_stages_ok", count=len(data))
                return data
            self.dbg("get_stages_fail", status=resp.status_code)
            return []
        except Exception as e:
            print(f"Error fetching stages: {e}")
            return []

    def get_or_create_stage_history(self, project_id, phases, stages,
                                    zone_id=None, flat_id=None, room_id=None, current_purpose_id=None):
        """
        Location-based StageHistory (no category in Option A).
        """
        try:
            filters = {"project": project_id, "is_current": True}
            if flat_id is not None:
                filters["flat"] = flat_id
            if room_id is not None:
                filters["room"] = room_id
            if zone_id is not None:
                filters["zone"] = zone_id
            self.dbg("StageHistory_lookup", filters=filters)

            stage_history = StageHistory.objects.filter(**filters).first()
            if stage_history:
                self.dbg("StageHistory_found",
                         stage=stage_history.stage,
                         phase_id=getattr(stage_history, "phase_id", None))
                return stage_history.stage

            if not phases or not stages:
                self.dbg("StageHistory_no_phases_or_stages")
                return None

            purpose_phases = [
                p for p in phases
                if (p.get('purpose') and (
                    p.get('purpose').get('id') if isinstance(p.get('purpose'), dict) else p.get('purpose'))
                    == current_purpose_id)
            ]
            self.dbg("StageHistory_purpose_phases",
                     count=len(purpose_phases), current_purpose_id=current_purpose_id)
            if not purpose_phases:
                return None

            lowest_phase = min(purpose_phases, key=lambda x: x.get('sequence', 0))
            phase_stages = [s for s in stages if s.get('phase') == lowest_phase['id']]
            if not phase_stages:
                self.dbg("StageHistory_no_phase_stages", lowest_phase=lowest_phase['id'])
                return None

            lowest_stage = min(phase_stages, key=lambda x: x.get('sequence', 0))
            StageHistory.objects.create(
                project=project_id,
                zone=zone_id,
                phase_id=lowest_phase['id'],
                flat=flat_id,
                room=room_id,
                stage=lowest_stage['id'],
                is_current=True
            )
            self.dbg("StageHistory_created", phase_id=lowest_phase['id'], stage_id=lowest_stage['id'])
            return lowest_stage['id']
        except Exception as e:
            print(f"Error in get_or_create_stage_history: {e}")
            return None

    # ---------------------------
    # UserAccess helpers (Option A + stage-gate)
    # ---------------------------

    def get_user_accesses(self, request, user_id, project_id, headers):
        """
        Pulls user-access list. On failure, returns [] (no filter).
        """
        try:
            resp = requests.get(
                self.USER_ACCESS_API,
                params={"user_id": user_id, "project_id": project_id},
                headers=headers,
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json() or []
                self.dbg("get_user_accesses_ok", count=len(data))
                return data
        except Exception as e:
            print("User access fetch error:", e)
        self.dbg("get_user_accesses_fail")
        return []

    @staticmethod
    def access_has_all_checklist(accesses):
        return any(bool(a.get("All_checklist")) for a in (accesses or []))

    STAGE_INFO_API = "https://konstruct.world/projects/stages/{stage_id}/info/"

    def _get_stage_info(self, stage_id, headers=None):
        """Fetch rich stage info; always return a dict with at least stage_id."""
        info = {"stage_id": stage_id}
        if not stage_id:
            return info
        try:
            url = self.STAGE_INFO_API.format(stage_id=int(stage_id))
            resp = requests.get(url, headers=headers or {}, timeout=5)
            if resp.status_code == 200 and isinstance(resp.json(), dict):
                info.update(resp.json())
        except Exception:
            pass
        return info

    def _format_stage_label(self, info):
        """
        Build a readable label like:
        'Project (Phase: Flat Posession Checklists, Purpose: Snagging)'
        falling back to 'Stage 14' if names are missing.
        """
        name = info.get("stage_name") or f"Stage {info.get('stage_id')}"
        phase = info.get("phase_name")
        purpose = info.get("purpose_name")
        extras = []
        if phase:
            extras.append(f"Phase: {phase}")
        if purpose:
            extras.append(f"Purpose: {purpose}")
        return f'{name} ({", ".join(extras)})' if extras else name


    @staticmethod
    def first_assigned_stage_id(accesses):
        for a in accesses or []:
            sid = a.get("stage_id")
            if sid is not None:
                try:
                    return int(sid)
                except Exception:
                    continue
        return None

    @staticmethod
    def stage_history_param_key(true_level):
        return {
            "flat_level": "flat",
            "room_level": "room",
            "zone_level": "zone",
        }.get(true_level)

    def get_location_for_true_level(self, request, true_level):
        key = self.stage_history_param_key(true_level)
        if not key:
            return (None, None)
        qp_key = f"{key}_id"
        return (key, self.safe_nt(request.query_params.get(qp_key)))


    def fetch_stage_history(self, project_id, headers=None, key=None, loc_id=None,
                            is_current=None, ordering=None):
        try:
            filters = {"project": int(project_id)}
            if key and loc_id:
                filters[key] = loc_id
            if is_current is not None:
                filters["is_current"] = bool(is_current)

            self.dbg("fetch_stage_history_db", filters=filters)
            qs = StageHistory.objects.filter(**filters)

            # ✅ Accept "field1,field2" or ("field1","field2") etc.
            if ordering:
                try:
                    if isinstance(ordering, (list, tuple)):
                        qs = qs.order_by(*ordering)
                    elif isinstance(ordering, str):
                        parts = [p.strip() for p in ordering.split(",") if p.strip()]
                        if parts:
                            qs = qs.order_by(*parts)
                except Exception as e:
                    self.dbg("fetch_stage_history_order_err", err=str(e))
                    # fall through without ordering

            result = [
                {
                    "id": sh.id,
                    "project": sh.project,
                    "stage": sh.stage,
                    "phase_id": sh.phase_id,
                    "flat": sh.flat,
                    "zone": sh.zone,
                    "room": sh.room,
                    "is_current": sh.is_current,
                    "status": sh.status,
                    "started_at": sh.started_at,
                    "completed_at": sh.completed_at,
                    "completed_by": sh.completed_by,
                    "completed_by_name": getattr(sh, "completed_by_name", None),
                    "crm_hoto": getattr(sh, "crm_hoto", None),
                    "crm_date": getattr(sh, "crm_date", None),
                    "crm_completed_by": getattr(sh, "crm_completed_by", None),
                    "crm_completed_by_name": getattr(sh, "crm_completed_by_name", None),
                }
                for sh in qs
            ]
            return result

        except Exception as e:
            self.dbg("fetch_stage_history_err", err=str(e))
            return []



    def empty_paginated_with_stage_history(self, request, stage_history, note=None):
        """
        Build an empty paginated response but include `stage_history` (and optional note).
        """
        paginator = LimitOffsetPagination()
        paginator.default_limit = 10
        paginated = paginator.paginate_queryset([], request, view=self)
        response = paginator.get_paginated_response(paginated)
        response.data["stage_history"] = stage_history
        if note:
            response.data["note"] = note
        return self._rewrite_paginator_links(response)

    def stage_gate_precheck(self, request, project_id, headers, true_level, accesses):
        """
        Returns (allowed: bool, Response or None).

        Policy:
          - If All_checklist=True in any access -> allow.
          - Else find assigned stage_id:
              - If missing -> BLOCK with empty results + stage_history + "No stage assigned to your access."
              - Else compare with current StageHistory(stage) at this location:
                  - If != -> BLOCK with empty results + stage_history + note "Current stage is X; your access is Y."
                  - If == -> allow.
        """
        if self.access_has_all_checklist(accesses):
            self.dbg("stage_gate", reason="all_checklist_true -> allow")
            return True, None

        assigned_stage_id = self.first_assigned_stage_id(accesses)
        key, loc_id = self.get_location_for_true_level(request, true_level)

        if assigned_stage_id is None:
            history = self.fetch_stage_history(project_id, headers, key, loc_id, is_current=None, ordering="stage,started_at")
            self.dbg("stage_gate", reason="no_assigned_stage_in_access -> block")
            return False, self.empty_paginated_with_stage_history(
                request, history, note="No stage assigned to your access."
            )

        if not key or not loc_id:
            self.dbg("stage_gate", reason="no_location_id -> allow", true_level=true_level)
            return True, None

        current_rows = self.fetch_stage_history(project_id, headers, key, loc_id, is_current=True)
# no_current_row -> block
        if not current_rows:
            history = self.fetch_stage_history(project_id, headers, key, loc_id, is_current=None, ordering=("stage", "started_at"))
            assigned_info = self._get_stage_info(assigned_stage_id, headers)
            assigned_label = self._format_stage_label(assigned_info)

            resp = self.empty_paginated_with_stage_history(
                request, history, note=f"Current stage unavailable; your access is {assigned_label}."
            )
            # Replace/augment note with CRM-aware one and attach meta
            note2, sh2 = self._compute_stage_note_and_history(request, project_id, headers, true_level=true_level)
            if sh2: resp.data["stage_history"] = sh2
            if note2: resp.data["note"] = note2
            self._attach_crm_meta(resp, request, note2, sh2)
            return False, resp


        current_stage = int(current_rows[0].get("stage"))
        self.dbg("stage_gate_compare", assigned_stage_id=assigned_stage_id, current_stage=current_stage)

        if current_stage == int(assigned_stage_id):
            return True, None

        history = self.fetch_stage_history(project_id, headers, key, loc_id, is_current=None, ordering="stage,started_at")
        current_info = self._get_stage_info(current_stage, headers)
        assigned_info = self._get_stage_info(assigned_stage_id, headers)
        current_label = self._format_stage_label(current_info)
        assigned_label = self._format_stage_label(assigned_info)
        note = f"Current stage is {current_label}; your access is for {assigned_label}."

        self.dbg("stage_gate", reason="mismatch -> block")
        return False, self.empty_paginated_with_stage_history(request, history, note=note)

    # ---------------------------
    # Category helpers (Option A)
    # ---------------------------

    @staticmethod
    def get_branch_q(access):
        """
        Builds a single-branch Q from an access dict:
          {category, CategoryLevel1..6}
        """
        q = Q()
        if access.get('category') is not None:
            q &= Q(category=access.get('category'))
        for i in range(1, 7):
            key = f'CategoryLevel{i}'
            val = access.get(key)
            if val is not None:
                q &= Q(**{f'category_level{i}': val})
            else:
                break
        return q

    def build_category_q(self, request, accesses):
        """
        If query params provide category/category_level*, intersect with access unless all_cat=True.
        Otherwise, use access union. If user has all_cat=True, don't narrow by category unless
        they explicitly pass params (then honor those).
        """
        param_category = request.query_params.get("category") or request.query_params.get("category_id")
        keys = ["category", "category_id"] + [f"category_level{i}" for i in range(1, 7)]
        has_params = any(k in request.query_params for k in keys)

        # Build Q from query params (if any)
        param_q = Q()
        if has_params:
            try:
                if param_category is not None:
                    param_q &= Q(category=int(param_category))
                for i in range(1, 7):
                    k = f"category_level{i}"
                    v = request.query_params.get(k)
                    if v not in (None, ""):
                        param_q &= Q(**{k: int(v)})
            except Exception:
                # bad input? don't 500; return no narrowing
                return Q()

        # If any access has all_cat=True => pass-through (no narrowing), but still allow user to
        # voluntarily narrow with query params.
        if any(bool(a.get("all_cat")) for a in (accesses or [])):
            return param_q if has_params else Q()

        # Build union of allowed branches from accesses
        union_q = Q()
        added = False
        for acc in accesses or []:
            if acc.get("category") is None:
                continue
            branch = Q(category=acc.get("category"))
            for i in range(1, 7):
                key = f"CategoryLevel{i}"
                val = acc.get(key)
                if val is not None:
                    branch &= Q(**{f"category_level{i}": val})
                else:
                    break
            union_q |= branch
            added = True

        if not added:
            # user has no category rights; if they explicitly asked for a category, return empty
            return Q() if not has_params else Q(pk__in=[])

        # If params provided, intersect with allowed branches; else just return the allowed union
        return (union_q & param_q) if has_params else union_q
    # ---------------------------
    # Core checklist fetchers
    # ---------------------------

    def get_checklists_of_current_stage(self, project_id, true_level, headers, request):
        """
        Returns all checklists for current purpose & stage at the filterable location
        (no category applied here; category will be applied by caller).
        """
        self.dbg("GCCS_enter", project_id=project_id, true_level=true_level, qp=dict(request.query_params))

        current_purpose = self.get_current_purpose(project_id, headers)
        if not current_purpose:
            self.dbg("GCCS_no_current_purpose")
            return Checklist.objects.none()

        purpose_id = current_purpose["id"]
        phases = self.get_phases(project_id, headers)
        stages = self.get_stages(project_id, headers)
        if not phases or not stages:
            self.dbg("GCCS_no_phases_or_stages")
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
        self.dbg("GCCS_location", **location)

        stage_id = self.get_or_create_stage_history(
            project_id, phases, stages,
            zone_id=location.get("zone_id"),
            flat_id=location.get("flat_id"),
            room_id=location.get("room_id"),
            current_purpose_id=purpose_id
        )
        self.dbg("GCCS_stage_resolved", stage_id=stage_id, purpose_id=purpose_id)
        if not stage_id:
            return Checklist.objects.none()

        checklist_filter = Q(project_id=project_id, purpose_id=purpose_id, stage_id=stage_id)
        if true_level == "flat_level":
            checklist_filter &= Q(flat_id=location["flat_id"])
        elif true_level == "room_level":
            checklist_filter &= Q(room_id=location["room_id"])
        elif true_level == "zone_level":
            checklist_filter &= Q(zone_id=location["zone_id"])

        qs = Checklist.objects.filter(checklist_filter)
        self.dbg("GCCS_base_qs",
                 count=qs.count(),
                 ids=list(qs.values_list("id", flat=True)),
                 names=list(qs.values_list("name", flat=True)))
        return qs

    def all_items_have_status(self, checklists, allowed_statuses):
        """
        Returns list of checklists for which ALL items ∈ allowed_statuses.
        """
        filtered = []
        for checklist in checklists:
            items = ChecklistItem.objects.filter(checklist=checklist)
            item_count = items.count()
            valid_count = items.filter(status__in=allowed_statuses).count()
            self.dbg("all_items_have_status_scan",
                     checklist_id=checklist.id, item_count=item_count, valid_count=valid_count)
            if item_count > 0 and item_count == valid_count:
                filtered.append(checklist)
        return filtered

    def filter_by_level(self, checklists, allowed_statuses, true_level, project_id, headers, category_q=None):
        """
        Applies true_level grouping and checks "all items in allowed_statuses" per location group.
        Category filter is included in group selection (Option A).
        """
        self.dbg("filter_by_level_enter",
                 true_level=true_level, qs_count=checklists.count(), allowed_statuses=allowed_statuses)
        qs = Checklist.objects.none()

        if true_level == "checklist_level":
            base = checklists.filter(category_q) if category_q else checklists
            filtered = self.all_items_have_status(base, allowed_statuses)
            self.dbg("filter_by_level_checklist_level",
                     base_count=base.count(), filtered_ids=[c.id for c in filtered])
            return base.filter(id__in=[c.id for c in filtered])

        if true_level in ["flat_level", "room_level", "zone_level"]:
            location_field = {
                "flat_level": "flat_id",
                "room_level": "room_id",
                "zone_level": "zone_id"
            }.get(true_level)

            locations = list(checklists.values_list(location_field, flat=True).distinct())
            self.dbg("filter_by_level_locations", field=location_field, locations=locations)

            current_purpose = self.get_current_purpose(project_id, headers)
            if not current_purpose:
                return Checklist.objects.none()
            purpose_id = current_purpose["id"]
            phases = self.get_phases(project_id, headers)
            stages = self.get_stages(project_id, headers)

            for loc_id in locations:
                if loc_id is None:
                    continue

                stage_id = self.get_or_create_stage_history(
                    project_id,
                    phases=phases,
                    stages=stages,
                    zone_id=loc_id if true_level == "zone_level" else None,
                    flat_id=loc_id if true_level == "flat_level" else None,
                    room_id=loc_id if true_level == "room_level" else None,
                    current_purpose_id=purpose_id
                )
                if not stage_id:
                    self.dbg("filter_by_level_no_stage_for_loc", loc_id=loc_id)
                    continue

                filters = {
                    location_field: loc_id,
                    "project_id": project_id,
                    "purpose_id": purpose_id,
                    "stage_id": stage_id,
                }
                group_checklists = Checklist.objects.filter(**filters)
                if category_q:
                    group_checklists = group_checklists.filter(category_q)

                ok_len = len(self.all_items_have_status(group_checklists, allowed_statuses))
                self.dbg("filter_by_level_group",
                         loc_id=loc_id, group_count=group_checklists.count(), ok_count=ok_len)
                if ok_len == group_checklists.count() and group_checklists.count() > 0:
                    qs = qs.union(group_checklists)

            self.dbg("filter_by_level_result", result_count=qs.count())
            return qs.distinct()

        return Checklist.objects.none()
    # ---------------------------
    # Completeness helpers for response
    # ---------------------------
    def compute_group_complete(self, group_checklists, allowed_statuses):
        """
        True if group_checklists exist AND each checklist has all items ∈ allowed_statuses.
        """
        if not group_checklists.exists():
            return False
        ok = self.all_items_have_status(group_checklists, allowed_statuses)
        return group_checklists.count() == len(ok)

    def compute_room_group_complete(self, project_id, purpose_id, stage_id,
                                    true_level, loc_id, allowed_statuses, category_q):
        """
        Build the exact group (location + purpose + stage [+ category]) and
        compute completeness on it.
        """
        field_map = {"flat_level": "flat_id", "room_level": "room_id", "zone_level": "zone_id"}
        lf = field_map.get(true_level)
        if not lf or loc_id is None:
            return False
        filters = {
            "project_id": project_id,
            "purpose_id": purpose_id,
            "stage_id": stage_id,
            lf: loc_id,
        }
        group_qs = Checklist.objects.filter(**filters)
        if category_q:
            group_qs = group_qs.filter(category_q)
        return self.compute_group_complete(group_qs, allowed_statuses)
    # ---------------------------
    # Utils
    # ---------------------------
    def safe_nt(self, val):
        if val is None:
            return None
        try:
            return int(str(val).strip("/"))
        except Exception:
            return None

    # ---------------------------
    # Role handlers
    # ---------------------------

    def get(self, request):
        user_id = request.user.id
        project_id = request.query_params.get("project_id")
        self.dbg("GET_entry", user_id=user_id, project_id=project_id, qp=dict(request.query_params))

        if not user_id or not project_id:
            return Response({"detail": "user_id and project_id required"}, status=400)

        role = self.get_user_role(request, user_id, project_id)
        if not role:
            return Response({"detail": "Could not determine role"}, status=403)
        print(f"🔍 BACKEND DEBUG - Detected Role: {role} for User: {user_id}")

        role_upper = role.upper()
        if role == "Intializer":
            return self.handle_intializer(request, user_id, project_id)
        elif role_upper == "SUPERVISOR":
            return self.handle_supervisor(request, user_id, project_id)
        elif role_upper == "CHECKER":
            return self.handle_checker(request, user_id, project_id)
        elif role_upper == "MAKER":
            return self.handle_maker(request, user_id, project_id)
        elif role.lower() in ("manager", "client"):
            return self.handle_manager_client(request, user_id, project_id)
        else:
            return Response({"detail": f"Role '{role}' not supported"}, status=400)

    # ---------- Initializer (NO category filter) ----------

    def handle_intializer(self, request, user_id, project_id):
        """
        Same as before — NO category filter for initializer. Sees all checklists.
        """
        USER_SERVICE_URL = f"https://{local}/users/user-access/"
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        tower_id = self.safe_nt(request.query_params.get("tower_id"))
        flat_id = self.safe_nt(request.query_params.get("flat_id"))
        zone_id = self.safe_nt(request.query_params.get("zone_id"))
        self.dbg("initializer_params", tower_id=tower_id, flat_id=flat_id, zone_id=zone_id)

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
            self.dbg("initializer_user_accesses", count=len(accesses))
        except Exception as e:
            return Response({"detail": "User service error", "error": str(e)}, status=400)

        true_level = self.get_true_level(project_id)
        base_qs = self.get_checklists_of_current_stage(project_id, true_level, headers, request)
        self.dbg("initializer_base_qs",
                 count=base_qs.count(),
                 ids=list(base_qs.values_list("id", flat=True)),
                 names=list(base_qs.values_list("name", flat=True)))

        checklist_filter = Q()
        if flat_id:
            checklist_filter &= Q(flat_id=flat_id)
        elif zone_id:
            checklist_filter &= Q(zone_id=zone_id, flat_id__isnull=True, room_id__isnull=True)
        elif tower_id:
            checklist_filter &= Q(building_id=tower_id, zone_id__isnull=True, flat_id__isnull=True, room_id__isnull=True)

        filtered_qs = base_qs.filter(checklist_filter)
        self.dbg("initializer_after_location_filter",
                 count=filtered_qs.count(),
                 ids=list(filtered_qs.values_list("id", flat=True)),
                 names=list(filtered_qs.values_list("name", flat=True)))

        status_param = request.query_params.get("status")
        if status_param:
            if "," in status_param:
                statuses = [s.strip() for s in status_param.split(",")]
                filtered_qs = filtered_qs.filter(status__in=statuses).distinct()
                self.dbg("initializer_status_filter_list", statuses=statuses, count=filtered_qs.count())
            else:
                filtered_qs = filtered_qs.filter(status=status_param).distinct()
                self.dbg("initializer_status_filter_single", status=status_param, count=filtered_qs.count())
        else:
            filtered_qs = filtered_qs.filter(status="not_started").distinct()
            self.dbg("initializer_default_status_filter", status="not_started", count=filtered_qs.count())

        return self.paginate_and_group(request, filtered_qs, headers)

    # ---------- Checker ----------

    def handle_checker(self, request, user_id, project_id):
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        true_level = self.get_true_level(project_id)
        accesses = self.get_user_accesses(request, user_id, project_id, headers)

        # Stage gate
        allowed, early = self.stage_gate_precheck(request, project_id, headers, true_level, accesses)
        if not allowed:
            return early

        base_qs = self.get_checklists_of_current_stage(project_id, true_level, headers, request)

        category_q = self.build_category_q(request, accesses)
        base_qs = base_qs.filter(category_q) if category_q else base_qs

        allowed_statuses = self.ROLE_STATUS_MAP.get("checker", [])
        filtered_checklists = self.filter_by_level(base_qs, allowed_statuses, true_level, project_id, headers, category_q)

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
        assigned_to_me = filtered_checklists.annotate(has_assigned=Exists(assigned_item_exists)).filter(has_assigned=True)
        available_for_me = filtered_checklists.annotate(has_available=Exists(available_item_exists)).filter(has_available=True)

        assigned_ids = set(c.id for c in assigned_to_me)
        available_for_me = [c for c in available_for_me if c.id not in assigned_ids]

        return self.paginate_and_group_checker(
            request, assigned_to_me, available_for_me, headers,
            true_level=true_level, allowed_statuses=allowed_statuses,
            category_q=category_q
        )

    # ---------- Supervisor ----------

    def handle_supervisor(self, request, user_id, project_id):
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        true_level = self.get_true_level(project_id)
        accesses = self.get_user_accesses(request, user_id, project_id, headers)

        # Stage gate
        allowed, early = self.stage_gate_precheck(request, project_id, headers, true_level, accesses)
        if not allowed:
            return early

        if self.get_project_skip_supervisory(project_id, headers=headers):
            return self.paginate_and_group_supervisor(
                request, [], [], headers,
                true_level=true_level,
                allowed_statuses=self.ROLE_STATUS_MAP["supervisor"],
                category_q=Q()
            )

        base_qs = self.get_checklists_of_current_stage(project_id, true_level, headers, request)

        category_q = self.build_category_q(request, accesses)
        base_qs = base_qs.filter(category_q) if category_q else base_qs

        allowed_statuses = self.ROLE_STATUS_MAP["supervisor"]
        filtered_checklists = self.filter_by_level(base_qs, allowed_statuses, true_level, project_id, headers, category_q)

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

        return self.paginate_and_group_supervisor(
            request, assigned_to_me, available_for_me, headers,
            true_level=true_level, allowed_statuses=allowed_statuses,
            category_q=category_q
        )

    # ---------- Maker ----------

    def handle_maker(self, request, user_id, project_id):
        true_level = self.get_true_level(project_id)
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        accesses = self.get_user_accesses(request, user_id, project_id, headers)

        # Stage gate
        allowed, early = self.stage_gate_precheck(request, project_id, headers, true_level, accesses)
        if not allowed:
            return early

        checklist_qs = self.get_checklists_of_current_stage(project_id, true_level, headers, request)

        category_q = self.build_category_q(request, accesses)
        checklist_qs = checklist_qs.filter(category_q) if category_q else checklist_qs

        skip_super = self.get_project_skip_supervisory(project_id, headers=headers)
        allowed_statuses = ["pending_for_maker", "tetmpory_inspctor", "completed"] if skip_super else self.ROLE_STATUS_MAP["maker"]

        filtered_checklists = self.filter_by_level(checklist_qs, allowed_statuses, true_level, project_id, headers, category_q)
        if not filtered_checklists.exists():
            return self.paginate_and_group_supervisor(
                request, [], [], headers,
                true_level=true_level, allowed_statuses=allowed_statuses,
                category_q=category_q
            )

        assigned_item_exists = ChecklistItem.objects.filter(
            checklist=OuterRef('pk'),
            status="pending_for_maker",
            submissions__maker_id=user_id,
            submissions__status="created"
        )
        available_item_exists = ChecklistItem.objects.filter(
            checklist=OuterRef('pk'),
            status="pending_for_maker",
            submissions__maker_id__isnull=True
        )
        assigned_to_me = filtered_checklists.annotate(has_assigned=Exists(assigned_item_exists)).filter(has_assigned=True)
        available_for_me = filtered_checklists.annotate(has_available=Exists(available_item_exists)).filter(has_available=True)

        assigned_ids = set(c.id for c in assigned_to_me)
        available_for_me = [c for c in available_for_me if c.id not in assigned_ids]

        return self.paginate_and_group_maker(
            request, assigned_to_me, available_for_me, headers,
            true_level=true_level, allowed_statuses=allowed_statuses,
            category_q=category_q
        )

    def handle_manager_client(self, request, user_id, project_id):
        true_level = self.get_true_level(project_id)
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        accesses = self.get_user_accesses(request, user_id, project_id, headers)

        # Stage gate
        allowed, early = self.stage_gate_precheck(request, project_id, headers, true_level, accesses)
        if not allowed:
            return early

        base_qs = self.get_checklists_of_current_stage(project_id, true_level, headers, request)

        paginator = LimitOffsetPagination()
        paginator.default_limit = 10
        paginated_checklists = paginator.paginate_queryset(base_qs, request, view=self)

        data = []
        for checklist in paginated_checklists:
            checklist_data = {
                "id": checklist.id,
                "title": getattr(checklist, "title", None) or checklist.name,
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
        response = paginator.get_paginated_response(data)
        return self._rewrite_paginator_links(response)

    # ---------------------------
    # Grouping / pagination builders
    # ---------------------------

    def paginate_and_group_checker(self, request, assigned_checklists, available_checklists, headers,
                                   true_level, allowed_statuses, category_q):
        """
        Room-wise grouping + group_complete flag; include only items status=pending_for_inspector
        """
        project_id = int(request.query_params.get("project_id"))
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
            "group_complete": False,
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

        # compute group_complete per room
        for room_id, payload in grouped.items():
            src = payload["assigned_to_me"] or payload["available_for_me"]
            if src:
                checklist_ids = [c["id"] for c in src]
                any_c = Checklist.objects.filter(id__in=checklist_ids).first()
                if any_c:
                    purpose_id = any_c.purpose_id
                    stage_id = any_c.stage_id
                    payload["group_complete"] = self.compute_room_group_complete(
                        project_id, purpose_id, stage_id,
                        true_level=true_level, loc_id=room_id,
                        allowed_statuses=allowed_statuses,
                        category_q=category_q
                    )

        user_generated_qs = Checklist.objects.filter(
            user_generated_id__isnull=False,
            project_id=project_id,
            room_id__isnull=True
        )
        if category_q:
            user_generated_qs = user_generated_qs.filter(category_q)

        user_generated_serialized = []
        for checklist in user_generated_qs:
            checklist_data = ChecklistSerializer(checklist).data
            items = ChecklistItem.objects.filter(checklist=checklist, status="pending_for_inspector")
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

        response_data = [
            room_data for room_data in grouped.values()
            if room_data["assigned_to_me"] or room_data["available_for_me"]
        ]
        response = paginator.get_paginated_response(response_data)
        note, sh_rows = self._compute_stage_note_and_history(
            request, int(request.query_params.get("project_id")), headers, true_level=true_level
        )
        if sh_rows:
            response.data["stage_history"] = sh_rows
        if note:
            response.data["note"] = note
        self._attach_crm_meta(response, request, note, sh_rows)

        # <<< END ADD >>>

        response.data['user_generated_checklists'] = user_generated_serialized
        return self._rewrite_paginator_links(response)

    def paginate_and_group_supervisor(self, request, assigned_checklists, available_checklists, headers,
                                      true_level, allowed_statuses, category_q):
        """
        Room-wise grouping + group_complete flag; items status=pending_for_supervisor
        """
        project_id = int(request.query_params.get("project_id"))

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
            "group_complete": False,
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

        for room_id, payload in grouped.items():
            src = payload["assigned_to_me"] or payload["available_for_me"]
            if src:
                checklist_ids = [c["id"] for c in src]
                any_c = Checklist.objects.filter(id__in=checklist_ids).first()
                if any_c:
                    purpose_id = any_c.purpose_id
                    stage_id = any_c.stage_id
                    payload["group_complete"] = self.compute_room_group_complete(
                        project_id, purpose_id, stage_id,
                        true_level=true_level, loc_id=room_id,
                        allowed_statuses=allowed_statuses,
                        category_q=category_q
                    )

        user_generated_qs = Checklist.objects.filter(
            user_generated_id__isnull=False,
            project_id=project_id,
            room_id__isnull=True
        )
        if category_q:
            user_generated_qs = user_generated_qs.filter(category_q)

        user_generated_serialized = []
        for checklist in user_generated_qs:
            checklist_data = ChecklistSerializer(checklist).data
            items = ChecklistItem.objects.filter(checklist=checklist, status="pending_for_supervisor")
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

        response_data = [
            room_data for room_data in grouped.values()
            if room_data["assigned_to_me"] or room_data["available_for_me"]
        ]
        response = paginator.get_paginated_response(response_data)
        note, sh_rows = self._compute_stage_note_and_history(
            request, int(request.query_params.get("project_id")), headers, true_level=true_level
        )
        if sh_rows:
            response.data["stage_history"] = sh_rows
        if note:
            response.data["note"] = note
        self._attach_crm_meta(response, request, note, sh_rows)


        response.data['user_generated_checklists'] = user_generated_serialized
        return self._rewrite_paginator_links(response)


    def paginate_and_group_maker(self, request, assigned_checklists, available_checklists, headers,
                                 true_level, allowed_statuses, category_q):
        """
        Room-wise grouping + group_complete flag; items status=pending_for_maker
        """
        project_id = int(request.query_params.get("project_id"))

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
            "group_complete": False,
            "assigned_to_me": [],
            "available_for_me": []
        })

        for checklist in paginated_checklists:
            room_id = checklist.room_id
            if room_id and room_id in room_details:
                grouped[room_id]["room_details"] = room_details[room_id]
            grouped[room_id]["room_id"] = room_id

            checklist_data = ChecklistSerializer(checklist).data
            items = ChecklistItem.objects.filter(checklist=checklist, status="pending_for_maker")
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

        for room_id, payload in grouped.items():
            src = payload["assigned_to_me"] or payload["available_for_me"]
            if src:
                checklist_ids = [c["id"] for c in src]
                any_c = Checklist.objects.filter(id__in=checklist_ids).first()
                if any_c:
                    purpose_id = any_c.purpose_id
                    stage_id = any_c.stage_id
                    payload["group_complete"] = self.compute_room_group_complete(
                        project_id, purpose_id, stage_id,
                        true_level=true_level, loc_id=room_id,
                        allowed_statuses=allowed_statuses,
                        category_q=category_q
                    )

        user_generated_qs = Checklist.objects.filter(
            user_generated_id__isnull=False,
            project_id=project_id,
            room_id__isnull=True
        )
        if category_q:
            user_generated_qs = user_generated_qs.filter(category_q)

        user_generated_serialized = []
        for checklist in user_generated_qs:
            checklist_data = ChecklistSerializer(checklist).data
            items = ChecklistItem.objects.filter(checklist=checklist, status="pending_for_maker")
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

        response_data = [
            room_data for room_data in grouped.values()
            if room_data["assigned_to_me"] or room_data["available_for_me"]
        ]
        response = paginator.get_paginated_response(response_data)
        note, sh_rows = self._compute_stage_note_and_history(
            request, int(request.query_params.get("project_id")), headers, true_level=true_level
        )
        if sh_rows:
            response.data["stage_history"] = sh_rows
        if note:
            response.data["note"] = note
        self._attach_crm_meta(response, request, note, sh_rows)


        response.data['user_generated_checklists'] = user_generated_serialized
        return self._rewrite_paginator_links(response)


    def paginate_and_group(self, request, checklists, headers):
        """
        Generic room-wise grouping with full item/submission expansion (initializer).
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
        response = paginator.get_paginated_response(response_data)

        project_id = request.query_params.get("project_id")
        note, sh_rows = self._compute_stage_note_and_history(
            request, int(project_id) if project_id else None, headers, true_level=None
        )
        if sh_rows:
            response.data["stage_history"] = sh_rows
        if note:
            response.data["note"] = note
        self._attach_crm_meta(response, request, note, sh_rows)


        return self._rewrite_paginator_links(response)



class MAker_DOne_view(APIView):
    permission_classes = [permissions.IsAuthenticated]

    USER_ACCESS_API = f"https://{local}/users/user-access/"

    # ---------------------------
    # helpers
    # ---------------------------
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
        """
        Stage/location filter (project + stage + true_level location).
        Category gets added via Q in _category_branch_q_from_checklist when needed.
        """
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

    def _category_branch_q_from_checklist(self, checklist):
        """
        Build a category-branch Q using this checklist's category + levels.
        """
        q = Q(category=checklist.category)
        for i in range(1, 7):
            v = getattr(checklist, f"category_level{i}", None)
            if v is not None:
                q &= Q(**{f"category_level{i}": v})
            else:
                break
        return q

    def _has_all_cat(self, request, user_id, project_id, headers) -> bool:
        """
        Return True if any of the user's accesses for this project has all_cat=true.
        """
        try:
            resp = requests.get(
                self.USER_ACCESS_API,
                params={"user_id": user_id, "project_id": project_id},
                headers=headers,
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json() or []
                return any(bool(a.get("all_cat") or a.get("ALL_CAT")) for a in data)
        except Exception:
            pass
        return False

    # ---------------------------
    # POST
    # ---------------------------
    # @transaction.atomic
    # def post(self, request):
    #     checklist_item_id = request.data.get("checklist_item_id")
    #     maker_remark = request.data.get("maker_remark", "")
    #     maker_media = request.FILES.get("maker_media", None)

    #     if not checklist_item_id:
    #         return Response({"detail": "checklist_item_id required."}, status=400)

    #     # 1) Item must be pending_for_maker
    #     try:
    #         item = ChecklistItem.objects.select_related("checklist").get(
    #             id=checklist_item_id, status="pending_for_maker"
    #         )
    #     except ChecklistItem.DoesNotExist:
    #         return Response(
    #             {"detail": "ChecklistItem not found or not pending for maker."},
    #             status=404,
    #         )

    #     checklist = item.checklist
    #     project_id = checklist.project_id

    #     latest_submission = (
    #         ChecklistItemSubmission.objects
    #         .filter(checklist_item=item, status="created")
    #         .order_by("-attempts", "-created_at")
    #         .first()
    #     )
    #     if not latest_submission:
    #         return Response(
    #             {"detail": "No matching submission found for rework."},
    #             status=404,
    #         )

    #     if not latest_submission.maker_id:
    #         latest_submission.maker_id = request.user.id

    #     headers = {}
    #     auth_header = request.headers.get("Authorization")
    #     if auth_header:
    #         headers["Authorization"] = auth_header  # keep full header as-is

    #     # --- flags
    #     flags = get_project_flags(project_id, headers=headers)
    #     skip_super = flags.get("skip_supervisory", False)
    #     repo_on = flags.get("checklist_repoetory", False)
    #     maker_to_checker = flags.get("maker_to_checker", False)

    #     # 2) Update submission + item (immediate statuses)
    #     if skip_super and maker_to_checker:
    #         # ✅ Directly complete on maker submit (no checker/supervisor step)
    #         latest_submission.status = "completed"
    #         item.status = "completed"
    #     elif skip_super:
    #         # maker -> checker flow (will become visible to checker later when scope ready)
    #         latest_submission.status = "pending_checker"
    #         item.status = "tetmpory_inspctor"
    #     else:
    #         # maker -> supervisor flow
    #         latest_submission.status = "pending_supervisor"
    #         item.status = "pending_for_supervisor"

    #     latest_submission.maker_remarks = maker_remark
    #     latest_submission.maker_at = timezone.now()
    #     if maker_media:
    #         latest_submission.maker_media = maker_media

    #     latest_submission.save(
    #         update_fields=["status", "maker_id", "maker_remarks", "maker_media", "maker_at"]
    #     )
    #     item.save(update_fields=["status"])

    #     # If the item is completed now, check if the whole checklist is completed too
    #     if item.status == "completed":
    #         if not checklist.items.exclude(status="completed").exists():
    #             checklist.status = "completed"
    #             checklist.save(update_fields=["status"])

    #     # 3) Flip to inspector visibility ONLY when skip_super=True AND maker_to_checker=False
    #     #    Scope:
    #     #      - If user has all_cat=True ⇒ wait for WHOLE true-level group (all categories)
    #     #      - Else ⇒ wait just for the category slice
    #     if skip_super and not maker_to_checker:
    #         true_level = self._get_true_level(project_id)
    #         group_fk = self._group_filters_for_checklist(checklist, true_level)

    #         has_all_cat = self._has_all_cat(request, request.user.id, project_id, headers)
    #         if has_all_cat:
    #             group_checklists = Checklist.objects.filter(**group_fk)
    #         else:
    #             branch_q = self._category_branch_q_from_checklist(checklist)
    #             group_checklists = Checklist.objects.filter(**group_fk).filter(branch_q)

    #         # Only expose to checker when the whole scope is ready
    #         group_not_ready_for_inspector = ChecklistItem.objects.filter(
    #             checklist__in=group_checklists
    #         ).exclude(status__in=["completed", "tetmpory_inspctor"]).exists()

    #         if not group_not_ready_for_inspector:
    #             ChecklistItem.objects.filter(
    #                 checklist__in=group_checklists,
    #                 status="tetmpory_inspctor"
    #             ).update(status="pending_for_inspector")

    #         # Re-open temp maker items only when whole scope is in allowed states
    #         group_not_ready_for_maker = ChecklistItem.objects.filter(
    #             checklist__in=group_checklists
    #         ).exclude(status__in=["completed", "tetmpory_Maker", "tetmpory_inspctor"]).exists()

    #         if not group_not_ready_for_maker:
    #             ChecklistItem.objects.filter(
    #                 checklist__in=group_checklists,
    #                 status="tetmpory_Maker"
    #             ).update(status="pending_for_maker")

    #     # 4) Maker_to_checker advancement (true-level scope only)
    #     stage_advanced = False
    #     advancement_info = None

    #     if skip_super and maker_to_checker:
    #         try:
    #             true_level = self._get_true_level(project_id)
    #             group_fk_full = self._group_filters_for_checklist(checklist, true_level)

    #             # TRUE-LEVEL scope across ALL categories
    #             group_checklists = Checklist.objects.filter(**group_fk_full)

    #             # Advance only when NO pending_for_maker items remain in this true-level group
    #             maker_open_exists = ChecklistItem.objects.filter(
    #                 checklist__in=group_checklists,
    #                 status="pending_for_maker"
    #             ).exists()

    #             if not maker_open_exists:
    #                 # resolve current StageHistory row for this location
    #                 sh_filter = {"project": project_id, "is_current": True}
    #                 if true_level == "flat_level":
    #                     sh_filter["flat"] = checklist.flat_id
    #                 elif true_level == "room_level":
    #                     sh_filter["room"] = checklist.room_id
    #                 elif true_level == "zone_level":
    #                     sh_filter["zone"] = checklist.zone_id
    #                 elif true_level == "level_id":
    #                     sh_filter["level_id"] = checklist.level_id
    #                 elif true_level == "checklist_level":
    #                     sh_filter["checklist"] = checklist.id

    #                 current_sh = StageHistory.objects.filter(**sh_filter).first()
    #                 if not current_sh:
    #                     advancement_info = "No current StageHistory found"
    #                 else:
    #                     # ask project-service for next stage/phase
    #                     next_stage_api = f"https://konstruct.world/projects/stages/{current_sh.stage}/next/"
    #                     try:
    #                         resp = requests.get(next_stage_api, headers=headers, timeout=5)
    #                         data = resp.json()
    #                     except Exception as e:
    #                         data = {}
    #                         advancement_info = f"Exception during next stage fetch: {e}"

    #                     if data.get("workflow_completed") is True:
    #                         current_sh.is_current = False
    #                         current_sh.completed_at = timezone.now()
    #                         current_sh.completed_by = request.user.id
    #                         current_sh.status = "completed"
    #                         current_sh.save()
    #                         stage_advanced = True
    #                         advancement_info = "Workflow fully completed"

    #                     elif "next_stage_id" in data and "phase_id" in data:
    #                         next_stage_id = data["next_stage_id"]
    #                         next_phase_id = data["phase_id"]

    #                         # close current
    #                         if next_phase_id == current_sh.phase_id:
    #                             current_sh.status = "move_to_next_stage"
    #                         else:
    #                             current_sh.status = "move_to_next_phase"
    #                         current_sh.is_current = False
    #                         current_sh.completed_at = timezone.now()
    #                         current_sh.completed_by = request.user.id
    #                         current_sh.save()

    #                         # open next
    #                         StageHistory.objects.create(
    #                             project=current_sh.project,
    #                             phase_id=next_phase_id,
    #                             stage=next_stage_id,
    #                             started_at=timezone.now(),
    #                             is_current=True,
    #                             flat=getattr(checklist, "flat_id", None),
    #                             room=getattr(checklist, "room_id", None),
    #                             zone=getattr(checklist, "zone_id", None),
    #                             checklist=checklist if true_level == "checklist_level" else None,
    #                             status="started",
    #                         )
    #                         stage_advanced = True
    #                         advancement_info = {
    #                             "new_phase_id": next_phase_id,
    #                             "new_stage_id": next_stage_id,
    #                             "msg": "Advanced to next stage (maker path)",
    #                         }

    #                         # clone repository for the TRUE-LEVEL group
    #                         if repo_on:
    #                             source_group_qs = group_checklists
    #                             if source_group_qs.exists():
    #                                 VerifyChecklistItemForCheckerNSupervisorAPIView._clone_group_to_next_stage(
    #                                     source_group_qs=source_group_qs,
    #                                     next_phase_id=next_phase_id,
    #                                     next_stage_id=next_stage_id,
    #                                 )
    #                     elif data.get("workflow_completed") is False and "detail" in data:
    #                         current_sh.is_current = False
    #                         current_sh.completed_at = timezone.now()
    #                         current_sh.completed_by = request.user.id
    #                         current_sh.status = "completed"
    #                         current_sh.save()
    #                         stage_advanced = True
    #                         advancement_info = data["detail"]
    #                     else:
    #                         advancement_info = data.get("detail", "Invalid next stage/phase data")
    #             else:
    #                 advancement_info = "Maker group not complete yet (true-level scope)"
    #         except Exception as e:
    #             advancement_info = f"Maker-to-checker advance failed: {e}"

    #     # 5) Response
    #     item_data = ChecklistItemSerializer(item).data
    #     submission_data = {
    #         "id": latest_submission.id,
    #         "status": latest_submission.status,
    #         "maker_remarks": latest_submission.maker_remarks,
    #         "maker_media": latest_submission.maker_media.url if latest_submission.maker_media else None,
    #         "maker_at": latest_submission.maker_at,
    #         "checker_id": latest_submission.checker_id,
    #         "maker_id": latest_submission.maker_id,
    #         "supervisor_id": latest_submission.supervisor_id,
    #     }
    #     return Response(
    #         {
    #             "item": item_data,
    #             "submission": submission_data,
    #             "detail": "Checklist item marked as done by maker.",
    #             "stage_advanced": stage_advanced,
    #             "advancement_info": advancement_info,
    #         },
    #         status=200
    #     )


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

        headers = {}
        auth_header = request.headers.get("Authorization")
        if auth_header:
            headers["Authorization"] = auth_header  # keep full header as-is

        # --- flags
        flags = get_project_flags(project_id, headers=headers)
        skip_super = flags.get("skip_supervisory", False)
        repo_on = flags.get("checklist_repoetory", False)
        maker_to_checker = flags.get("maker_to_checker", False)

        # 2) Update submission + item (immediate statuses)
        if skip_super and maker_to_checker:
            # ✅ Directly complete on maker submit (no checker/supervisor step)
            latest_submission.status = "completed"
            item.status = "completed"
        elif skip_super:
            # maker -> checker flow (will become visible to checker later when scope ready)
            latest_submission.status = "pending_checker"
            item.status = "tetmpory_inspctor"
        else:
            # maker -> supervisor flow
            latest_submission.status = "pending_supervisor"
            item.status = "pending_for_supervisor"

        latest_submission.maker_remarks = maker_remark
        latest_submission.maker_at = timezone.now()
        if maker_media:
            latest_submission.maker_media = maker_media

        latest_submission.save(
            update_fields=["status", "maker_id", "maker_remarks", "maker_media", "maker_at"]
        )
        item.save(update_fields=["status"])

        # If the item is completed now, check if the whole checklist is completed too
        if item.status == "completed":
            if not checklist.items.exclude(status="completed").exists():
                checklist.status = "completed"
                checklist.save(update_fields=["status"])

        # 3) Flip to inspector visibility ONLY when skip_super=True AND maker_to_checker=False
        #    Scope:
        #      - If user has all_cat=True ⇒ wait for WHOLE true-level group (all categories)
        #      - Else ⇒ wait just for the category slice
        if skip_super and not maker_to_checker:
            true_level = self._get_true_level(project_id)
            group_fk = self._group_filters_for_checklist(checklist, true_level)

            has_all_cat = self._has_all_cat(request, request.user.id, project_id, headers)
            if has_all_cat:
                group_checklists = Checklist.objects.filter(**group_fk)
            else:
                branch_q = self._category_branch_q_from_checklist(checklist)
                group_checklists = Checklist.objects.filter(**group_fk).filter(branch_q)

            # Only expose to checker when the whole scope is ready
            group_not_ready_for_inspector = ChecklistItem.objects.filter(
                checklist__in=group_checklists
            ).exclude(status__in=["completed", "tetmpory_inspctor"]).exists()

            if not group_not_ready_for_inspector:
                ChecklistItem.objects.filter(
                    checklist__in=group_checklists,
                    status="tetmpory_inspctor"
                ).update(status="pending_for_inspector")

            # Re-open temp maker items only when whole scope is in allowed states
            group_not_ready_for_maker = ChecklistItem.objects.filter(
                checklist__in=group_checklists
            ).exclude(status__in=["completed", "tetmpory_Maker", "tetmpory_inspctor"]).exists()

            if not group_not_ready_for_maker:
                ChecklistItem.objects.filter(
                    checklist__in=group_checklists,
                    status="tetmpory_Maker"
                ).update(status="pending_for_maker")

        # 4) Maker_to_checker advancement (true-level scope only)
        stage_advanced = False
        advancement_info = None
        note = None  # ← extra field for response

        if skip_super and maker_to_checker:
            try:
                true_level = self._get_true_level(project_id)
                group_fk_full = self._group_filters_for_checklist(checklist, true_level)

                # TRUE-LEVEL scope across ALL categories
                group_checklists = Checklist.objects.filter(**group_fk_full)

                # Advance only when NO pending_for_maker items remain in this true-level group
                maker_open_exists = ChecklistItem.objects.filter(
                    checklist__in=group_checklists,
                    status="pending_for_maker"
                ).exists()

                if not maker_open_exists:
                    # resolve current StageHistory row for this location
                    sh_filter = {"project": project_id, "is_current": True}
                    if true_level == "flat_level":
                        sh_filter["flat"] = checklist.flat_id
                    elif true_level == "room_level":
                        sh_filter["room"] = checklist.room_id
                    elif true_level == "zone_level":
                        sh_filter["zone"] = checklist.zone_id
                    elif true_level == "level_id":
                        sh_filter["level_id"] = checklist.level_id
                    elif true_level == "checklist_level":
                        sh_filter["checklist"] = checklist.id

                    current_sh = StageHistory.objects.filter(**sh_filter).first()
                    if not current_sh:
                        advancement_info = "No current StageHistory found"
                    else:
                        # ask project-service for next stage/phase
                        next_stage_api = f"https://konstruct.world/projects/stages/{current_sh.stage}/next/"
                        try:
                            resp = requests.get(next_stage_api, headers=headers, timeout=5)
                            data = resp.json()
                        except Exception as e:
                            data = {}
                            advancement_info = f"Exception during next stage fetch: {e}"

                        # Helper to fill completed_by_name
                        completed_by_name = (
                            getattr(request.user, "get_full_name", lambda: "")() or
                            getattr(request.user, "username", str(request.user.id))
                        )

                        if data.get("workflow_completed") is True:
                            current_sh.is_current = False
                            current_sh.completed_at = timezone.now()
                            current_sh.completed_by = request.user.id
                            current_sh.completed_by_name = completed_by_name
                            current_sh.status = "completed"
                            current_sh.save()
                            stage_advanced = True
                            advancement_info = "Workflow fully completed"
                            note ="Completed CRM PENDING"

                        elif "next_stage_id" in data and "phase_id" in data:
                            next_stage_id = data["next_stage_id"]
                            next_phase_id = data["phase_id"]

                            # close current
                            if next_phase_id == current_sh.phase_id:
                                current_sh.status = "move_to_next_stage"
                            else:
                                current_sh.status = "move_to_next_phase"
                            current_sh.is_current = False
                            current_sh.completed_at = timezone.now()
                            current_sh.completed_by = request.user.id
                            current_sh.completed_by_name = completed_by_name
                            current_sh.save()

                            # open next
                            StageHistory.objects.create(
                                project=current_sh.project,
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
                            stage_advanced = True
                            advancement_info = {
                                "new_phase_id": next_phase_id,
                                "new_stage_id": next_stage_id,
                                "msg": "Advanced to next stage (maker path)",
                            }

                            # clone repository for the TRUE-LEVEL group
                            if repo_on:
                                source_group_qs = group_checklists
                                if source_group_qs.exists():
                                    VerifyChecklistItemForCheckerNSupervisorAPIView._clone_group_to_next_stage(
                                        source_group_qs=source_group_qs,
                                        next_phase_id=next_phase_id,
                                        next_stage_id=next_stage_id,
                                    )
                        elif data.get("workflow_completed") is False and "detail" in data:
                            # treat as terminal here as well
                            current_sh.is_current = False
                            current_sh.completed_at = timezone.now()
                            current_sh.completed_by = request.user.id
                            current_sh.completed_by_name = completed_by_name
                            current_sh.status = "completed"
                            current_sh.save()
                            stage_advanced = True
                            advancement_info = data["detail"]
                            note = "Completed CRM PENDING"
                        else:
                            advancement_info = data.get("detail", "Invalid next stage/phase data")
                else:
                    advancement_info = "Maker group not complete yet (true-level scope)"
            except Exception as e:
                advancement_info = f"Maker-to-checker advance failed: {e}"

        # 5) Response
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
                "detail": "Checklist item marked as done by maker.",
                "stage_advanced": stage_advanced,
                "advancement_info": advancement_info,
                "note": note,  # ← NEW
            },
            status=200
        )



    # ---------------------------
    # GET (optional)
    # ---------------------------
    def get(self, request):
        user_id = request.user.id
        queryset = ChecklistItemSubmission.objects.filter(
            maker_id=user_id,
            status__in=["created", "pending_supervisor", "pending_checker"]
        ).order_by("-created_at")
        serializer = ChecklistItemSubmissionSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)


class VerifyChecklistItemForCheckerNSupervisorAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _group_filter_kwargs(checklist, true_level):
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

    @staticmethod
    @transaction.atomic
    def _clone_group_to_next_stage(*, source_group_qs, next_phase_id, next_stage_id):
        """
        Clone all checklists/items/options/submissions from source_group_qs into (next_phase_id, next_stage_id).
        - New checklist.status = "work_in_progress"
        - New item.status = "pending_for_inspector"
        - Clone ALL existing submissions for each item (same field values, linked to new item)
        - Then create ONE fresh submission per new item with status="pending_checker" and other fields NULL
        """
        # Local imports to avoid circulars
        from django.db import models
        from checklists.models import (
            Checklist, ChecklistItem, ChecklistItemOption, ChecklistItemSubmission
        )

        print(f"[CLONE] Starting clone for next_phase={next_phase_id}, next_stage={next_stage_id}")
        print(f"[CLONE] Source group has {source_group_qs.count()} checklists to clone")

        old_to_new_checklist = {}
        new_checklists = []
        for c in source_group_qs:
            nc = Checklist(
                project_id=c.project_id,
                purpose_id=c.purpose_id,
                phase_id=next_phase_id,
                stage_id=next_stage_id,

                building_id=c.building_id,
                zone_id=c.zone_id,
                flat_id=c.flat_id,
                room_id=c.room_id,
                subzone_id=getattr(c, "subzone_id", None),
                level_id=getattr(c, "level_id", None),

                category=c.category,
                category_level1=c.category_level1,
                category_level2=c.category_level2,
                category_level3=c.category_level3,
                category_level4=c.category_level4,
                category_level5=c.category_level5,
                category_level6=c.category_level6,

                name=c.name,
                description=c.description,
                remarks=c.remarks,
                created_by_id=c.created_by_id,
                user_generated_id=c.user_generated_id,

                status="work_in_progress",
            )
            old_to_new_checklist[c.id] = nc
            new_checklists.append(nc)

        Checklist.objects.bulk_create(new_checklists)
        print(f"[CLONE] Created {len(new_checklists)} new checklists")

        missing_pks = sum(1 for nc in new_checklists if not getattr(nc, "id", None))
        if missing_pks:
            print(f"[CLONE][WARN] {missing_pks} new checklists have no PK after bulk_create; "
                  f"ensure Postgres / Django supports returning IDs on bulk_create.")

        old_to_new_item = {}
        new_items = []
        for oc in source_group_qs:
            items = ChecklistItem.objects.filter(checklist_id=oc.id).order_by("id")
            print(f"[CLONE] Found {items.count()} items for checklist {oc.id}")
            parent_new_checklist = old_to_new_checklist[oc.id]
            for it in items:
                nit = ChecklistItem(
                    checklist=parent_new_checklist,
                    title=it.title,
                    description=it.description,
                    status="pending_for_inspector",
                    ignore_now=getattr(it, "ignore_now", False),
                    photo_required=getattr(it, "photo_required", False),
                )
                old_to_new_item[it.id] = nit
                new_items.append(nit)

        if new_items:
            ChecklistItem.objects.bulk_create(new_items)
        print(f"[CLONE] Created {len(new_items)} new items")

        # 3) clone options
        new_opts = []
        for old_item_id, new_item in old_to_new_item.items():
            opts = ChecklistItemOption.objects.filter(checklist_item_id=old_item_id)
            if opts.exists():
                print(f"[CLONE] Found {opts.count()} options for item {old_item_id}")
            for op in opts:
                new_opts.append(
                    ChecklistItemOption(
                        checklist_item=new_item,
                        name=op.name,
                        choice=op.choice,
                    )
                )
        if new_opts:
            ChecklistItemOption.objects.bulk_create(new_opts)
        print(f"[CLONE] Created {len(new_opts)} new options")

        # 4) clone ALL existing submissions (history)
        cloned_submissions = []
        for old_item_id, new_item in old_to_new_item.items():
            subs = ChecklistItemSubmission.objects.filter(
                checklist_item_id=old_item_id
            ).order_by("created_at", "id")
            if subs.exists():
                print(f"[CLONE] Found {subs.count()} submissions for item {old_item_id}")
            for s in subs:
                cloned_submissions.append(
                    ChecklistItemSubmission(
                        checklist_item=new_item,
                        status=s.status,
                        attempts=s.attempts,

                        maker_id=s.maker_id,
                        maker_remarks=s.maker_remarks,
                        maker_media=s.maker_media,
                        maker_at=s.maker_at,

                        supervisor_id=s.supervisor_id,
                        supervisor_remarks=s.supervisor_remarks,
                        reviewer_photo=s.reviewer_photo,
                        supervised_at=s.supervised_at,

                        inspector_photo=s.inspector_photo,
                        checker_id=s.checker_id,
                        checked_at=s.checked_at,
                        checker_remarks=s.checker_remarks,

                        remarks=s.remarks,
                    )
                )
        if cloned_submissions:
            ChecklistItemSubmission.objects.bulk_create(cloned_submissions)
        print(f"[CLONE] Cloned {len(cloned_submissions)} submissions from history")

        # 5) add one fresh pending_checker submission per new item
        fresh_subs = []
        for _, new_item in old_to_new_item.items():
            max_attempt = ChecklistItemSubmission.objects.filter(
                checklist_item=new_item
            ).aggregate(m=models.Max("attempts"))["m"] or 0

            fresh_subs.append(
                ChecklistItemSubmission(
                    checklist_item=new_item,
                    status="pending_checker",
                    attempts=max_attempt + 1,

                    maker_id=None,
                    maker_remarks=None,
                    maker_media=None,
                    maker_at=None,

                    supervisor_id=None,
                    supervisor_remarks=None,
                    reviewer_photo=None,
                    supervised_at=None,

                    inspector_photo=None,
                    checker_id=None,
                    checked_at=None,
                    checker_remarks=None,

                    remarks=None,
                )
            )
        if fresh_subs:
            ChecklistItemSubmission.objects.bulk_create(fresh_subs)
        print(f"[CLONE] Created {len(fresh_subs)} fresh 'pending_checker' submissions")

        print("[CLONE] ✅ Clone completed successfully")

    USER_ACCESS_API = f"https://{local}/users/user-access/"

    def _has_all_cat(self, request, project_id, headers) -> bool:
        try:
            resp = requests.get(
                self.USER_ACCESS_API,
                params={"user_id": request.user.id, "project_id": project_id},
                headers=headers,
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json() or []
                return any(bool(a.get("all_cat") or a.get("All_checklist") or a.get("ALL_CAT")) for a in data)
        except Exception:
            pass
        return False

    def _category_branch_q_from_checklist(self, checklist):
        q = Q(category=checklist.category)
        for i in range(1, 7):
            v = getattr(checklist, f"category_level{i}", None)
            if v is not None:
                q &= Q(**{f"category_level{i}": v})
            else:
                break
        return q

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

        current_stagehistory.is_current = False
        current_stagehistory.completed_at = timezone.now()
        current_stagehistory.completed_by = user_id
        # optional: if you want here too
        # current_stagehistory.completed_by_name = <provide a name if available in this context>
        current_stagehistory.status = "completed"
        current_stagehistory.save()
        print(f"[DEBUG] advance_stage_if_completed: Marked current StageHistory id={current_stagehistory.id} completed")

        purpose_id = self.get_active_purpose(project_id)
        phases = self.get_phases(project_id, purpose_id)
        if not phases:
            print("[DEBUG] advance_stage_if_completed: No phases found, assuming workflow complete")
            return True, "Phases not found, assuming workflow complete"

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
            check_photo = request.FILES.get('inspector_photo', None)

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
                note = None  # << ensure defined for all paths

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

                            completed_by_name = (
                                getattr(request.user, "get_full_name", lambda: "")() or
                                getattr(request.user, "username", str(request.user.id))
                            )

                            if data.get("workflow_completed") is True:
                                current_stagehistory.is_current = False
                                current_stagehistory.completed_at = timezone.now()
                                current_stagehistory.completed_by = user_id
                                current_stagehistory.completed_by_name = completed_by_name
                                current_stagehistory.status = "completed"
                                current_stagehistory.save()
                                advanced = True
                                advancement_info = "Workflow fully completed"
                                note = "Completed"

                            elif data.get("workflow_completed") is False and "detail" in data:
                                current_stagehistory.is_current = False
                                current_stagehistory.completed_at = timezone.now()
                                current_stagehistory.completed_by = user_id
                                current_stagehistory.completed_by_name = completed_by_name
                                current_stagehistory.status = "completed"
                                current_stagehistory.save()
                                advanced = True
                                advancement_info = data["detail"]
                                note = "Completed"

                            elif "next_stage_id" in data and "phase_id" in data:
                                next_stage_id = data["next_stage_id"]
                                next_phase_id = data["phase_id"]

                                if next_phase_id == current_stagehistory.phase_id:
                                    current_stagehistory.status = "move_to_next_stage"
                                else:
                                    current_stagehistory.status = "move_to_next_phase"

                                current_stagehistory.is_current = False
                                current_stagehistory.completed_at = timezone.now()
                                current_stagehistory.completed_by = user_id
                                current_stagehistory.completed_by_name = completed_by_name
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
                                    flags = get_project_flags(project_id, headers=headers)
                                    print(f"[DEBUG] checklist_repoetory = {flags.get('checklist_repoetory')} for project {project_id}")

                                    if flags.get("checklist_repoetory", False):
                                        true_level = self.get_true_level(project_id)
                                        print(f"[DEBUG] true_level for project {project_id} = {true_level}")
                                        group_fk = self._group_filter_kwargs(checklist, true_level)
                                        print(f"[DEBUG] group_fk for source group: {group_fk}")
                                        source_group_qs = Checklist.objects.filter(**group_fk)
                                        print(f"[DEBUG] Found {source_group_qs.count()} checklists in source group")

                                        if source_group_qs.exists():
                                            self._clone_group_to_next_stage(
                                                source_group_qs=source_group_qs,
                                                next_phase_id=next_phase_id,
                                                next_stage_id=next_stage_id,
                                            )
                                            print(f"[DEBUG] Cloning done into phase={next_phase_id}, stage={next_stage_id}")
                                        else:
                                            print("[DEBUG] No source checklists found — skipping clone")

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

                return Response({
                    "detail": "Item completed.",
                    "item_id": item.id,
                    "item_status": item.status,
                    "submission_id": submission.id,
                    "submission_status": submission.status,
                    "checklist_status": checklist.status,
                    "stage_advanced": advanced,
                    "advancement_info": advancement_info,
                    "note": note,  # now "Completed" only on terminal
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
            supervisor_remark = request.data.get('supervisor_remarks', '')
            supervisor_photo = request.FILES.get('reviewer_photo', None)

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

            auth_header = request.headers.get("Authorization")
            headers = {"Authorization": auth_header} if auth_header else {}

            # Category vs true-level scope depending on all_cat
            if self._has_all_cat(request, checklist.project_id, headers):
                # user can see all categories ⇒ keep true-level scope (as-is)
                checklists_in_group = Checklist.objects.filter(**filter_kwargs)
            else:
                # user restricted ⇒ gate by the checklist's category branch only
                branch_q = self._category_branch_q_from_checklist(checklist)
                checklists_in_group = Checklist.objects.filter(**filter_kwargs).filter(branch_q)

            if option.choice == "P":
                item.status = "tetmpory_inspctor"
                submission.status = "pending_checker"
                item.save(update_fields=["status"])
                submission.save(update_fields=[
                    "supervisor_remarks", "supervised_at", "reviewer_photo", "status", "supervisor_id"
                ])

                group_items = ChecklistItem.objects.filter(checklist__in=checklists_in_group)

                # Only flip to inspector-visible when ENTIRE scope (category or true-level) is ready
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



# class VerifyChecklistItemForCheckerNSupervisorAPIView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     @staticmethod
#     def _group_filter_kwargs(checklist, true_level):
#         fk = {"project_id": checklist.project_id, "stage_id": checklist.stage_id}
#         if true_level == "flat_level":
#             fk["flat_id"] = checklist.flat_id
#         elif true_level == "room_level":
#             fk["room_id"] = checklist.room_id
#         elif true_level == "zone_level":
#             fk["zone_id"] = checklist.zone_id
#         elif true_level == "level_id":
#             fk["level_id"] = checklist.level_id
#         elif true_level == "checklist_level":
#             fk["id"] = checklist.id
#         return fk

#     @staticmethod
#     @transaction.atomic
#     def _clone_group_to_next_stage(*, source_group_qs, next_phase_id, next_stage_id):
#         """
#         Clone all checklists/items/options/submissions from source_group_qs into (next_phase_id, next_stage_id).
#         - New checklist.status = "work_in_progress"
#         - New item.status = "pending_for_inspector"
#         - Clone ALL existing submissions for each item (same field values, linked to new item)
#         - Then create ONE fresh submission per new item with status="pending_checker" and other fields NULL
#         """
#         # Local imports to avoid circulars
#         from django.db import models
#         from checklists.models import (
#             Checklist, ChecklistItem, ChecklistItemOption, ChecklistItemSubmission
#         )

#         print(f"[CLONE] Starting clone for next_phase={next_phase_id}, next_stage={next_stage_id}")
#         print(f"[CLONE] Source group has {source_group_qs.count()} checklists to clone")

#         old_to_new_checklist = {}
#         new_checklists = []
#         for c in source_group_qs:
#             nc = Checklist(
#                 project_id=c.project_id,
#                 purpose_id=c.purpose_id,
#                 phase_id=next_phase_id,
#                 stage_id=next_stage_id,

#                 building_id=c.building_id,
#                 zone_id=c.zone_id,
#                 flat_id=c.flat_id,
#                 room_id=c.room_id,
#                 subzone_id=getattr(c, "subzone_id", None),
#                 level_id=getattr(c, "level_id", None),

#                 category=c.category,
#                 category_level1=c.category_level1,
#                 category_level2=c.category_level2,
#                 category_level3=c.category_level3,
#                 category_level4=c.category_level4,
#                 category_level5=c.category_level5,
#                 category_level6=c.category_level6,

#                 name=c.name,
#                 description=c.description,
#                 remarks=c.remarks,
#                 created_by_id=c.created_by_id,
#                 user_generated_id=c.user_generated_id,

#                 status="work_in_progress",
#             )
#             old_to_new_checklist[c.id] = nc
#             new_checklists.append(nc)

#         Checklist.objects.bulk_create(new_checklists)
#         print(f"[CLONE] Created {len(new_checklists)} new checklists")

#         missing_pks = sum(1 for nc in new_checklists if not getattr(nc, "id", None))
#         if missing_pks:
#             print(f"[CLONE][WARN] {missing_pks} new checklists have no PK after bulk_create; "
#                 f"ensure Postgres / Django supports returning IDs on bulk_create.")

#         old_to_new_item = {}
#         new_items = []
#         for oc in source_group_qs:
#             items = ChecklistItem.objects.filter(checklist_id=oc.id).order_by("id")
#             print(f"[CLONE] Found {items.count()} items for checklist {oc.id}")
#             parent_new_checklist = old_to_new_checklist[oc.id]
#             for it in items:
#                 nit = ChecklistItem(
#                     checklist=parent_new_checklist,
#                     title=it.title,
#                     description=it.description,
#                     status="pending_for_inspector",
#                     ignore_now=getattr(it, "ignore_now", False),
#                     photo_required=getattr(it, "photo_required", False),
#                 )
#                 old_to_new_item[it.id] = nit
#                 new_items.append(nit)

#         if new_items:
#             ChecklistItem.objects.bulk_create(new_items)
#         print(f"[CLONE] Created {len(new_items)} new items")

#         # 3) clone options (✅ your model uses `name`, not `label`)
#         new_opts = []
#         for old_item_id, new_item in old_to_new_item.items():
#             opts = ChecklistItemOption.objects.filter(checklist_item_id=old_item_id)
#             if opts.exists():
#                 print(f"[CLONE] Found {opts.count()} options for item {old_item_id}")
#             for op in opts:
#                 new_opts.append(
#                     ChecklistItemOption(
#                         checklist_item=new_item,
#                         name=op.name,
#                         choice=op.choice,
#                     )
#                 )
#         if new_opts:
#             ChecklistItemOption.objects.bulk_create(new_opts)
#         print(f"[CLONE] Created {len(new_opts)} new options")

#         # 4) clone ALL existing submissions (history)
#         cloned_submissions = []
#         for old_item_id, new_item in old_to_new_item.items():
#             subs = ChecklistItemSubmission.objects.filter(
#                 checklist_item_id=old_item_id
#             ).order_by("created_at", "id")
#             if subs.exists():
#                 print(f"[CLONE] Found {subs.count()} submissions for item {old_item_id}")
#             for s in subs:
#                 cloned_submissions.append(
#                     ChecklistItemSubmission(
#                         checklist_item=new_item,
#                         status=s.status,
#                         attempts=s.attempts,

#                         maker_id=s.maker_id,
#                         maker_remarks=s.maker_remarks,
#                         maker_media=s.maker_media,
#                         maker_at=s.maker_at,

#                         supervisor_id=s.supervisor_id,
#                         supervisor_remarks=s.supervisor_remarks,
#                         reviewer_photo=s.reviewer_photo,
#                         supervised_at=s.supervised_at,

#                         inspector_photo=s.inspector_photo,
#                         checker_id=s.checker_id,
#                         checked_at=s.checked_at,
#                         checker_remarks=s.checker_remarks,

#                         remarks=s.remarks,
#                     )
#                 )
#         if cloned_submissions:
#             ChecklistItemSubmission.objects.bulk_create(cloned_submissions)
#         print(f"[CLONE] Cloned {len(cloned_submissions)} submissions from history")

#         # 5) add one fresh pending_checker submission per new item
#         fresh_subs = []
#         for _, new_item in old_to_new_item.items():
#             max_attempt = ChecklistItemSubmission.objects.filter(
#                 checklist_item=new_item
#             ).aggregate(m=models.Max("attempts"))["m"] or 0

#             fresh_subs.append(
#                 ChecklistItemSubmission(
#                     checklist_item=new_item,
#                     status="pending_checker",
#                     attempts=max_attempt + 1,

#                     maker_id=None,
#                     maker_remarks=None,
#                     maker_media=None,
#                     maker_at=None,

#                     supervisor_id=None,
#                     supervisor_remarks=None,
#                     reviewer_photo=None,
#                     supervised_at=None,

#                     inspector_photo=None,
#                     checker_id=None,
#                     checked_at=None,
#                     checker_remarks=None,

#                     remarks=None,
#                 )
#             )
#         if fresh_subs:
#             ChecklistItemSubmission.objects.bulk_create(fresh_subs)
#         print(f"[CLONE] Created {len(fresh_subs)} fresh 'pending_checker' submissions")

#         print("[CLONE] ✅ Clone completed successfully")


#     USER_ACCESS_API = f"https://{local}/users/user-access/"

#     def _has_all_cat(self, request, project_id, headers) -> bool:
#         try:
#             resp = requests.get(
#                 self.USER_ACCESS_API,
#                 params={"user_id": request.user.id, "project_id": project_id},
#                 headers=headers,
#                 timeout=5,
#             )
#             if resp.status_code == 200:
#                 data = resp.json() or []
#                 return any(bool(a.get("all_cat") or a.get("All_checklist") or a.get("ALL_CAT")) for a in data)
#         except Exception:
#             pass
#         return False

#     def _category_branch_q_from_checklist(self, checklist):
#         q = Q(category=checklist.category)
#         for i in range(1, 7):
#             v = getattr(checklist, f"category_level{i}", None)
#             if v is not None:
#                 q &= Q(**{f"category_level{i}": v})
#             else:
#                 break
#         return q



#     def get_active_purpose(self, project_id):
#         url = f"https://konstruct.world/projects/projects/{project_id}/activate-purpose/"
#         try:
#             resp = requests.get(url)
#             print(f"[DEBUG] get_active_purpose: status {resp.status_code} for project {project_id}")
#             if resp.status_code == 200:
#                 data = resp.json()
#                 if data.get("is_current"):
#                     print(f"[DEBUG] get_active_purpose: found active purpose id {data['id']}")
#                     return data["id"]
#             print("[DEBUG] get_active_purpose: no active purpose found or not current")
#         except Exception as e:
#             print(f"[ERROR] Purpose fetch error: {e}")
#         return None

#     def get_phases(self, project_id, purpose_id):
#         url = f"https://konstruct.world/projects/phases/by-project/{project_id}/"
#         try:
#             resp = requests.get(url)
#             print(f"[DEBUG] get_phases: status {resp.status_code} for project {project_id}, purpose {purpose_id}")
#             if resp.status_code == 200:
#                 data = resp.json()
#                 phases = [p for p in data if p["purpose"]["id"] == purpose_id and p["is_active"]]
#                 phases.sort(key=lambda x: x["sequence"])
#                 print(f"[DEBUG] get_phases: found phases {[p['id'] for p in phases]}")
#                 return phases
#             print(f"[DEBUG] get_phases: failed to get phases or empty list")
#         except Exception as e:
#             print(f"[ERROR] Phase fetch error: {e}")
#         return []

#     def get_stages(self, project_id, phase_id):
#         url = f"https://konstruct.world/projects/get-stage-details-by-project-id/{project_id}/"
#         try:
#             resp = requests.get(url)
#             print(f"[DEBUG] get_stages: status {resp.status_code} for project {project_id}, phase {phase_id}")
#             if resp.status_code == 200:
#                 data = resp.json()
#                 stages = [s for s in data if s["phase"] == phase_id and s["is_active"]]
#                 stages.sort(key=lambda x: x["sequence"])
#                 print(f"[DEBUG] get_stages: found stages {[s['id'] for s in stages]}")
#                 return stages
#             print(f"[DEBUG] get_stages: failed to get stages or empty list")
#         except Exception as e:
#             print(f"[ERROR] Stage fetch error: {e}")
#         return []

#     def get_true_level(self, project_id):
#         TRANSFER_RULE_API = f"https://{local}/projects/transfer-rules/"
#         try:
#             resp = requests.get(TRANSFER_RULE_API, params={"project_id": project_id})
#             print(f"[DEBUG] get_true_level: status {resp.status_code} for project {project_id}")
#             if resp.status_code == 200 and resp.json():
#                 true_level = resp.json()[0].get("true_level")
#                 print(f"[DEBUG] get_true_level: true_level = {true_level}")
#                 return true_level
#             print(f"[DEBUG] get_true_level: no transfer rule found or empty response")
#         except Exception as e:
#             print(f"[ERROR] TransferRule error: {e}")
#         return None

#     def advance_stage_if_completed(self, checklist, user_id, true_level):
#         print(f"[DEBUG] advance_stage_if_completed called for checklist id={checklist.id} user_id={user_id} true_level={true_level}")

#         project_id = checklist.project_id

#         filter_kwargs = {
#             "project": project_id,
#             "is_current": True,
#         }
#         if true_level == "flat_level":
#             filter_kwargs["flat"] = checklist.flat_id
#         elif true_level == "room_level":
#             filter_kwargs["room"] = checklist.room_id
#         elif true_level == "zone_level":
#             filter_kwargs["zone"] = checklist.zone_id
#         elif true_level == "level_id":
#             filter_kwargs["level_id"] = checklist.level_id
#         elif true_level == "checklist_level":
#             filter_kwargs["checklist"] = checklist.id

#         print(f"[DEBUG] advance_stage_if_completed: filter_kwargs = {filter_kwargs}")
#         current_stagehistory = StageHistory.objects.filter(**filter_kwargs).first()
#         if not current_stagehistory:
#             print("[DEBUG] advance_stage_if_completed: No current StageHistory found")
#             return False, "No current StageHistory found"

#         checklists_in_group = Checklist.objects.filter(
#             project_id=project_id,
#             stage_id=current_stagehistory.stage,
#         )
#         if true_level == "flat_level":
#             checklists_in_group = checklists_in_group.filter(flat_id=checklist.flat_id)
#         elif true_level == "room_level":
#             checklists_in_group = checklists_in_group.filter(room_id=checklist.room_id)
#         elif true_level == "zone_level":
#             checklists_in_group = checklists_in_group.filter(zone_id=checklist.zone_id)
#         elif true_level == "level_id":
#             checklists_in_group = checklists_in_group.filter(level_id=checklist.level_id)
#         elif true_level == "checklist_level":
#             checklists_in_group = checklists_in_group.filter(id=checklist.id)

#         all_completed = not checklists_in_group.exclude(status="completed").exists()
#         print(f"[DEBUG] advance_stage_if_completed: all_checklists_completed = {all_completed}")
#         if not all_completed:
#             return False, "Not all checklists are completed"

#         current_stagehistory.is_current = False
#         current_stagehistory.completed_at = timezone.now()
#         current_stagehistory.completed_by = user_id
#         current_stagehistory.status = "completed"
#         current_stagehistory.save()
#         print(f"[DEBUG] advance_stage_if_completed: Marked current StageHistory id={current_stagehistory.id} completed")

#         purpose_id = self.get_active_purpose(project_id)
#         phases = self.get_phases(project_id, purpose_id)
#         if not phases:
#             print("[DEBUG] advance_stage_if_completed: No phases found, assuming workflow complete")
#             return True, "Phases not found, assuming workflow complete"

#         current_phase_id = getattr(current_stagehistory, "phase_id", None) or checklist.phase_id
#         phase_ids = [p["id"] for p in phases]
#         try:
#             current_phase_idx = phase_ids.index(current_phase_id)
#         except ValueError:
#             current_phase_idx = 0

#         current_phase = phases[current_phase_idx]
#         print(f"[DEBUG] advance_stage_if_completed: current_phase id={current_phase['id']}")

#         stages = self.get_stages(project_id, current_phase["id"])
#         if not stages:
#             print("[DEBUG] advance_stage_if_completed: No stages found in current phase, assuming workflow complete")
#             return True, "Stages not found, assuming workflow complete"

#         stage_ids = [s["id"] for s in stages]
#         try:
#             current_stage_idx = stage_ids.index(current_stagehistory.stage)
#         except ValueError:
#             current_stage_idx = 0

#         print(f"[DEBUG] advance_stage_if_completed: current_stage_idx={current_stage_idx}")

#         current_seq = None
#         for s in stages:
#             if s["id"] == current_stagehistory.stage:
#                 current_seq = s["sequence"]
#                 break

#         print(f"[DEBUG] Current stage sequence: {current_seq}")

#         next_stage = None
#         for s in stages:
#             if s["sequence"] > current_seq:
#                 next_stage = s
#                 break

#         if next_stage:
#             next_phase = current_phase
#             print(f"[DEBUG] Advancing to next stage {next_stage['id']} in current phase {next_phase['id']}")
#         else:
#             current_phase_seq = current_phase["sequence"]
#             next_phase = None
#             phases_sorted = sorted(phases, key=lambda x: x["sequence"])
#             for p in phases_sorted:
#                 if p["sequence"] > current_phase_seq:
#                     next_phase = p
#                     break

#             if not next_phase:
#                 print("[DEBUG] No further phases. Workflow complete.")
#                 return True, "Workflow fully completed"

#             # Get stages for next phase
#             next_stages = self.get_stages(project_id, next_phase["id"])
#             if not next_stages:
#                 print("[DEBUG] No stages in next phase. Workflow complete.")
#                 return True, "No stages in next phase, workflow complete"

#             # Pick lowest sequence stage in next phase
#             next_stage = sorted(next_stages, key=lambda x: x["sequence"])[0]
#             print(f"[DEBUG] Advancing to first stage {next_stage['id']} in next phase {next_phase['id']}")


#         new_stagehistory = StageHistory.objects.create(
#             project=project_id,
#             phase_id=next_phase["id"],
#             stage=next_stage["id"],
#             started_at=timezone.now(),
#             is_current=True,
#             flat=getattr(checklist, "flat_id", None),
#             room=getattr(checklist, "room_id", None),
#             zone=getattr(checklist, "zone_id", None),
#             checklist=checklist if true_level == "checklist_level" else None,
#             status="started",
#         )
#         print(f"[DEBUG] advance_stage_if_completed: Created new StageHistory id={new_stagehistory.id}")

#         return True, {
#             "new_phase_id": next_phase["id"],
#             "new_stage_id": next_stage["id"],
#             "msg": "Advanced to next stage"
#         }

#     def patch(self, request):
#         checklist_item_id = request.data.get('checklist_item_id')
#         role = request.data.get('role')
#         option_id = request.data.get('option_id')

#         print(f"[DEBUG] patch called with checklist_item_id={checklist_item_id}, role={role}, option_id={option_id}")

#         if not checklist_item_id or not role or not option_id:
#             print("[DEBUG] patch: missing required parameters")
#             return Response({"detail": "checklist_item_id, role, and option_id are required."}, status=400)

#         try:
#             item = ChecklistItem.objects.get(id=checklist_item_id)
#             print(f"[DEBUG] patch: fetched ChecklistItem id={item.id}")
#         except ChecklistItem.DoesNotExist:
#             print(f"[DEBUG] patch: ChecklistItem {checklist_item_id} not found")
#             return Response({"detail": "ChecklistItem not found."}, status=404)

#         try:
#             option = ChecklistItemOption.objects.get(id=option_id)
#             print(f"[DEBUG] patch: fetched ChecklistItemOption id={option.id}, choice={option.choice}")
#         except ChecklistItemOption.DoesNotExist:
#             print(f"[DEBUG] patch: ChecklistItemOption {option_id} not found")
#             return Response({"detail": "ChecklistItemOption not found."}, status=404)

#         checklist = item.checklist
#         print(f"[DEBUG] patch: checklist id={checklist.id}")

#         if role.lower() == "checker":
#             check_remark = request.data.get('check_remark', '')
#             check_photo = request.FILES.get('inspector_photo', None)

#             submission = item.submissions.filter(
#                 checker_id=request.user.id,
#                 status="pending_checker"
#             ).order_by('-attempts', '-created_at').first()

#             if not submission:
#                 max_attempts = item.submissions.aggregate(max_attempts=models.Max('attempts'))['max_attempts'] or 0
#                 submission = ChecklistItemSubmission.objects.create(
#                     checklist_item=item,
#                     checker_id=request.user.id,
#                     status="pending_checker",
#                     attempts=max_attempts + 1
#                 )
#                 print(f"[DEBUG] patch: created new submission id={submission.id}")

#             submission.checker_remarks = check_remark
#             submission.checked_at = timezone.now()
#             if check_photo:
#                 submission.inspector_photo = check_photo

#             if option.choice == "P":
#                 # Mark item and submission completed
#                 submission.status = "completed"
#                 item.status = "completed"
#                 submission.save(update_fields=["checker_remarks", "checked_at", "inspector_photo", "status"])
#                 item.save(update_fields=["status"])
#                 print(f"[DEBUG] patch: marked item {item.id} completed")

#                 # If all checklist items completed, mark checklist completed
#                 if not checklist.items.exclude(status="completed").exists():
#                     checklist.status = "completed"
#                     checklist.save(update_fields=["status"])
#                     print(f"[DEBUG] patch: checklist {checklist.id} marked completed")

#                 # Get true_level once and reuse
#                 true_level = self.get_true_level(checklist.project_id)
#                 project_id = checklist.project_id
#                 user_id = request.user.id

#                 # Build StageHistory filter based on true_level
#                 stagehistory_filter = {
#                     "project": project_id,
#                     "is_current": True,
#                 }
#                 if true_level == "flat_level":
#                     stagehistory_filter["flat"] = checklist.flat_id
#                 elif true_level == "room_level":
#                     stagehistory_filter["room"] = checklist.room_id
#                 elif true_level == "zone_level":
#                     stagehistory_filter["zone"] = checklist.zone_id
#                 elif true_level == "level_id":
#                     stagehistory_filter["level_id"] = checklist.level_id
#                 elif true_level == "checklist_level":
#                     stagehistory_filter["checklist"] = checklist.id

#                 current_stagehistory = StageHistory.objects.filter(**stagehistory_filter).first()
#                 if not current_stagehistory:
#                     print("[DEBUG] No current StageHistory found for filtering")
#                     return Response({"detail": "No current StageHistory found for filtering"}, status=400)

#                 # Build checklist filter for checklists in current stage/location group
#                 checklist_filter = {
#                     "project_id": project_id,
#                     "stage_id": current_stagehistory.stage,
#                 }
#                 if true_level == "flat_level":
#                     checklist_filter["flat_id"] = checklist.flat_id
#                 elif true_level == "room_level":
#                     checklist_filter["room_id"] = checklist.room_id
#                 elif true_level == "zone_level":
#                     checklist_filter["zone_id"] = checklist.zone_id
#                 elif true_level == "level_id":
#                     checklist_filter["level_id"] = checklist.level_id
#                 elif true_level == "checklist_level":
#                     checklist_filter["id"] = checklist.id

#                 incomplete_exists = Checklist.objects.filter(**checklist_filter).exclude(status="completed").exists()
#                 all_checklists_completed = not incomplete_exists
#                 print(f"[DEBUG] all_checklists_completed = {all_checklists_completed}")

#                 advanced = False
#                 advancement_info = None

#                 if all_checklists_completed:
#                     stagehistory_filter = {
#                         "project": project_id,
#                         "is_current": True,
#                     }
#                     if true_level == "flat_level":
#                         stagehistory_filter["flat"] = checklist.flat_id
#                     elif true_level == "room_level":
#                         stagehistory_filter["room"] = checklist.room_id
#                     elif true_level == "zone_level":
#                         stagehistory_filter["zone"] = checklist.zone_id
#                     elif true_level == "level_id":
#                         stagehistory_filter["level_id"] = checklist.level_id
#                     elif true_level == "checklist_level":
#                         stagehistory_filter["checklist"] = checklist.id

#                     current_stagehistory = StageHistory.objects.filter(**stagehistory_filter).first()
#                     if not current_stagehistory:
#                         print("[DEBUG] No current StageHistory found")
#                         advanced = False
#                         advancement_info = "No current StageHistory found"
#                     else:
#                         next_stage_api = f"https://konstruct.world/projects/stages/{current_stagehistory.stage}/next/"
                        
#                         headers = {}
#                         auth_header = request.headers.get("Authorization")
#                         if auth_header:
#                             headers["Authorization"] = auth_header
                        
#                         try:
#                             print(f"[DEBUG] Calling next stage API: {next_stage_api} with headers: {headers}")
#                             resp = requests.get(next_stage_api, headers=headers, timeout=5)
#                             print(f"[DEBUG] next stage API response status: {resp.status_code}")
#                             print(f"[DEBUG] next stage API response content: {resp.text}")
#                             data = resp.json()

#                             if data.get("workflow_completed") is True:
#                                 current_stagehistory.is_current = False
#                                 current_stagehistory.completed_at = timezone.now()
#                                 current_stagehistory.completed_by = user_id
#                                 current_stagehistory.status = "completed"
#                                 current_stagehistory.save()
#                                 advanced = True
#                                 advancement_info = "Workflow fully completed"
#                                 print("[DEBUG] Workflow fully completed")

#                             elif data.get("workflow_completed") is False and "detail" in data:
                               
#                                 current_stagehistory.is_current = False
#                                 current_stagehistory.completed_at = timezone.now()
#                                 current_stagehistory.completed_by = user_id
#                                 current_stagehistory.status = "completed"
#                                 current_stagehistory.save()
#                                 advanced = True
#                                 advancement_info = data["detail"]
#                                 print(f"[DEBUG] {data['detail']} - Marked current StageHistory completed")

#                             elif "next_stage_id" in data and "phase_id" in data:
#                                 next_stage_id = data["next_stage_id"]
#                                 next_phase_id = data["phase_id"]

                              
#                                 if next_phase_id == current_stagehistory.phase_id:
#                                     current_stagehistory.status = "move_to_next_stage"
#                                 else:
#                                     current_stagehistory.status = "move_to_next_phase"

#                                 current_stagehistory.is_current = False
#                                 current_stagehistory.completed_at = timezone.now()
#                                 current_stagehistory.completed_by = user_id
#                                 current_stagehistory.save()
#                                 print(f"[DEBUG] Updated StageHistory {current_stagehistory.id} status to {current_stagehistory.status}")

#                                 try:
#                                     new_stagehistory = StageHistory.objects.create(
#                                         project=current_stagehistory.project,
#                                         phase_id=next_phase_id,
#                                         stage=next_stage_id,
#                                         started_at=timezone.now(),
#                                         is_current=True,
#                                         flat=getattr(checklist, "flat_id", None),
#                                         room=getattr(checklist, "room_id", None),
#                                         zone=getattr(checklist, "zone_id", None),
#                                         checklist=checklist if true_level == "checklist_level" else None,
#                                         status="started",
#                                     )
#                                     print(f"[DEBUG] Created new StageHistory id={new_stagehistory.id}")
#                                     advanced = True
#                                     advancement_info = {
#                                         "new_phase_id": next_phase_id,
#                                         "new_stage_id": next_stage_id,
#                                         "msg": "Advanced to next stage",
#                                     }
#                                     flags = get_project_flags(project_id,headers=headers)
#                                     print(f"[DEBUG] checklist_repoetory = {flags.get('checklist_repoetory')} for project {project_id}")

#                                     if flags.get("checklist_repoetory", False):
#                                         true_level = self.get_true_level(project_id)
#                                         print(f"[DEBUG] true_level for project {project_id} = {true_level}")
#                                         group_fk = self._group_filter_kwargs(checklist, true_level)
#                                         print(f"[DEBUG] group_fk for source group: {group_fk}")
#                                         source_group_qs = Checklist.objects.filter(**group_fk)
#                                         print(f"[DEBUG] Found {source_group_qs.count()} checklists in source group")

#                                         if source_group_qs.exists():
#                                             self._clone_group_to_next_stage(
#                                                 source_group_qs=source_group_qs,
#                                                 next_phase_id=next_phase_id,
#                                                 next_stage_id=next_stage_id,
#                                             )
#                                             print(f"[DEBUG] Cloning done into phase={next_phase_id}, stage={next_stage_id}")
#                                         else:
#                                             print("[DEBUG] No source checklists found — skipping clone")

#                                 except Exception as e:
#                                     print(f"[ERROR] Failed to create new StageHistory: {e}")
#                                     advanced = False
#                                     advancement_info = f"Failed to create StageHistory: {e}"

#                             else:
#                                 advanced = False
#                                 advancement_info = data.get("detail", "Invalid next stage/phase data")

#                         except Exception as e:
#                             advanced = False
#                             advancement_info = f"Exception during next stage fetch: {str(e)}"
#                             print(f"[ERROR] Exception during next stage fetch: {str(e)}")
#                 else:
#                     advanced = False
#                     advancement_info = "Not all checklists are completed"


#                 return Response({
#                     "detail": "Item completed.",
#                     "item_id": item.id,
#                     "item_status": item.status,
#                     "submission_id": submission.id,
#                     "submission_status": submission.status,
#                     "checklist_status": checklist.status,
#                     "stage_advanced": advanced,
#                     "advancement_info": advancement_info,
#                 }, status=200)


#             elif option.choice == "N":
#                 submission.status = "rejected_by_checker"
#                 submission.save(update_fields=["checker_remarks", "checked_at", "inspector_photo", "status"])
#                 item.status = "pending_for_maker"
#                 item.save(update_fields=["status"])
#                 print(f"[DEBUG] patch: item {item.id} rejected by checker")

#                 max_attempts = item.submissions.aggregate(max_attempts=models.Max('attempts'))['max_attempts'] or 0
#                 ChecklistItemSubmission.objects.create(
#                     checklist_item=item,
#                     maker_id=submission.maker_id if submission.maker_id else None,
#                     checker_id=submission.checker_id,
#                     supervisor_id=submission.supervisor_id,
#                     attempts=max_attempts + 1,
#                     status="created"
#                 )

#                 checklist.status = "work_in_progress"
#                 checklist.save(update_fields=["status"])
#                 print(f"[DEBUG] patch: checklist {checklist.id} status set to work_in_progress")

#                 return Response({
#                     "detail": "Rejected by checker, sent back to maker.",
#                     "item_id": item.id,
#                     "item_status": item.status,
#                     "checklist_status": checklist.status
#                 }, status=200)

#             else:
#                 print(f"[DEBUG] patch: invalid option choice for checker: {option.choice}")
#                 return Response({"detail": "Invalid option value for checker."}, status=400)

#         elif role.lower() == "supervisor":
#             supervisor_remark = request.data.get('supervisor_remarks', '')
#             supervisor_photo = request.FILES.get('reviewer_photo', None)

#             submission = item.submissions.filter(
#                 supervisor_id=request.user.id,
#                 status="pending_supervisor"
#             ).order_by('-attempts', '-created_at').first()
#             if not submission:
#                 submission = item.submissions.filter(
#                     checker_id__isnull=False,
#                     maker_id__isnull=False,
#                     status="pending_supervisor",
#                     supervisor_id__isnull=True
#                 ).order_by('-attempts', '-created_at').first()
#             if not submission:
#                 print("[DEBUG] patch: no submission found for supervisor action")
#                 return Response({
#                     "detail": (
#                         "No submission found for supervisor action. "
#                         "This usually means the item hasn't been checked by checker or submitted by maker. "
#                         "Please check workflow: Maker must submit, Checker must verify before Supervisor can act."
#                     ),
#                     "item_id": item.id,
#                     "item_status": item.status
#                 }, status=400)

#             if not submission.supervisor_id:
#                 submission.supervisor_id = request.user.id

#             submission.supervisor_remarks = supervisor_remark
#             submission.supervised_at = timezone.now()
#             if supervisor_photo:
#                 submission.reviewer_photo = supervisor_photo

#             true_level = self.get_true_level(checklist.project_id)
#             filter_kwargs = {
#                 "project_id": checklist.project_id,
#                 "stage_id": checklist.stage_id,
#             }
#             if true_level == "flat_level":
#                 filter_kwargs["flat_id"] = checklist.flat_id
#             elif true_level == "room_level":
#                 filter_kwargs["room_id"] = checklist.room_id
#             elif true_level == "zone_level":
#                 filter_kwargs["zone_id"] = checklist.zone_id
#             elif true_level == "level_id":
#                 filter_kwargs["level_id"] = checklist.level_id
#             elif true_level == "checklist_level":
#                 filter_kwargs["id"] = checklist.id

#             print(f"[DEBUG] patch: supervisor filter_kwargs = {filter_kwargs}")

#             checklists_in_group = Checklist.objects.filter(**filter_kwargs)

#             if option.choice == "P":
#                 item.status = "tetmpory_inspctor"
#                 submission.status = "pending_checker"
#                 item.save(update_fields=["status"])
#                 submission.save(update_fields=[
#                     "supervisor_remarks", "supervised_at", "reviewer_photo", "status", "supervisor_id"
#                 ])

#                 group_items = ChecklistItem.objects.filter(checklist__in=checklists_in_group)

#                 all_ready = all(
#                     it.status in ["completed", "tetmpory_inspctor"] for it in group_items
#                 )
#                 print(f"[DEBUG] patch: all_ready for inspector = {all_ready}")
#                 if all_ready:
#                     ChecklistItem.objects.filter(
#                         checklist__in=checklists_in_group,
#                         status="tetmpory_inspctor"
#                     ).update(status="pending_for_inspector")

#                 all_ready = all(
#                     it.status in ["completed", "tetmpory_Maker", "tetmpory_inspctor"]
#                     for it in group_items
#                 )
#                 print(f"[DEBUG] patch: all_ready for maker = {all_ready}")
#                 if all_ready:
#                     ChecklistItem.objects.filter(
#                         checklist__in=checklists_in_group,
#                         status="tetmpory_Maker"
#                     ).update(status="pending_for_maker")

#                 return Response({
#                     "detail": "Sent to inspector.",
#                     "item_id": item.id,
#                     "item_status": item.status,
#                     "submission_id": submission.id,
#                     "submission_status": submission.status,
#                 }, status=200)

#             elif option.choice == "N":
#                 item.status = "tetmpory_Maker"
#                 submission.status = "rejected_by_supervisor"
#                 item.save(update_fields=["status"])
#                 submission.save(update_fields=[
#                     "supervisor_remarks", "supervised_at", "reviewer_photo", "status", "supervisor_id"
#                 ])

#                 group_items = ChecklistItem.objects.filter(checklist__in=checklists_in_group)

#                 max_attempts = item.submissions.aggregate(
#                     max_attempts=models.Max('attempts')
#                 )['max_attempts'] or 0

#                 ChecklistItemSubmission.objects.create(
#                     checklist_item=item,
#                     maker_id=submission.maker_id,
#                     checker_id=submission.checker_id,
#                     supervisor_id=submission.supervisor_id,
#                     attempts=max_attempts + 1,
#                     status="created"
#                 )

#                 checklist.status = "work_in_progress"
#                 checklist.save(update_fields=["status"])

#                 all_ready = all(
#                     it.status in ["completed", "tetmpory_inspctor"] for it in group_items
#                 )
#                 if all_ready:
#                     ChecklistItem.objects.filter(
#                         checklist__in=checklists_in_group,
#                         status="tetmpory_inspctor"
#                     ).update(status="pending_for_inspector")

#                 all_ready = all(
#                     it.status in ["completed", "tetmpory_Maker", "tetmpory_inspctor"]
#                     for it in group_items
#                 )
#                 if all_ready:
#                     ChecklistItem.objects.filter(
#                         checklist__in=checklists_in_group,
#                         status="tetmpory_Maker"
#                     ).update(status="pending_for_maker")

#                 print(f"[DEBUG] patch: item {item.id} rejected by supervisor and sent back to maker")

#                 return Response({
#                     "detail": "Rejected by supervisor, sent back to maker.",
#                     "item_id": item.id,
#                     "item_status": item.status,
#                     "checklist_status": checklist.status
#                 }, status=200)

#             else:
#                 print(f"[DEBUG] patch: invalid option value for supervisor: {option.choice}")
#                 return Response({"detail": "Invalid option value for supervisor."}, status=400)



class StageHistoryListView(ListAPIView):
    """
    GET /api/stage-history/?project=...&zone=...&flat=...&room=...&checklist=...
                                &stage=...&phase_id=...&status=...&is_current=true
                                &ordering=stage,started_at
    """
    serializer_class = StageHistorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # <-- disable pagination

    def get_queryset(self):
        qs = StageHistory.objects.all()
        p = self.request.query_params

        # Build filters from query params (empty values ignored)
        filters = {}
        if p.get("project"):   filters["project"] = p.get("project")
        if p.get("zone"):      filters["zone"] = p.get("zone")
        if p.get("flat"):      filters["flat"] = p.get("flat")
        if p.get("room"):      filters["room"] = p.get("room")
        if p.get("checklist"): filters["checklist_id"] = p.get("checklist")
        if p.get("stage"):     filters["stage"] = p.get("stage")
        if p.get("phase_id"):  filters["phase_id"] = p.get("phase_id")
        if p.get("status"):    filters["status"] = p.get("status")

        is_current = p.get("is_current")
        if is_current is not None and is_current != "":
            # truthy values: 1, true, yes, y, t
            v = str(is_current).strip().lower()
            filters["is_current"] = v in ("1", "true", "t", "yes", "y")

        qs = qs.filter(**filters)

        # Safe ordering support
        ordering = p.get("ordering")
        if ordering:
            allowed = {
                "stage", "-stage",
                "started_at", "-started_at",
                "completed_at", "-completed_at",
                "id", "-id",
            }
            fields = [f.strip() for f in ordering.split(",") if f.strip() in allowed]
            if fields:
                return qs.order_by(*fields)

        # default ordering: stage → started_at → id
        return qs.order_by("stage", "started_at", "id")




class FlatReportAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    BASE_PROJECT_API = "https://konstruct.world/projects"
    BASE_USER_API = "https://konstruct.world/users/users"
    BASE_STAGE_API = "https://konstruct.world/projects/stages"

    def get(self, request, flat_id):
        token = self._get_token(request)

        flat_data = self._get_flat_details(flat_id, token)
        if not flat_data:
            return Response({"error": "Flat not found"}, status=status.HTTP_404_NOT_FOUND)

        checklists = Checklist.objects.filter(flat_id=flat_id)
        project_id = flat_data.get("project")
        true_level = self.get_true_level(project_id)

        data = {
            "flat": flat_data,
            "summary": self._build_summary(checklists),
            "report_date": self._current_date(),
        }

        if true_level == "flat_level":
            # --- GROUP BY STAGE ID ---
            stages = {}
            for checklist in checklists:
                stage_id = checklist.stage_id
                if not stage_id:
                    continue
                if stage_id not in stages:
                    stage_name = self._get_stage_name(stage_id, token)
                    stages[stage_id] = {
                        "stage_id": stage_id,
                        "stage_name": stage_name,
                        "checklists": []
                    }
                checklist_data = self._serialize_checklist(checklist, token)
                stages[stage_id]["checklists"].append(checklist_data)
            # Sort stages by stage_id (optional)
            data["stages"] = sorted(stages.values(), key=lambda x: x["stage_id"])
        else:
            # All your old code for non-flat_level
            data["checklists"] = []
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

    def get_true_level(self, project_id):
        TRANSFER_RULE_API = f"https://konstruct.world/projects/transfer-rules/"
        try:
            resp = requests.get(TRANSFER_RULE_API, params={"project_id": project_id})
            if resp.status_code == 200 and resp.json():
                return resp.json()[0].get("true_level")
        except Exception as e:
            print(f"[ERROR] TransferRule error: {e}")
        return None

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

    def _get_stage_name(self, stage_id, token):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            resp = requests.get(f"{self.BASE_STAGE_API}/{stage_id}/info/", headers=headers)
            if resp.status_code == 200:
                return resp.json().get("stage_name")
        except Exception as e:
            print(f"[ERROR] Could not fetch stage name for {stage_id}: {e}")
        return f"Stage {stage_id}"

    def _serialize_checklist(self, checklist, token):
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
        return checklist_data

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


            q |= (cat_q)

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


# class MAker_DOne_view(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def _get_true_level(self, project_id):
#         try:
#             resp = requests.get(
#                 f"https://{local}/projects/transfer-rules/",
#                 params={"project_id": project_id},
#                 timeout=5,
#             )
#             if resp.status_code == 200 and resp.json():
#                 return resp.json()[0].get("true_level")
#         except Exception:
#             pass
#         return None

#     def _group_filters_for_checklist(self, checklist, true_level):
#         fk = {"project_id": checklist.project_id, "stage_id": checklist.stage_id}
#         if true_level == "flat_level":
#             fk["flat_id"] = checklist.flat_id
#         elif true_level == "room_level":
#             fk["room_id"] = checklist.room_id
#         elif true_level == "zone_level":
#             fk["zone_id"] = checklist.zone_id
#         elif true_level == "level_id":
#             fk["level_id"] = checklist.level_id
#         elif true_level == "checklist_level":
#             fk["id"] = checklist.id
#         return fk

#     @transaction.atomic
#     def post(self, request):
#         checklist_item_id = request.data.get("checklist_item_id")
#         maker_remark = request.data.get("maker_remark", "")
#         maker_media = request.FILES.get("maker_media", None)

#         if not checklist_item_id:
#             return Response({"detail": "checklist_item_id required."}, status=400)

#         # 1) Item must be pending_for_maker
#         try:
#             item = ChecklistItem.objects.select_related("checklist").get(
#                 id=checklist_item_id, status="pending_for_maker"
#             )
#         except ChecklistItem.DoesNotExist:
#             return Response(
#                 {"detail": "ChecklistItem not found or not pending for maker."},
#                 status=404,
#             )

#         checklist = item.checklist
#         project_id = checklist.project_id

#         latest_submission = (
#             ChecklistItemSubmission.objects
#             .filter(checklist_item=item, status="created")
#             .order_by("-attempts", "-created_at")
#             .first()
#         )
#         if not latest_submission:
#             return Response(
#                 {"detail": "No matching submission found for rework."},
#                 status=404,
#             )

#         if not latest_submission.maker_id:
#             latest_submission.maker_id = request.user.id

#         # 3) Decide path based on project flag
#         headers = {}
#         auth_header = request.headers.get("Authorization")
#         if auth_header:
#             headers["Authorization"] = auth_header  # keep full "Bearer ..." as-is

#         flags = get_project_flags(project_id, headers=headers)
#         skip_super = flags.get("skip_supervisory", False)

#         if skip_super:
#             # Bypass supervisor → go straight to checker
#             latest_submission.status = "pending_checker"
#             item.status = "tetmpory_inspctor"
#         else:
#             # Old behavior (Supervisor step)
#             latest_submission.status = "pending_supervisor"
#             item.status = "pending_for_supervisor"

#         # 4) Update maker fields
#         latest_submission.maker_remarks = maker_remark
#         latest_submission.maker_at = timezone.now()
#         if maker_media:
#             latest_submission.maker_media = maker_media

#         latest_submission.save(
#             update_fields=[
#                 "status", "maker_id", "maker_remarks", "maker_media", "maker_at"
#             ]
#         )
#         item.save(update_fields=["status"])

#         if skip_super:
#             true_level = self._get_true_level(project_id)
#             group_fk = self._group_filters_for_checklist(checklist, true_level)
#             checklists_in_group = Checklist.objects.filter(**group_fk)

#             from django.db.models import Q

#             not_ready_for_inspector_exists = ChecklistItem.objects.filter(
#                 checklist__in=checklists_in_group
#             ).exclude(status__in=["completed", "tetmpory_inspctor"]).exists()

#             if not not_ready_for_inspector_exists:
#                 ChecklistItem.objects.filter(
#                     checklist__in=checklists_in_group,
#                     status="tetmpory_inspctor"
#                 ).update(status="pending_for_inspector")

#             not_ready_for_maker_exists = ChecklistItem.objects.filter(
#                 checklist__in=checklists_in_group
#             ).exclude(status__in=["completed", "tetmpory_Maker", "tetmpory_inspctor"]).exists()

#             if not not_ready_for_maker_exists:
#                 ChecklistItem.objects.filter(
#                     checklist__in=checklists_in_group,
#                     status="tetmpory_Maker"
#                 ).update(status="pending_for_maker")

#         item_data = ChecklistItemSerializer(item).data
#         submission_data = {
#             "id": latest_submission.id,
#             "status": latest_submission.status,
#             "maker_remarks": latest_submission.maker_remarks,
#             "maker_media": latest_submission.maker_media.url if latest_submission.maker_media else None,
#             "maker_at": latest_submission.maker_at,
#             "checker_id": latest_submission.checker_id,
#             "maker_id": latest_submission.maker_id,
#             "supervisor_id": latest_submission.supervisor_id,
#         }
#         return Response(
#             {
#                 "item": item_data,
#                 "submission": submission_data,
#                 "detail": "Checklist item marked as done by maker."
#             },
#             status=200
#         )

#     def get(self, request):
#         """
#         Optional: list the maker's submissions (open and recently submitted).
#         Adjust the statuses as per your product needs.
#         """
#         user_id = request.user.id
#         queryset = ChecklistItemSubmission.objects.filter(
#             maker_id=user_id,
#             status__in=["created", "pending_supervisor", "pending_checker"]
#         ).order_by("-created_at")
#         serializer = ChecklistItemSubmissionSerializer(
#             queryset, many=True, context={"request": request}
#         )
#         return Response(serializer.data)


# class MAker_DOne_view(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request):
#         checklist_item_id = request.data.get("checklist_item_id")
#         maker_remark = request.data.get("maker_remark", "")
#         maker_media = request.FILES.get("maker_media", None)

#         if not checklist_item_id:
#             return Response({"detail": "checklist_item_id required."}, status=400)

#         try:
#             item = ChecklistItem.objects.get(
#                 id=checklist_item_id, status="pending_for_maker"
#             )
#         except ChecklistItem.DoesNotExist:
#             return Response({
#                 "detail": "ChecklistItem not found or not pending for maker."
#             }, status=404)

#         latest_submission = (
#             ChecklistItemSubmission.objects
#             .filter(checklist_item=item, status="created")
#             .order_by('-attempts', '-created_at')
#             .first()
#         )

#         if not latest_submission:
#             return Response({
#                 "detail": "No matching submission found for rework."
#             }, status=404)

#         if not latest_submission.maker_id:
#             latest_submission.maker_id = request.user.id

#         latest_submission.status = "pending_supervisor"
#         latest_submission.maker_remarks = maker_remark
#         latest_submission.maker_at = timezone.now()
#         if maker_media:
#             latest_submission.maker_media = maker_media
#         latest_submission.save(update_fields=["status", "maker_id", "maker_remarks", "maker_media", "maker_at"])

#         item.status = "pending_for_supervisor"
#         item.save(update_fields=["status"])

#         # 5. Respond
#         item_data = ChecklistItemSerializer(item).data
#         submission_data = {
#             "id": latest_submission.id,
#             "status": latest_submission.status,
#             "maker_remarks": latest_submission.maker_remarks,
#             "maker_media": latest_submission.maker_media.url if latest_submission.maker_media else None,
#             "maker_at": latest_submission.maker_at,
#             "checker_id": latest_submission.checker_id,
#             "maker_id": latest_submission.maker_id,
#             "supervisor_id": latest_submission.supervisor_id,
#         }
#         return Response({
#             "item": item_data,
#             "submission": submission_data,
#             "detail": "Checklist item marked as done by maker."
#         }, status=200)

#     def get(self, request):
#         user_id = request.user.id
#         queryset = ChecklistItemSubmission.objects.filter(
#             status="pending_for_maker",
#             maker_id=user_id,
#         )
#         serializer = ChecklistItemSubmissionSerializer(
#             queryset, many=True, context={"request": request}
#         )
#         return Response(serializer.data)


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
                continue  

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

