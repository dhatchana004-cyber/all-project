from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status,generics
from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated

from .models import (
    Project, Purpose, Phase, Stage, Building, Level,
    Zone, Flattype, Flat,Subzone,Rooms,    Category, CategoryLevel1, CategoryLevel2, CategoryLevel3,
    CategoryLevel4, CategoryLevel5, CategoryLevel6,TransferRule
)
from .serializers import CategoryTreeSerializer
from .models import AllPurpose, ClientPurpose
from .serializers import AllPurposeSerializer, ClientPurposeSerializer
import requests
from .serializers import (
    ProjectSerializer, PurposeSerializer, PhaseSerializer,
    StageSerializer, BuildingSerializer, LevelSerializer,
    ZoneSerializer, FlattypeSerializer, FlatSerializer,BuildingWithLevelsSerializer,
    BuildingWithLevelsAndZonesSerializer,SubzoneSerializer,BuildingWithLevelsZonesCreateSerializer,
    LevelZoneBulkCreateSerializer,RoomSerializer,
    CategorySerializer, CategoryLevel1Serializer, CategoryLevel2Serializer, CategoryLevel3Serializer,
    CategoryLevel4Serializer, CategoryLevel5Serializer, CategoryLevel6Serializer
    ,BuildingWithAllDetailsSerializer,TransferRuleSerializer,CategorySimpleSerializer,
       CategoryLevel1SimpleSerializer, CategoryLevel2SimpleSerializer,
    CategoryLevel3SimpleSerializer, CategoryLevel4SimpleSerializer,
    CategoryLevel5SimpleSerializer, CategoryLevel6SimpleSerializer

)


USER_SERVICE_URL = "https://konstruct.world/users/"  # To fetch users if needed

# --- Create and List AllPurpose (Superadmin only can list all) ---rializer.save(created_by=self.request.user.id)


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Stage, Phase

class NextStageAPIView(APIView):
    def get(self, request, stage_id):
        try:
            current_stage = Stage.objects.get(id=stage_id)
        except Stage.DoesNotExist:
            return Response({"detail": "Stage not found"}, status=status.HTTP_404_NOT_FOUND)

        # Find next stage in same phase with higher sequence
        next_stage = Stage.objects.filter(
            phase=current_stage.phase,
            sequence__gt=current_stage.sequence,
            is_active=True
        ).order_by('sequence').first()

        if next_stage:
            return Response({
                "next_stage_id": next_stage.id,
                "phase_id": current_stage.phase.id,
                "message": "Next stage in current phase"
            })

        # No next stage in current phase, find next phase with higher sequence
        current_phase = current_stage.phase
        next_phase = Phase.objects.filter(
            project=current_phase.project,
            purpose=current_phase.purpose,
            sequence__gt=current_phase.sequence,
            is_active=True
        ).order_by('sequence').first()

        if next_phase:
            # Find lowest sequence stage in next phase
            lowest_stage = Stage.objects.filter(
                phase=next_phase,
                is_active=True
            ).order_by('sequence').first()

            if lowest_stage:
                return Response({
                    "next_stage_id": lowest_stage.id,
                    "phase_id": next_phase.id,
                    "message": "First stage in next phase"
                })
            else:
                return Response({
                    "detail": "No stages found in next phase",
                    "workflow_completed": False
                }, status=status.HTTP_200_OK)

        # No next phase -> workflow completed
        return Response({
            "workflow_completed": True,
            "message": "Workflow fully completed"
        })

class StageInfoAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, stage_id):
        try:
            stage = Stage.objects.select_related('phase', 'purpose', 'project').get(id=stage_id)
        except Stage.DoesNotExist:
            return Response({'detail': 'Stage not found'}, status=status.HTTP_404_NOT_FOUND)

        # If stage.purpose.name is a FK to ClientPurpose, use .name or str() as appropriate
        # Adjust as per your actual field names
        data = {
            "stage_id": stage.id,
            "stage_name": stage.name,
            "stage_sequence": stage.sequence,
            "phase_id": stage.phase.id if stage.phase else None,
            "phase_name": stage.phase.name if stage.phase else None,
            "purpose_id": stage.purpose.id if stage.purpose else None,
            "purpose_name":  stage.purpose.name.purpose.name if stage.purpose and stage.purpose.name and stage.purpose.name.purpose else None,
            "project_id": stage.project.id if stage.project else None,
            "project_name": stage.project.name if stage.project else None,
        }
        return Response(data, status=200)

