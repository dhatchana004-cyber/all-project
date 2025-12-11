from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User, UserAccess, UserAccessRole


# ---------------------------
# User
# ---------------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "has_access",
            "is_client",
            "is_manager",
            "org",
            "company",
            "entity",
            "password",
            "created_by",
        ]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        created_by = validated_data.pop("created_by", None)
        user = User(**validated_data)
        if created_by:
            user.created_by = created_by
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


# ---------------------------
# Roles
# ---------------------------
class UserAccessRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAccessRole
        fields = ["role"]


# ---------------------------
# Access (READ)
# ---------------------------
class UserAccessSerializer(serializers.ModelSerializer):
    roles = UserAccessRoleSerializer(many=True, read_only=True)

    class Meta:
        model = UserAccess
        fields = [
            "id",
            "user",
            "project_id",
            "building_id",
            "zone_id",
            "flat_id",
            "active",
            "created_at",
            "All_checklist",
            "all_cat",  # <- expose all_cat
            "category",
            "purpose_id",
            "phase_id",
            "stage_id",
            "CategoryLevel1",
            "CategoryLevel2",
            "CategoryLevel3",
            "CategoryLevel4",
            "CategoryLevel5",
            "CategoryLevel6",
            "roles",
        ]


# ---------------------------
# Access + Roles (CREATE, simple)
# ---------------------------
class UserAccessWithRolesCreateSerializer(serializers.ModelSerializer):
    roles = UserAccessRoleSerializer(many=True, write_only=True)
    user_id = serializers.IntegerField(write_only=True)
    all_cat = serializers.BooleanField(required=False)  # <- allow writing all_cat

    class Meta:
        model = UserAccess
        fields = [
            "user_id",
            "project_id",
            "building_id",
            "zone_id",
            "flat_id",
            "active",
            "all_cat",
            "category",
            "CategoryLevel1",
            "roles",
        ]

    def validate_user_id(self, value):
        if not User.objects.filter(pk=value).exists():
            raise serializers.ValidationError("User with this id does not exist.")
        return value

    def create(self, validated_data):
        roles_data = validated_data.pop("roles", [])
        user_id = validated_data.pop("user_id")
        user = User.objects.get(pk=user_id)

        # defaults
        validated_data.setdefault("all_cat", False)

        user_access = UserAccess.objects.create(user=user, **validated_data)
        roles = [
            UserAccessRole.objects.create(user_access=user_access, **role_data)
            for role_data in roles_data
        ]
        return {"access": user_access, "roles": roles, "user": user}


