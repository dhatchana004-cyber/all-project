from rest_framework import serializers
from django.db.models import Q
from django.db import models
from .models import (
    Project, Purpose, Phase, Stage, Building, Level,
    Zone, Flattype, Flat,Subzone,Rooms,
    Category, CategoryLevel1, CategoryLevel2, CategoryLevel3,
    CategoryLevel4, CategoryLevel5, CategoryLevel6,TransferRule,AllPurpose, ClientPurpose
)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests

ORGANIZATION_SERVICE_URL = "http://127.0.0.1:8002/api/organizations/"
COMPANY_SERVICE_URL = "http://127.0.0.1:8002/api/companies/"
ENTITY_SERVICE_URL = "http://127.0.0.1:8002/api/entities/"
USER_SERVICE_URL = "http://127.0.0.1:8000/api/users/"

class AllPurposeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AllPurpose
        fields = ['id', 'name', 'created_by', 'created_at']
        read_only_fields = ['created_by', 'created_at']


class ClientPurposeSerializer(serializers.ModelSerializer):
    purpose = AllPurposeSerializer(read_only=True)
    purpose_id = serializers.PrimaryKeyRelatedField(queryset=AllPurpose.objects.all(), source='purpose', write_only=True)
    class Meta:
        model = ClientPurpose
        fields = ['id', 'client_id', 'purpose', 'purpose_id', 'assigned_by', 'assigned_at']
        read_only_fields = ['assigned_by', 'assigned_at']


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'

    def validate(self, data):
        token = self.context.get('auth_token') 
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        org_id = data.get('organization_id')
        comp_id = data.get('company_id')
        ent_id = data.get('entity_id')
        created_by = data.get('created_by')

        # Exactly one of org/company/entity must be set
        ids = [bool(org_id), bool(comp_id), bool(ent_id)]
        if sum(ids) < 1:
            raise serializers.ValidationError("Atleast one of organization_id, company_id, or entity_id must be set.")

        if org_id:
            url = f"{ORGANIZATION_SERVICE_URL}{org_id}/"
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                raise serializers.ValidationError({"organization_id": "Organization does not exist."})

        if comp_id:
            url = f"{COMPANY_SERVICE_URL}{comp_id}/"
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                raise serializers.ValidationError({"company_id": "Company does not exist."})

        if ent_id:
            url = f"{ENTITY_SERVICE_URL}{ent_id}/"
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                raise serializers.ValidationError({"entity_id": "Entity does not exist."})

        if created_by:
            url = f"{USER_SERVICE_URL}{created_by}/"
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                raise serializers.ValidationError({"created_by": "User does not exist."})
        return data
    

# class PurposeSerializer(serializers.ModelSerializer):
#     name = ClientPurposeSerializer(read_only=True)
#     name_id = serializers.PrimaryKeyRelatedField(
#         queryset=ClientPurpose.objects.all(),
#         source='name',
#         write_only=True
#     )

#     class Meta:
#         model = Purpose
#         fields = ['id', 'project', 'name', 'name_id', 'is_active']