class ActivateProjectPurposeView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # Use your admin permission

    def post(self, request, project_id):
        purpose_id = request.data.get("purpose_id")
        if not purpose_id:
            return Response({"error": "purpose_id required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            purpose = Purpose.objects.get(pk=purpose_id, project_id=project_id)
        except Purpose.DoesNotExist:
            return Response({"error": "Purpose not found for this project"}, status=status.HTTP_404_NOT_FOUND)
        Purpose.objects.filter(project_id=project_id).update(is_current=False)
        purpose.is_current = True
        purpose.save()
        return Response({"success": True, "activated_purpose_id": purpose_id})

    def get(self, request, project_id):
        current_purposes = Purpose.objects.filter(project_id=project_id, is_current=True)
        count = current_purposes.count()
        if count == 0:
            return Response({"detail": "No active purpose found for this project."}, status=status.HTTP_404_NOT_FOUND)
        elif count > 1:
            return Response({"detail": "Data integrity error: More than one active purpose found for this project!"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # Exactly one active purpose
        serializer = PurposeSerializer(current_purposes.first())
        return Response(serializer.data)




from .serializers import ProjectDeepCustomSerializer

class ProjectNestedAPIView(APIView):
    def get(self, request, project_id):
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return Response({'detail': 'Project not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProjectDeepCustomSerializer(project)
        return Response(serializer.data, status=status.HTTP_200_OK)



class AllPurposeListCreateAPIView(generics.ListCreateAPIView):
    queryset = AllPurpose.objects.all()
    serializer_class = AllPurposeSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.id)


class ClientPurposeCreateAPIView(generics.CreateAPIView):
    serializer_class = ClientPurposeSerializer
    queryset = ClientPurpose.objects.all()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(assigned_by=self.request.user.id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            print(serializer.errors)  # Prints to your server console
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





class ProjectsByIdsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # or AllowAny if public

    def post(self, request):
        ids = request.data.get("ids")
        if not ids or not isinstance(ids, list):
            return Response({"detail": "List of ids required as 'ids'"}, status=400)
        
        projects = Project.objects.filter(id__in=ids)
        data = ProjectSerializer(projects, many=True).data

        # Return as dict: {id: project_obj}
        result = {str(item['id']): item for item in data}
        return Response(result,status=200)



class ClientPurposeListAPIView(generics.ListAPIView):
    serializer_class = ClientPurposeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        client_id = self.kwargs.get('client_id')
        return ClientPurpose.objects.filter(client_id=client_id, delete=False)


class ClientPurposeSoftDeleteAPIView(APIView):
    def patch(self, request, pk):
        try:
            obj = ClientPurpose.objects.get(pk=pk)
            obj.delete = True
            obj.save()
            return Response({'detail': 'deleted successfully'}, status=200)
        except ClientPurpose.DoesNotExist:
            return Response({'detail': 'Not found'}, status=404)

class CategoryTreeByProjectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get('project')
        if not project_id:
            return Response({'detail': 'Missing project parameter'}, status=400)
        categories = Category.objects.filter(project_id=project_id)
        serializer = CategoryTreeSerializer(categories, many=True)
        print(serializer.data)
        return Response(serializer.data)
    

class OrgProjectUserSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org_ids = Project.objects.values_list('organization_id', flat=True).distinct()
        result = []

        for org_id in org_ids:
            org_data = {"org_id": org_id}
            projects = Project.objects.filter(organization_id=org_id)
            project_list = []
            user_ids = set()
            for project in projects:
                project_list.append({
                    "project_id": project.id,
                    "project_name": project.name,
                    "created_by": project.created_by
                })
                user_ids.add(project.created_by)
            users_data = []
            if user_ids:
                try:
                    resp = requests.get(
                        f"{USER_SERVICE_URL}/users/",
                        params={"ids": ','.join(map(str, user_ids))},
                        timeout=5
                    )
                    if resp.ok:
                        users_data = resp.json()
                except Exception:
                    pass

            org_data["projects"] = project_list
            org_data["project_count"] = len(project_list)
            org_data["user_ids"] = list(user_ids)
            org_data["users"] = users_data  

            result.append(org_data)
        return Response(result)



class CategorySimpleViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySimpleSerializer


class UnitListAPIView(APIView):
    def get(self, request):
        filters = {}
        flat_id = request.query_params.get('flat_id')
        subzone_id = request.query_params.get('subzone_id')
        zone_id = request.query_params.get('zone_id')
        building_id = request.query_params.get('building_id')
        project_id = request.query_params.get('project_id')
        level_id = request.query_params.get('level_id')

        if flat_id:
            filters['id'] = flat_id
        if subzone_id:
            filters['subzone_id'] = subzone_id
        if zone_id:
            filters['zone_id'] = zone_id
        if building_id:
            filters['building_id'] = building_id
        if project_id:
            filters['project_id'] = project_id
        if level_id:
            filters['level_id'] = level_id

        if not filters:
            return Response({
                "error": "At least one identifier (flat_id, subzone_id, zone_id, building_id, project_id, level_id) is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        flats = Flat.objects.filter(**filters).select_related('flattype').prefetch_related('flattype__rooms')

        response_data = []
        for flat in flats:
            rooms = []
            if flat.flattype:
                rooms = [
                    {"id": r.id, "name": r.rooms}
                    for r in flat.flattype.rooms.all()
                ]
            # Include all hierarchy for downstream microservices
            response_data.append({
                "unit_id": flat.id,
                "building_id": flat.building_id if flat.building_id else None,
                "zone_id": flat.zone_id if flat.zone_id else None,
                "subzone_id": flat.subzone_id if flat.subzone_id else None,
                "level_id": flat.level_id if flat.level_id else None,
                "project_id": flat.project_id,
                "rooms": rooms
            })

        return Response({
            "units": response_data
        }, status=status.HTTP_200_OK)


class CategoryLevel1SimpleViewSet(viewsets.ModelViewSet):
    queryset = CategoryLevel1.objects.all()
    serializer_class = CategoryLevel1SimpleSerializer

class CategoryLevel2SimpleViewSet(viewsets.ModelViewSet):
    queryset = CategoryLevel2.objects.all()
    serializer_class = CategoryLevel2SimpleSerializer

class CategoryLevel3SimpleViewSet(viewsets.ModelViewSet):
    queryset = CategoryLevel3.objects.all()
    serializer_class = CategoryLevel3SimpleSerializer

class CategoryLevel4SimpleViewSet(viewsets.ModelViewSet):
    queryset = CategoryLevel4.objects.all()
    serializer_class = CategoryLevel4SimpleSerializer

class CategoryLevel5SimpleViewSet(viewsets.ModelViewSet):
    queryset = CategoryLevel5.objects.all()
    serializer_class = CategoryLevel5SimpleSerializer

class CategoryLevel6SimpleViewSet(viewsets.ModelViewSet):
    queryset = CategoryLevel6.objects.all()
    serializer_class = CategoryLevel6SimpleSerializer

class BulkLevelZonesSubzonesCreateAPIView(APIView):
    def post(self, request):
        serializer = LevelZoneBulkCreateSerializer(data=request.data, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Zones and subzones created successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    



from django.db import transaction
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Project
from .serializers import ProjectSerializer


from django.db import transaction
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Project
from .serializers import ProjectSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    # ----------------------------
    # Helpers
    # ----------------------------
    MAKER_FLAG_CANDIDATES = ("maker_to_chechker", "maker_to_checker", "Maker_to_checker")

    def _maker_attr(self, project: Project):
        """
        Returns the actual attribute name present on the model
        for the maker->checker flag (handles your 'chechker' typo).
        """
        for name in self.MAKER_FLAG_CANDIDATES:
            if hasattr(project, name):
                return name
        return None

    def _maker_value(self, project: Project):
        attr = self._maker_attr(project)
        return getattr(project, attr) if attr else None

    # ----------------------------
    # Standard create + serializer context
    # ----------------------------
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            # Keep your debug print if you like
            print("Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        auth_header = self.request.headers.get('Authorization')
        token = None
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        context['auth_token'] = token
        return context

    # ----------------------------
    # Convenience: read current flags
    # ----------------------------
    @action(detail=True, methods=['get'], url_path='flags')
    def flags(self, request, pk=None):
        project = self.get_object()
        maker_val = self._maker_value(project)
        payload = {
            "id": project.id,
            "skip_supervisory": getattr(project, "skip_supervisory", None),
            "checklist_repoetory": getattr(project, "checklist_repoetory", None),
            # expose both keys for client compatibility; both show the same value
            "maker_to_checker": maker_val,
            "maker_to_chechker": maker_val,
        }
        return Response(payload, status=status.HTTP_200_OK)

    # ----------------------------
    # Enable both main flags (not touching maker flag)
    # ----------------------------
    @action(detail=True, methods=['post'], url_path='enable-all-flags')
    @transaction.atomic
    def enable_all_flags(self, request, pk=None):
        project = self.get_object()
        updated_fields = []

        if hasattr(project, "skip_supervisory") and not project.skip_supervisory:
            project.skip_supervisory = True
            updated_fields.append('skip_supervisory')

        if hasattr(project, "checklist_repoetory") and not project.checklist_repoetory:
            project.checklist_repoetory = True
            updated_fields.append('checklist_repoetory')

        if updated_fields:
            project.save(update_fields=updated_fields)

        return Response(
            {
                "id": project.id,
                "skip_supervisory": getattr(project, "skip_supervisory", None),
                "checklist_repoetory": getattr(project, "checklist_repoetory", None),
                "updated_fields": updated_fields,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='disable-all-flags')
    @transaction.atomic
    def disable_all_flags(self, request, pk=None):
        project = self.get_object()
        updated_fields = []

        if hasattr(project, "skip_supervisory") and project.skip_supervisory:
            project.skip_supervisory = False
            updated_fields.append('skip_supervisory')

        if hasattr(project, "checklist_repoetory") and project.checklist_repoetory:
            project.checklist_repoetory = False
            updated_fields.append('checklist_repoetory')

        if updated_fields:
            project.save(update_fields=updated_fields)

        return Response(
            {
                "id": project.id,
                "skip_supervisory": getattr(project, "skip_supervisory", None),
                "checklist_repoetory": getattr(project, "checklist_repoetory", None),
                "updated_fields": updated_fields,
            },
            status=status.HTTP_200_OK,
        )

    # ----------------------------
    # Skip Supervisory toggles
    # ----------------------------
    @action(detail=True, methods=['post'], url_path='enable-skip-supervisory')
    def enable_skip_supervisory(self, request, pk=None):
        project = self.get_object()
        if not getattr(project, "skip_supervisory", False):
            project.skip_supervisory = True
            project.save(update_fields=['skip_supervisory'])
        return Response({"id": project.id, "skip_supervisory": project.skip_supervisory}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='disable-skip-supervisory')
    def disable_skip_supervisory(self, request, pk=None):
        project = self.get_object()
        if getattr(project, "skip_supervisory", False):
            project.skip_supervisory = False
            project.save(update_fields=['skip_supervisory'])
        return Response({"id": project.id, "skip_supervisory": project.skip_supervisory}, status=status.HTTP_200_OK)

    # ----------------------------
    # Checklist Repoetory toggles
    # ----------------------------
    @action(detail=True, methods=['post'], url_path='enable-checklist-repoetory')
    def enable_checklist_repoetory(self, request, pk=None):
        project = self.get_object()
        if not getattr(project, "checklist_repoetory", False):
            project.checklist_repoetory = True
            project.save(update_fields=['checklist_repoetory'])
        return Response({"id": project.id, "checklist_repoetory": project.checklist_repoetory}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='disable-checklist-repoetory')
    def disable_checklist_repoetory(self, request, pk=None):
        project = self.get_object()
        if getattr(project, "checklist_repoetory", False):
            project.checklist_repoetory = False
            project.save(update_fields=['checklist_repoetory'])
        return Response({"id": project.id, "checklist_repoetory": project.checklist_repoetory}, status=status.HTTP_200_OK)

    # ----------------------------
    # Maker → Checker toggles (robust to field name)
    # ----------------------------
    @action(detail=True, methods=['post'], url_path='enable-maker-to-checker')
    def enable_maker_to_checker(self, request, pk=None):
        project = self.get_object()
        attr = self._maker_attr(project)
        if not attr:
            return Response({"detail": "Maker-to-checker flag not present on Project."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not getattr(project, attr):
            setattr(project, attr, True)
            project.save(update_fields=[attr])
        return Response({"id": project.id, "maker_to_checker": getattr(project, attr)}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='disable-maker-to-checker')
    def disable_maker_to_checker(self, request, pk=None):
        project = self.get_object()
        attr = self._maker_attr(project)
        if not attr:
            return Response({"detail": "Maker-to-checker flag not present on Project."},
                            status=status.HTTP_400_BAD_REQUEST)
        if getattr(project, attr):
            setattr(project, attr, False)
            project.save(update_fields=[attr])
        return Response({"id": project.id, "maker_to_checker": getattr(project, attr)}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='set-maker-to-checker')
    def set_maker_to_checker(self, request, pk=None):
        """
        POST body can be:
          {"value": true/false}  OR  {"maker_to_checker": true/false}  OR  {"maker_to_chechker": true/false}
        Boolean or string-ish truthy ("1","true","yes","y").
        """
        project = self.get_object()
        attr = self._maker_attr(project)
        if not attr:
            return Response({"detail": "Maker-to-checker flag not present on Project."},
                            status=status.HTTP_400_BAD_REQUEST)

        raw = (request.data.get("value",
               request.data.get("maker_to_checker",
               request.data.get("maker_to_chechker"))))

        if raw is None:
            return Response({"detail": "Provide 'value' (bool) or 'maker_to_checker'/'maker_to_chechker'."},
                            status=status.HTTP_400_BAD_REQUEST)

        value = raw if isinstance(raw, bool) else str(raw).strip().lower() in ("1", "true", "yes", "y")
        if getattr(project, attr) != value:
            setattr(project, attr, value)
            project.save(update_fields=[attr])

        return Response({"id": project.id, "maker_to_checker": getattr(project, attr)}, status=status.HTTP_200_OK)



from rest_framework import status

class PurposeViewSet(viewsets.ModelViewSet):
    queryset = Purpose.objects.all()
    serializer_class = PurposeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        project_id = request.data.get('project')
        if not project_id:
            return Response({'error': 'Project is required'}, status=status.HTTP_400_BAD_REQUEST)

        existing_purpose_count = Purpose.objects.filter(project_id=project_id).count()
        set_is_current = (existing_purpose_count == 0)

        data = request.data.copy()
        if set_is_current:
            data['is_current'] = True

        serializer = self.get_serializer(data=data)
        if not serializer.is_valid():
            print("Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=400)
        self.perform_create(serializer)
        return Response(serializer.data, status=201)





class PhaseViewSet(viewsets.ModelViewSet):
    queryset = Phase.objects.all()
    serializer_class = PhaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=400)
        self.perform_create(serializer)
        return Response(serializer.data, status=201)
    
    @action(detail=False, methods=['get'], url_path='by-purpose/(?P<purpose_id>[^/.]+)')
    def by_purpose(self, request, purpose_id=None):
        phases = self.get_queryset().filter(purpose_id=purpose_id)
        serializer = self.get_serializer(phases, many=True)
        return Response(serializer.data)
    

class StageViewSet(viewsets.ModelViewSet):
    queryset = Stage.objects.all()
    serializer_class = StageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=400)
        self.perform_create(serializer)
        return Response(serializer.data, status=201)

class BuildingViewSet(viewsets.ModelViewSet):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer
    permission_classes = [permissions.IsAuthenticated]
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=400)
        self.perform_create(serializer)
        return Response(serializer.data, status=201)


class LevelViewSet(viewsets.ModelViewSet):
    queryset = Level.objects.all()
    serializer_class = LevelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=400)
        self.perform_create(serializer)
        return Response(serializer.data, status=201)

class ZoneViewSet(viewsets.ModelViewSet):
    queryset = Zone.objects.all()
    serializer_class = ZoneSerializer
    permission_classes = [permissions.IsAuthenticated]
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=400)
        self.perform_create(serializer)
        return Response(serializer.data, status=201)

class FlattypeViewSet(viewsets.ModelViewSet):
    queryset = Flattype.objects.all()
    serializer_class = FlattypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=400)
        self.perform_create(serializer)
        return Response(serializer.data, status=201)


import traceback
class FlatViewSet(viewsets.ModelViewSet):
    queryset = Flat.objects.all()
    serializer_class = FlatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            print("Exception occurred while saving Flat:", str(e))
            traceback.print_exc()  # This prints the full stack trace
            return Response(
                {"error": "Internal Server Error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PurposeListByProject(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, project_id):
        purpose = Purpose.objects.filter(project__id=project_id)
        serializer = PurposeSerializer(purpose, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class PhaseListByProject(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, project_id):
        phases = Phase.objects.filter(project__id=project_id)
        serializer = PhaseSerializer(phases, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PhaseCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PhaseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StageListByProject(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, project_id):
        stage = Stage.objects.filter(phase__project__id=project_id)
        serializer = StageSerializer(stage, many=True)
        print(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PurposeListByProject(APIView):
    def get(self, request, project_id):
        purposes = Purpose.objects.filter(project_id=project_id)
        serializer = PurposeSerializer(purposes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PhaseListByProject(APIView):
    def get(self, request, project_id):
        phases = Phase.objects.filter(project_id=project_id)
        serializer = PhaseSerializer(phases, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

# Stages by Phase
class StageListByPhase(APIView):
    def get(self, request, phase_id):
        stages = Stage.objects.filter(phase_id=phase_id)
        serializer = StageSerializer(stages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

# Buildings by Project
class BuildingListByProject(APIView):
    def get(self, request, project_id):
        # print(project_id,'projectiddd')
        buildings = Building.objects.filter(project_id=project_id)
        serializer = BuildingSerializer(buildings, many=True)
        # print(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


# Levels by Building
class LevelListByBuilding(APIView):
    def get(self, request, building_id):
        levels = Level.objects.filter(building_id=building_id)
        serializer = LevelSerializer(levels, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

# Zones by Building
class ZoneListByBuilding(APIView):
    def get(self, request, building_id):
        zones = Zone.objects.filter(building_id=building_id)
        serializer = ZoneSerializer(zones, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

# Zones by Level
class ZoneListByLevel(APIView):
    def get(self, request, level_id):
        zones = Zone.objects.filter(level_id=level_id)
        serializer = ZoneSerializer(zones, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

# Flattype by Project
class FlattypeListByProject(APIView):
    def get(self, request, project_id):
        flattypes = Flattype.objects.filter(project_id=project_id)
        serializer = FlattypeSerializer(flattypes, many=True)
        print(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)

class FLatssbyProjectId(APIView):
    def get(self,request,project_id):
        flats=Flat.objects.filter(project=project_id)
        serizlizer=FlatSerializer(flats,many=True)
        print(serizlizer.data)
        return Response(serizlizer.data,status=status.HTTP_200_OK)

# Flat by Building
class FlatListByBuilding(APIView):
    def get(self, request, building_id):
        flats = Flat.objects.filter(building_id=building_id)
        serializer = FlatSerializer(flats, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

# Flat by Level
class FlatListByLevel(APIView):
    def get(self, request, level_id):
        flats = Flat.objects.filter(level_id=level_id)
        serializer = FlatSerializer(flats, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

# Flat by Flattype
class FlatListByFlattype(APIView):
    def get(self, request, flattype_id):
        flats = Flat.objects.filter(flattype_id=flattype_id)
        serializer = FlatSerializer(flats, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

# class GetProjectsByUser(APIView):
#     def get(self, request):
#         user_id = request.GET.get('user_id')
#         if not user_id:
#             return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
#         projects = Project.objects.filter(created_by=user_id)
#         serializer = ProjectSerializer(projects, many=True)
#         print(serializer.data)
#         return Response(serializer.data, status=status.HTTP_200_OK)
    
class GetProjectsByUser(APIView):
    permission_classes = [IsAuthenticated]  

    def get(self, request):
        user = request.user 
        projects = Project.objects.filter(created_by=user.id) 
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    

class BuildingWithLevelsByProject(APIView):
    def get(self, request, project_id):
        buildings = Building.objects.filter(project_id=project_id)
        serializer = BuildingWithLevelsSerializer(buildings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class BuildingsWithLevelsAndZonesByProject(APIView):
    def get(self, request, project_id):
        buildings = Building.objects.filter(project_id=project_id)
        serializer = BuildingWithLevelsAndZonesSerializer(buildings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class NestedBuildingCreateView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = BuildingWithLevelsAndZonesSerializer(data=request.data, many=True)
        if serializer.is_valid():
            serializer.save() 
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubzoneViewSet(viewsets.ModelViewSet):
    queryset = Subzone.objects.all()
    serializer_class = SubzoneSerializer

    @action(detail=True, methods=['get'])
    def subzones(self, request, pk=None):
        subzones = Subzone.objects.filter(zone_id=pk)
        serializer = SubzoneSerializer(subzones, many=True)
        return Response(serializer.data)




class BulkLevelZonesSubzonesCreateAPIView(APIView):
    def post(self, request):
        serializer = LevelZoneBulkCreateSerializer(data=request.data, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Zones and subzones created successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Rooms.objects.all()
    serializer_class = RoomSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=400)
        self.perform_create(serializer)
        return Response(serializer.data, status=201)
    
    @action(detail=False, methods=['get'])
    def by_project(self, request):
        project_id = request.query_params.get('project_id')
        if not project_id:
            return Response({"error": "project_id is required."}, status=400)
        rooms = Rooms.objects.filter(Project_id=project_id)
        serializer = self.get_serializer(rooms, many=True)
        return Response(serializer.data)


class CreatedByMixin:
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.id)


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Default: Only return categories created by the current user.
        """
        return Category.objects.filter(created_by=self.request.user.id)

    @action(detail=True, methods=['get'], url_path='detail')
    def get_category_detail(self, request, pk=None):
        """
        Custom action: Get category by ID (ignores created_by filter)
        Example: /categories/<id>/detail/
        """
        category = Category.objects.filter(pk=pk).first()
        if not category:
            return Response({"error": "Category not found"}, status=404)

        serializer = self.get_serializer(category)
        return Response(serializer.data)

#class CategoryViewSet(CreatedByMixin, viewsets.ModelViewSet):
#    serializer_class = CategorySerializer
#    permission_classes = [IsAuthenticated]
#
#    def get_queryset(self):
#        return Category.objects.filter(created_by=self.request.user.id)

class CategoryLevel1ViewSet(CreatedByMixin, viewsets.ModelViewSet):
    serializer_class = CategoryLevel1Serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CategoryLevel1.objects.filter(created_by=self.request.user.id)
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset

class CategoryLevel2ViewSet(CreatedByMixin, viewsets.ModelViewSet):
    serializer_class = CategoryLevel2Serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CategoryLevel2.objects.filter(created_by=self.request.user.id)
        level1_id = self.request.query_params.get('category_level1')
        if level1_id:
            queryset = queryset.filter(category_level1_id=level1_id)
        return queryset

class CategoryLevel3ViewSet(CreatedByMixin, viewsets.ModelViewSet):
    serializer_class = CategoryLevel3Serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CategoryLevel3.objects.filter(created_by=self.request.user.id)
        level2_id = self.request.query_params.get('category_level2')
        if level2_id:
            queryset = queryset.filter(category_level2_id=level2_id)
        return queryset

class CategoryLevel4ViewSet(CreatedByMixin, viewsets.ModelViewSet):
    serializer_class = CategoryLevel4Serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CategoryLevel4.objects.filter(created_by=self.request.user.id)
        level3_id = self.request.query_params.get('category_level3')
        if level3_id:
            queryset = queryset.filter(category_level3_id=level3_id)
        return queryset

class CategoryLevel5ViewSet(CreatedByMixin, viewsets.ModelViewSet):
    serializer_class = CategoryLevel5Serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CategoryLevel5.objects.filter(created_by=self.request.user.id)
        level4_id = self.request.query_params.get('category_level4')
        if level4_id:
            queryset = queryset.filter(category_level4_id=level4_id)
        return queryset

class CategoryLevel6ViewSet(CreatedByMixin, viewsets.ModelViewSet):
    serializer_class = CategoryLevel6Serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CategoryLevel6.objects.filter(created_by=self.request.user.id)
        level5_id = self.request.query_params.get('category_level5')
        if level5_id:
            queryset = queryset.filter(category_level5_id=level5_id)
        return queryset



# Fetch full category tree by project_id
class CategoriesByProjectView(APIView):
    def get(self, request, project_id):
        queryset = Category.objects.filter(project_id=project_id)
        serializer = CategorySerializer(queryset, many=True)
        return Response(serializer.data)
    
class BuildingToFlatsByProject(APIView):
    def get(self, request, project_id):
        buildings = Building.objects.filter(project_id=project_id)
        serializer = BuildingWithAllDetailsSerializer(buildings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


from .serializers import LevelWithFlatsSerializer

class LevelsWithFlatsByBuilding(APIView):
    def get(self, request, building_id):
        levels = Level.objects.filter(building_id=building_id).order_by('id')
        serializer = LevelWithFlatsSerializer(levels, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TransferRuleViewSet(viewsets.ModelViewSet):
    queryset = TransferRule.objects.all()
    serializer_class = TransferRuleSerializer

    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return self.queryset.filter(project__id=project_id)
        return self.queryset

    def create(self, request, *args, **kwargs):
        project_id = request.data.get("project_id") or request.data.get("project")
        if not project_id:
            return Response({"message": "Project ID is required"}, status=400)
        obj, created = TransferRule.objects.update_or_create(
            project_id=project_id,
            defaults={
                "flat_level": request.data.get("flat_level", False),
                "room_level": request.data.get("room_level", False),
                "checklist_level": request.data.get("checklist_level", False),
                "question_level": request.data.get("question_level", True),
            },
        )
        serializer = self.get_serializer(obj)
        return Response({"message": "Saved!", "data": serializer.data}, status=200)
    

class ProjectsByIdsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # or AllowAny if public

    def post(self, request):
        ids = request.data.get("ids")
        if not ids or not isinstance(ids, list):
            return Response({"detail": "List of ids required as 'ids'"}, status=400)
        
        projects = Project.objects.filter(id__in=ids)
        data = ProjectSerializer(projects, many=True).data

        # Return as dict: {id: project_obj}
        result = {str(item['id']): item for item in data}
        return Response(result,status=200)


class ProjectsByOrganizationView(APIView):
    def get(self, request, organization_id):
        projects = Project.objects.filter(organization_id=organization_id)
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data)
    

class ProjectsByOwnershipParamView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        entity_id = request.query_params.get('entity_id')
        company_id = request.query_params.get('company_id')
        organization_id = request.query_params.get('organization_id')

        if entity_id:
            projects = Project.objects.filter(entity_id=entity_id)
        elif company_id:
            projects = Project.objects.filter(company_id=company_id)
        elif organization_id:
            projects = Project.objects.filter(organization_id=organization_id)
        else:
            projects = Project.objects.none()

        serializer = ProjectSerializer(projects, many=True)
        print(serializer.data)
        return Response(serializer.data)












