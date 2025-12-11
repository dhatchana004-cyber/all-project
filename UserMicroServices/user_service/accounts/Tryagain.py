from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from .models import User, UserAccess, UserAccessRole
from rest_framework import generics, permissions

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email', 'phone_number',  # Added first_name and last_name
            'has_access', 'is_client', 'is_manager',
            'org', 'company', 'entity','password','created_by'
        ]
        extra_kwargs = {
            'password': {'write_only': True}  
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        created_by = validated_data.pop('created_by', None)
        user = User(**validated_data)
        if created_by:
            user.created_by= created_by  # <-- THIS IS CORRECT
        if password:
            user.set_password(password)
        user.save()
        return user


    def update(self, instance, validated_data):
            password = validated_data.pop('password', None)
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            if password:
                instance.set_password(password) 
            instance.save()
            return instance

class UserAccessRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAccessRole
        fields = [ 'role']


class UserAccessSerializer(serializers.ModelSerializer):
    roles = UserAccessRoleSerializer(many=True, read_only=True)
    class Meta:
        model = UserAccess
        fields = [
            'id',
            'user',
            'project_id',
            'building_id',
            'zone_id',
            'flat_id',
            'active',
            'created_at',
	     'All_checklist',
            'category',
            'purpose_id',
            'phase_id',
            'stage_id',
'all_cat',
            'CategoryLevel1',
            'CategoryLevel2',
            'CategoryLevel3',
            'CategoryLevel4',
            'CategoryLevel5',
            'CategoryLevel6',
            'roles',
        ]





class UserAccessWithRolesCreateSerializer(serializers.ModelSerializer):
    roles = UserAccessRoleSerializer(many=True, write_only=True)
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = UserAccess
        fields = [
            'user_id',
            'project_id', 'building_id', 'zone_id', 'flat_id',
            'active', 'category', 'CategoryLevel1', 'roles'
        ]

    def validate_user_id(self, value):
        if not User.objects.filter(pk=value).exists():
            raise serializers.ValidationError("User with this id does not exist.")
        return value

    def create(self, validated_data):
        roles_data = validated_data.pop('roles')
        user_id = validated_data.pop('user_id')
        user = User.objects.get(pk=user_id)
        user_access = UserAccess.objects.create(user=user, **validated_data)
        roles = [UserAccessRole.objects.create(user_access=user_access, **role_data) for role_data in roles_data]
        return {
            "access": user_access,
            "roles": roles,
            "user": user
        }

import requests
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    BASE_API_URL = "https://konstruct.world/projects"  # All endpoints under /projects

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Basic user info
        token['user_id'] = user.id
        token['username'] = user.username
        token['email'] = user.email
        token['phone_number'] = user.phone_number
        token['has_access'] = user.has_access
        token['is_client'] = user.is_client
        token['is_manager'] = user.is_manager
        token['org'] = user.org
        token['company'] = user.company
        token['entity'] = user.entity
        token['superadmin'] = user.is_staff

        user_roles = []
        accesses_list = []

        # Get token string for authenticated requests
        auth_token = str(token.access_token)

        def fetch_data(endpoint, pk, detail=False):
            """Fetch either name or full detail"""
            if not pk:
                return None

            # Add detail endpoint for categories
            if endpoint == "categories" and detail:
                url = f"{cls.BASE_API_URL}/{endpoint}/{pk}/detail/"
            elif endpoint == "projects":
                url = f"{cls.BASE_API_URL}/projects/{pk}/"
            else:
                url = f"{cls.BASE_API_URL}/{endpoint}/{pk}/"

            headers = {"Authorization": f"Bearer {auth_token}"}

            try:
                resp = requests.get(url, headers=headers, timeout=3)
                if resp.status_code == 200:
                    return resp.json() if detail else (
                        resp.json().get("name") or resp.json().get("number") or resp.json().get("title")
                    )
                else:
                    print(f"FAILED: {url}, status={resp.status_code}, error={resp.text}")
            except Exception as e:
                print(f"Failed to fetch {endpoint}/{pk}: {e}")
            return None

        # Build the access list
        for access in user.accesses.all():
            roles = [role.role for role in access.roles.all()]
            user_roles.extend(roles)

            access_data = {
                "project_id": access.project_id,
                "project_name": fetch_data("projects", access.project_id),

                "building_id": access.building_id,
                "building_name": fetch_data("buildings", access.building_id),

                "zone_id": access.zone_id,
                "zone_name": fetch_data("zones", access.zone_id),

                "flat_id": access.flat_id,
                "flat_name": fetch_data("flats", access.flat_id),

                "category": access.category,
                # Fetch full detail of category
                "category_detail": fetch_data("categories", access.category, detail=True),

                "category_level1": access.CategoryLevel1,
                "category_level1_name": fetch_data("category-level1", access.CategoryLevel1),

                "category_level2": access.CategoryLevel2,
                "category_level2_name": fetch_data("category-level2", access.CategoryLevel2),

                "category_level3": access.CategoryLevel3,
                "category_level3_name": fetch_data("category-level3", access.CategoryLevel3),

                "category_level4": access.CategoryLevel4,
                "category_level4_name": fetch_data("category-level4", access.CategoryLevel4),

                "category_level5": access.CategoryLevel5,
                "category_level5_name": fetch_data("category-level5", access.CategoryLevel5),

                "category_level6": access.CategoryLevel6,
                "category_level6_name": fetch_data("category-level6", access.CategoryLevel6),

                "roles": roles,
                "active": access.active,
            }

            accesses_list.append(access_data)

        token['roles'] = list(set(user_roles))
        token['accesses'] = accesses_list

        return token


class UserWithAccessesSerializer(serializers.ModelSerializer):
    accesses = UserAccessSerializer(many=True, read_only=True)
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'accesses']

    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Get user roles
        user_roles = []
        for access in self.user.accesses.all():
            for role in access.roles.all():
                user_roles.append(role.role)
        
        data['user'] = {
            'user_id': self.user.id,
            'username': self.user.username,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'email': self.user.email,
            'phone_number': self.user.phone_number,
            'date_joined': self.user.date_joined.strftime("%Y-%m-%d"),
            'last_login': self.user.last_login.strftime("%Y-%m-%d") if self.user.last_login else None,
            'has_access': self.user.has_access,
            'is_client': self.user.is_client,
            'is_manager': self.user.is_manager,
            'org': self.user.org,
            'company': self.user.company,
            'entity': self.user.entity,
            'superadmin': self.user.is_staff,
            'roles': list(set(user_roles))  # Add actual roles array
        }
        return data
    