class PurposeSerializer(serializers.ModelSerializer):
    name = ClientPurposeSerializer(read_only=True)
    name_id = serializers.PrimaryKeyRelatedField(
        queryset=ClientPurpose.objects.none(),  # Will be filtered per request
        source='name',
        write_only=True
    )

    class Meta:
        model = Purpose
        fields = ['id', 'project', 'name', 'name_id', 'is_active','is_current']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        
        print(f"🔍 SERIALIZER DEBUG - Request exists: {request is not None}")
        
        if request:
            print(f"🔍 SERIALIZER DEBUG - Request method: {request.method}")
            print(f"🔍 SERIALIZER DEBUG - Request path: {request.path}")
            print(f"🔍 SERIALIZER DEBUG - Request user: {request.user}")
            print(f"🔍 SERIALIZER DEBUG - User is authenticated: {request.user.is_authenticated}")
            
            if hasattr(request, 'user') and request.user.is_authenticated:
                # Try multiple ways to get client_id
                user_client_id = None
                
                # Method 1: Direct client_id field
                if hasattr(request.user, 'client_id'):
                    user_client_id = request.user.client_id
                    print(f"🔍 SERIALIZER DEBUG - Found client_id in user: {user_client_id}")
                
                # Method 2: Use user.id as client_id (common pattern)
                if not user_client_id:
                    user_client_id = request.user.id
                    print(f"🔍 SERIALIZER DEBUG - Using user.id as client_id: {user_client_id}")
                
                # Method 3: Try to get from URL parameters
                if not user_client_id and hasattr(request, 'resolver_match'):
                    url_kwargs = getattr(request.resolver_match, 'kwargs', {})
                    user_client_id = url_kwargs.get('client_id') or url_kwargs.get('user_id')
                    print(f"🔍 SERIALIZER DEBUG - Found in URL kwargs: {user_client_id}")
                
                print(f"🔍 SERIALIZER DEBUG - Final user_client_id: {user_client_id}")
                
                if user_client_id:
                    # Filter ClientPurposes by this client_id
                    queryset = ClientPurpose.objects.filter(client_id=user_client_id)
                    all_client_purposes = list(queryset.values('id', 'client_id', 'purpose__name'))
                    print(f"🔍 SERIALIZER DEBUG - Available ClientPurposes: {all_client_purposes}")
                    print(f"🔍 SERIALIZER DEBUG - ClientPurpose count: {queryset.count()}")
                    
                    # Check if ClientPurpose ID 10 exists in this queryset
                    cp_10_exists = queryset.filter(id=10).exists()
                    print(f"🔍 SERIALIZER DEBUG - ClientPurpose ID 10 exists: {cp_10_exists}")
                    
                    self.fields['name_id'].queryset = queryset
                else:
                    print("🔍 SERIALIZER DEBUG - No client_id found, using empty queryset")
                    self.fields['name_id'].queryset = ClientPurpose.objects.none()
            else:
                print("🔍 SERIALIZER DEBUG - User not authenticated or no user")
                self.fields['name_id'].queryset = ClientPurpose.objects.none()
        else:
            print("🔍 SERIALIZER DEBUG - No request found")
            self.fields['name_id'].queryset = ClientPurpose.objects.none()
            
        # Final queryset check
        final_queryset = self.fields['name_id'].queryset
        print(f"🔍 SERIALIZER DEBUG - Final queryset count: {final_queryset.count()}")
        print(f"🔍 SERIALIZER DEBUG - Final queryset IDs: {list(final_queryset.values_list('id', flat=True))}")
        
class PhaseSerializer(serializers.ModelSerializer):
    purpose = PurposeSerializer(read_only=True)
    purpose_id = serializers.PrimaryKeyRelatedField(
        queryset=Purpose.objects.all(),
        source='purpose',
        write_only=True
    )

    class Meta:
        model = Phase
        fields = ['id', 'project', 'purpose', 'purpose_id', 'name', 'is_active','sequence']



class StageSerializer(serializers.ModelSerializer):
    purpose = PurposeSerializer(read_only=True)
    purpose_id = serializers.PrimaryKeyRelatedField(
        queryset=Purpose.objects.all(),
        source='purpose',
        write_only=True
    )

    class Meta:
        model = Stage
        fields = ['id','project','purpose', 'purpose_id', 'phase', 'name', 'sequence', 'is_active']



class SubzoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subzone
        fields = ['id', 'zone', 'name']


class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = ['id', 'name', 'building']




class FlattypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flattype
        fields = ['id', 'project', 'rooms', 'type_name']


class FlatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flat
        fields = ['id', 'project', 'building', 'level', 'flattype', 'number']


class FlatTypeMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flattype
        fields = ['id', 'type_name']

class FlatMiniSerializer(serializers.ModelSerializer):
    flattype = FlatTypeMiniSerializer(read_only=True)

    class Meta:
        model = Flat
        fields = ['id', 'number', 'flattype']