# ---------------------------
# JWT Token payload (adds roles + accesses)
# ---------------------------
import requests


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    # Base host; all endpoints are under /projects/...
    BASE_API_URL = "https://konstruct.world/projects"

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Basic user info
        token["user_id"] = user.id
        token["username"] = user.username
        token["email"] = user.email
        token["phone_number"] = user.phone_number
        token["has_access"] = user.has_access
        token["is_client"] = user.is_client
        token["is_manager"] = user.is_manager
        token["org"] = user.org
        token["company"] = user.company
        token["entity"] = user.entity
        token["superadmin"] = user.is_staff

        user_roles = []
        accesses_list = []

        # Use the access token to call external services
        auth_token = str(token.access_token)

        def fetch_data(endpoint, pk, detail=False):
            """
            Fetch either name or full detail for the given endpoint + pk.
            All endpoints live under /projects/ on the external host.
            """
            if not pk:
                return None

            if endpoint == "categories" and detail:
                url = f"{cls.BASE_API_URL}/projects/categories/{pk}/detail/"
            elif endpoint == "projects":
                url = f"{cls.BASE_API_URL}/projects/{pk}/"
            else:
                url = f"{cls.BASE_API_URL}/projects/{endpoint}/{pk}/"

            headers = {"Authorization": f"Bearer {auth_token}"}
            try:
                resp = requests.get(url, headers=headers, timeout=3)
                if resp.status_code == 200:
                    if detail:
                        return resp.json()
                    data = resp.json()
                    # Try to pick a meaningful label
                    return data.get("name") or data.get("number") or data.get("title")
                else:
                    print(f"FAILED: {url}, status={resp.status_code}, error={resp.text}")
            except Exception as e:
                print(f"Failed to fetch {endpoint}/{pk}: {e}")
            return None

        # Build access list
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

                # all-cat switch
                "all_cat": access.all_cat,

                # legacy single-category path (kept for backward compatibility)
                "category": access.category,
                "category_detail": fetch_data("categories", access.category, detail=True),

                "category_level1": access.CategoryLevel1,
                "category_level1_name": fetch_data(
                    "category-level1", access.CategoryLevel1
                ),

                "category_level2": access.CategoryLevel2,
                "category_level2_name": fetch_data(
                    "category-level2", access.CategoryLevel2
                ),

                "category_level3": access.CategoryLevel3,
                "category_level3_name": fetch_data(
                    "category-level3", access.CategoryLevel3
                ),

                "category_level4": access.CategoryLevel4,
                "category_level4_name": fetch_data(
                    "category-level4", access.CategoryLevel4
                ),

                "category_level5": access.CategoryLevel5,
                "category_level5_name": fetch_data(
                    "category-level5", access.CategoryLevel5
                ),

                "category_level6": access.CategoryLevel6,
                "category_level6_name": fetch_data(
                    "category-level6", access.CategoryLevel6
                ),

                "roles": roles,
                "active": access.active,
            }

            # Optional: give clients a quick hint
            if access.all_cat:
                access_data["categories"] = "ALL"
            else:
                access_data["categories"] = [
                    {
                        "category_id": access.category,
                        "level1": access.CategoryLevel1,
                        "level2": access.CategoryLevel2,
                        "level3": access.CategoryLevel3,
                        "level4": access.CategoryLevel4,
                        "level5": access.CategoryLevel5,
                        "level6": access.CategoryLevel6,
                    }
                ]

            accesses_list.append(access_data)

        token["roles"] = list(set(user_roles))
        token["accesses"] = accesses_list
        return token


# ---------------------------
# Access (CREATE/UPDATE minimal)
# ---------------------------
class UserAccessCreateSerializer(serializers.ModelSerializer):
    # optional flags/fields
    All_checklist = serializers.BooleanField(required=False)
    all_cat = serializers.BooleanField(required=False)
    purpose_id = serializers.IntegerField(required=False, allow_null=True)
    phase_id = serializers.IntegerField(required=False, allow_null=True)
    stage_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = UserAccess
        fields = [
            "project_id",
            "building_id",
            "zone_id",
            "flat_id",
            "active",
            "All_checklist",
            "all_cat",  # <- allow writing all_cat
            "purpose_id",
            "phase_id",
            "stage_id",
            "category",
            "CategoryLevel1",
            "CategoryLevel2",
            "CategoryLevel3",
            "CategoryLevel4",
            "CategoryLevel5",
            "CategoryLevel6",
        ]
        extra_kwargs = {
            "All_checklist": {"required": False},
            "purpose_id": {"required": False, "allow_null": True},
            "phase_id": {"required": False, "allow_null": True},
            "stage_id": {"required": False, "allow_null": True},
        }

    # convert "" -> None for optional ints
    def validate(self, attrs):
        for k in ("purpose_id", "phase_id", "stage_id"):
            if attrs.get(k) == "":
                attrs[k] = None
        return attrs


# ---------------------------
# Combined create: user + access + roles
# ---------------------------
class UserAccessFullSerializer(serializers.Serializer):
    user = UserSerializer()
    access = UserAccessCreateSerializer()
    roles = UserAccessRoleSerializer(many=True)

    def create(self, validated_data):
        with transaction.atomic():
            user_data = validated_data.pop("user")
            access_data = validated_data.pop("access")
            roles_data = validated_data.pop("roles")

            # Create user
            user_serializer = UserSerializer()
            user = user_serializer.create(user_data)

            # Ensure defaults
            access_data.setdefault("All_checklist", False)
            access_data.setdefault("all_cat", False)
            access_data.setdefault("purpose_id", None)
            access_data.setdefault("phase_id", None)
            access_data.setdefault("stage_id", None)

            # Create access
            user_access = UserAccess.objects.create(user=user, **access_data)

            # Create roles
            role_objs = []
            for role in roles_data:
                role_obj = UserAccessRole.objects.create(
                    user_access=user_access, **role
                )
                role_objs.append(role_obj)

            return {"user": user, "access": user_access, "roles": role_objs}