from rest_framework import serializers

class UserAccessCreateSerializer(serializers.ModelSerializer):
    # Mark optional
    All_checklist = serializers.BooleanField(required=False)
    purpose_id = serializers.IntegerField(required=False, allow_null=True)
    phase_id = serializers.IntegerField(required=False, allow_null=True)
    stage_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = UserAccess
        fields = [
            'project_id',
            'building_id',
            'zone_id',
            'flat_id',
            'active',
            'All_checklist',
            'purpose_id',
            'phase_id',
            'stage_id',
            'category',
            'CategoryLevel1',
            'CategoryLevel2',
            'CategoryLevel3',
            'CategoryLevel4',
            'CategoryLevel5',
            'CategoryLevel6',
        ]
        extra_kwargs = {
            'All_checklist': {'required': False},
            'purpose_id': {'required': False, 'allow_null': True},
            'phase_id':  {'required': False, 'allow_null': True},
            'stage_id':  {'required': False, 'allow_null': True},
        }

    # Optional: convert "" → None so omitted/blank dropdowns don’t fail
    def validate(self, attrs):
        for k in ('purpose_id', 'phase_id', 'stage_id'):
            if attrs.get(k) == "":
                attrs[k] = None
        return attrs

from django.db import transaction
from rest_framework import serializers

class UserAccessFullSerializer(serializers.Serializer):
    user = UserSerializer()
    access = UserAccessCreateSerializer()
    roles = UserAccessRoleSerializer(many=True)

    def create(self, validated_data):
        with transaction.atomic():
            user_data = validated_data.pop('user')
            access_data = validated_data.pop('access')
            roles_data = validated_data.pop('roles')

            # Create user first
            user_serializer = UserSerializer()
            user = user_serializer.create(user_data)

            # Ensure optional fields have defaults if omitted
            access_data.setdefault('All_checklist', False)
            access_data.setdefault('purpose_id', None)
            access_data.setdefault('phase_id', None)
            access_data.setdefault('stage_id', None)

            # Create access
            user_access = UserAccess.objects.create(user=user, **access_data)

            # Create roles
            role_objs = []
            for role in roles_data:
                role_obj = UserAccessRole.objects.create(user_access=user_access, **role)
                role_objs.append(role_obj)

            return {
                "user": user,
                "access": user_access,
                "roles": role_objs
            }