class LevelWithFlatsSerializer(serializers.ModelSerializer):
    flats = serializers.SerializerMethodField()

    class Meta:
        model = Level
        fields = ['id', 'name', 'flats']

    def get_flats(self, obj):
        flats = obj.flat_set.select_related('flattype').all()
        return FlatMiniSerializer(flats, many=True).data





class PhaseListByProject(APIView):
    def get(self, request, project_id):
        try:
            phases = Phase.objects.filter(project_id=project_id)
            serializer = PhaseSerializer(phases, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Project.DoesNotExist:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        
class BuildingWithLevelsSerializer(serializers.ModelSerializer):
    levels = LevelSerializer(many=True, source='level_set', read_only=True)
    
    class Meta:
        model = Building
        fields = ['id', 'name', 'levels']


class ZoneWithSubzonesSerializer(serializers.ModelSerializer):
    subzones = SubzoneSerializer(many=True, read_only=True)
    class Meta:
        model = Zone
        fields = ['id', 'building', 'level', 'name', 'subzones']


class LevelWithZonesSerializer(serializers.ModelSerializer):
    zones = ZoneWithSubzonesSerializer(many=True, source='zone_set', read_only=True)
    class Meta:
        model = Level
        fields = ['id', 'name', 'zones']

class BuildingWithLevelsAndZonesSerializer(serializers.ModelSerializer):
    levels = LevelWithZonesSerializer(many=True, source='level_set', read_only=True)
    class Meta:
        model = Building
        fields = ['id', 'name', 'levels']


class BuildingWithLevelsZonesCreateSerializer(serializers.ModelSerializer):
    levels = LevelSerializer(many=True, required=False)

    class Meta:
        model = Building
        fields = ['id', 'name', 'project', 'levels']

    def create(self, validated_data):
        levels_data = validated_data.pop('levels', [])
        building = Building.objects.create(**validated_data)
        for level_data in levels_data:
            zones_data = level_data.pop('zones', [])
            level = Level.objects.create(building=building, **level_data)
            for zone_data in zones_data:
                subzones_data = zone_data.pop('subzones', [])
                zone = Zone.objects.create(building=building, level=level, **zone_data)
                for subzone_data in subzones_data:
                    Subzone.objects.create(zone=zone, **subzone_data)
        return building


class SubzoneCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subzone
        fields = ["name"]

class ZoneCreateSerializer(serializers.ModelSerializer):
    subzones = SubzoneCreateSerializer(many=True, required=False)

    class Meta:
        model = Zone
        fields = ["name", "subzones"]

class LevelZoneBulkCreateSerializer(serializers.Serializer):
    level = serializers.PrimaryKeyRelatedField(queryset=Level.objects.all())
    zones = ZoneCreateSerializer(many=True)

    def create(self, validated_data):
        level = validated_data["level"]
        zones_data = validated_data.get("zones", [])
        created_zones = []
        for zone_data in zones_data:
            subzones_data = zone_data.pop("subzones", [])
            zone = Zone.objects.create(
                name=zone_data["name"],
                building=level.building,
                level=level,
            )
            for subzone_data in subzones_data:
                Subzone.objects.create(
                    name=subzone_data["name"],
                    zone=zone,
                )
            created_zones.append(zone)
        return {"level": level, "zones": created_zones}



class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rooms
        fields = '__all__'


class CategorySimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name','project']

class CategoryLevel1SimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryLevel1
        fields = ['id', 'name', 'category', 'created_by']

class CategoryLevel2SimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryLevel2
        fields = ['id', 'name', 'category_level1', 'created_by']

class CategoryLevel3SimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryLevel3
        fields = ['id', 'name', 'category_level2', 'created_by']

class CategoryLevel4SimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryLevel4
        fields = ['id', 'name', 'category_level3', 'created_by']

class CategoryLevel5SimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryLevel5
        fields = ['id', 'name', 'category_level4', 'created_by']

class CategoryLevel6SimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryLevel6
        fields = ['id', 'name', 'category_level5', 'created_by']



class CategoryLevel6Serializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryLevel6
        fields = ['id', 'name','category_level5','created_by']

class CategoryLevel5Serializer(serializers.ModelSerializer):
    level6 = CategoryLevel6Serializer(many=True, read_only=True)

    class Meta:
        model = CategoryLevel5
        fields = ['id', 'name', 'level6']

class CategoryLevel4Serializer(serializers.ModelSerializer):
    level5 = CategoryLevel5Serializer(many=True, read_only=True)

    class Meta:
        model = CategoryLevel4
        fields = ['id', 'name', 'level5']

class CategoryLevel3Serializer(serializers.ModelSerializer):
    level4 = CategoryLevel4Serializer(many=True, read_only=True)

    class Meta:
        model = CategoryLevel3
        fields = ['id', 'name', 'level4']

class CategoryLevel2Serializer(serializers.ModelSerializer):
    level3 = CategoryLevel3Serializer(many=True, read_only=True)

    class Meta:
        model = CategoryLevel2
        fields = ['id', 'name', 'level3']

class CategoryLevel1Serializer(serializers.ModelSerializer):
    level2 = CategoryLevel2Serializer(many=True, read_only=True)

    class Meta:
        model = CategoryLevel1
        fields = ['id', 'name', 'level2']

class CategorySerializer(serializers.ModelSerializer):
    level1 = CategoryLevel1Serializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'level1']




class ZoneWithFlatsSerializer(serializers.ModelSerializer):
    flats = serializers.SerializerMethodField()

    class Meta:
        model = Zone
        fields = ['id', 'name', 'level', 'building', 'flats']

    def get_flats(self, obj):
        # You may need to adjust this if you have a direct relation, otherwise filter by level/building/zone
        flats = Flat.objects.filter(level=obj.level, building=obj.building)
        return FlatSerializer(flats, many=True).data

class LevelWithZonesAndFlatsSerializer(serializers.ModelSerializer):
    zones = ZoneWithFlatsSerializer(many=True, source='zone_set', read_only=True)

    class Meta:
        model = Level
        fields = ['id', 'name', 'zones']

class BuildingWithAllDetailsSerializer(serializers.ModelSerializer):
    levels = LevelWithZonesAndFlatsSerializer(many=True, source='level_set', read_only=True)

    class Meta:
        model = Building
        fields = ['id', 'name', 'levels']




class TransferRuleSerializer(serializers.ModelSerializer):
    true_level = serializers.SerializerMethodField()

    class Meta:
        model = TransferRule
        fields = [
            'id', 'project', 'flat_level', 'room_level',
            'checklist_level', 'question_level', 'Zone_level',
            'true_level'   # Include the new field
        ]

    def get_true_level(self, obj):
        for field in ['flat_level', 'room_level', 'checklist_level', 'question_level', 'Zone_level']:
            if getattr(obj, field):
                return field
        return None


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ['id', 'name']

class BuildingSerializer(serializers.ModelSerializer):
    zones = ZoneSerializer(many=True, source='zone_set', read_only=True)

    class Meta:
        model = Building
        fields = ['id', 'name','project', 'zones']

class ProjectSerializer(serializers.ModelSerializer):
    buildings = BuildingSerializer(many=True, source='building_set', read_only=True)
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'organization_id', 'company_id', 'entity_id', 'image', 'created_by','buildings','skip_supervisory','checklist_repoetory',
'maker_to_chechker',
        ]


class CategoryLevel6TreeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryLevel6
        fields = ['id', 'name']

class CategoryLevel5TreeSerializer(serializers.ModelSerializer):
    level6 = CategoryLevel6TreeSerializer(many=True, read_only=True)
    class Meta:
        model = CategoryLevel5
        fields = ['id', 'name', 'level6']

class CategoryLevel4TreeSerializer(serializers.ModelSerializer):
    level5 = CategoryLevel5TreeSerializer(many=True, read_only=True)
    class Meta:
        model = CategoryLevel4
        fields = ['id', 'name', 'level5']

class CategoryLevel3TreeSerializer(serializers.ModelSerializer):
    level4 = CategoryLevel4TreeSerializer(many=True, read_only=True)
    class Meta:
        model = CategoryLevel3
        fields = ['id', 'name', 'level4']

class CategoryLevel2TreeSerializer(serializers.ModelSerializer):
    level3 = CategoryLevel3TreeSerializer(many=True,  read_only=True)
    class Meta:
        model = CategoryLevel2
        fields = ['id', 'name', 'level3']

class CategoryLevel1TreeSerializer(serializers.ModelSerializer):
    level2 = CategoryLevel2TreeSerializer(many=True, read_only=True)
    class Meta:
        model = CategoryLevel1
        fields = ['id', 'name', 'level2']

class CategoryTreeSerializer(serializers.ModelSerializer):
    level1 = CategoryLevel1TreeSerializer(many=True,  read_only=True)
    class Meta:
        model = Category
        fields = ['id', 'name', 'level1']



class FlattypeSerializerWithrooms(serializers.ModelSerializer):
    rooms = RoomSerializer(many=True, read_only=True)
    class Meta:
        model = Flattype
        fields = ['id', 'type_name', 'rooms']


class SubzoneWithFlatsSerializer(serializers.ModelSerializer):
    flats = serializers.SerializerMethodField()
    class Meta:
        model = Subzone
        fields = ['id', 'name', 'flats']
    def get_flats(self, obj):
        flats = Flat.objects.filter(subzone=obj)
        return FlatMiniSerializer(flats, many=True).data

# -- Zone: Subzones OR direct flats if no subzone --
class ZoneWithSubzonesAndFlatsSerializer(serializers.ModelSerializer):
    subzones = serializers.SerializerMethodField()
    flats = serializers.SerializerMethodField()
    class Meta:
        model = Zone
        fields = ['id', 'name', 'subzones', 'flats']
    def get_subzones(self, obj):
        subzones = obj.subzones.all()
        # Only include subzones with at least one flat
        subzones = [sz for sz in subzones if Flat.objects.filter(subzone=sz).exists()]
        return SubzoneWithFlatsSerializer(subzones, many=True).data
    def get_flats(self, obj):
        # Flats directly assigned to this zone but not to any subzone
        flats = Flat.objects.filter(zone=obj, subzone__isnull=True)
        return FlatMiniSerializer(flats, many=True).data

# -- Level: Zones or direct flats if no zone --
class LevelNestedSerializer(serializers.ModelSerializer):
    zones = serializers.SerializerMethodField()
    flats = serializers.SerializerMethodField()
    class Meta:
        model = Level
        fields = ['id', 'name', 'zones', 'flats']
    def get_zones(self, obj):
        zones = Zone.objects.filter(level=obj)
        # Only include zones that have at least one flat (either direct or via subzone)
        zone_list = []
        for zone in zones:
            has_flats = (
                Flat.objects.filter(zone=zone, subzone__isnull=True).exists() or
                any(Flat.objects.filter(subzone=subzone).exists() for subzone in zone.subzones.all())
            )
            if has_flats:
                zone_list.append(zone)
        return ZoneWithSubzonesAndFlatsSerializer(zone_list, many=True).data
    def get_flats(self, obj):
        # Flats not assigned to any zone or subzone for this level
        flats = Flat.objects.filter(level=obj, zone__isnull=True, subzone__isnull=True)
        return FlatMiniSerializer(flats, many=True).data

# -- Building with custom Levels --
class BuildingWithCustomLevelsSerializer(serializers.ModelSerializer):
    levels = LevelNestedSerializer(many=True, source='level_set', read_only=True)
    class Meta:
        model = Building
        fields = ['id', 'name', 'levels']

# -- Project with buildings --
class ProjectDeepCustomSerializer(serializers.ModelSerializer):
    buildings = BuildingWithCustomLevelsSerializer(many=True, source='building_set', read_only=True)
    class Meta:
        model = Project
        fields = ['id', 'name', 'organization_id', 'company_id', 'entity_id', 'image', 'created_by', 'buildings']
