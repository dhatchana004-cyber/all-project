
import copy
from collections import defaultdict
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.hashers import make_password
from django.contrib.auth.tokens import default_token_generator
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from django.db.models import Q
import requests


from deepface import DeepFace
from .models import StaffAttendance, StaffRegistration
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import StaffRegistration, StaffAttendance
from .serializers import StaffAttendanceSerializer
from deepface import DeepFace

class StaffAttendanceListCreateView(generics.GenericAPIView):
    serializer_class = StaffAttendanceSerializer
    parser_classes = [MultiPartParser, FormParser]



    def post(self, request):
        try:
            staff_id = request.data.get("staff")
            staff_image = request.FILES.get("staff_image")
            check_in = request.data.get("check_in")

            staff = StaffRegistration.objects.get(id=staff_id)

            # Attendance save
            attendance = StaffAttendance.objects.create(
                staff=staff,
                staff_image=staff_image,
                check_in=check_in,
                date=request.data.get("date")
            )

            # Compare two images (DeepFace)
            try:
                result = DeepFace.verify(
                    img1_path=staff.profile_photo.path,     # Registration image
                    img2_path=attendance.staff_image.path,  # Attendance image
                    model_name='Facenet',
                )

                if result["verified"]:
                    return Response({"message": f"✅ Welcome {staff.first_name}! Attendance marked successfully."},
                                    status=status.HTTP_200_OK)
                else:
                    return Response({"message": "❌ Face mismatch detected! Attendance not marked."},
                                    status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                return Response({"error": f"Face compare failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)







from .models import User, UserAccess, UserAccessRole
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserSerializer,
    UserAccessSerializer,
    UserAccessRoleSerializer,
    UserAccessFullSerializer,
    UserAccessWithRolesCreateSerializer,
    UserWithAccessesSerializer,
)

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import StaffRegistration
from .serializers import StaffRegistrationSerializer
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from rest_framework import generics
from rest_framework.parsers import MultiPartParser, FormParser
from .models import StaffRegistration
from .serializers import StaffRegistrationSerializer


class StaffListCreateView(generics.ListCreateAPIView):
    queryset = StaffRegistration.objects.all()
    serializer_class = StaffRegistrationSerializer
    parser_classes = [MultiPartParser, FormParser]

class StaffDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = StaffRegistration.objects.all()
    serializer_class = StaffRegistrationSerializer
    parser_classes = [MultiPartParser, FormParser]

PROJECT_SERVICE_URL = "https://konstruct.world/projects/"
ORG_SERVICE_URL = "https://konstruct.world/organizations/"
USER_SERVICE_URL = "https://konstruct.world/users/"
CHECKLIST_SERVICE_URL = "https://konstruct.world/checklists/"

from django.utils.http import urlsafe_base64_decode
from rest_framework import status


class PasswordResetConfirmView(APIView):
    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not uid or not token or not new_password:
            return Response({'detail': 'uid, token, and new_password are required.'}, status=400)

        try:
            uid = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'detail': 'Invalid UID.'}, status=400)

        if not default_token_generator.check_token(user, token):
            return Response({'detail': 'Invalid or expired token.'}, status=400)

        user.set_password(new_password)
        user.save()
        return Response({'detail': 'Password reset successful.'}, status=200)


# accounts/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from rest_framework import status

class PasswordResetRequestView(APIView):
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'detail': 'Email is required.'}, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'detail': 'User with this email does not exist.'}, status=400)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f"{request.build_absolute_uri('/reset-password/')}?uid={uid}&token={token}"

        send_mail(
            'Password Reset',
            f'Click the link to reset your password: {reset_url}',
            'noreply@yourdomain.com',
            [user.email],
            fail_silently=False,
        )
        return Response({'detail': 'Password reset link sent to email.'})


PROJECT_SERVICE_URL = "https://konstruct.world/projects/"
ORG_SERVICE_URL = "https://konstruct.world/organizations/"
USER_SERVICE_URL = "https://konstruct.world/users/"
CHECKLIST_SERVICE_URL = "https://konstruct.world/checklists/"

def fetch_checklist_analytics(user_id, project_id, role, auth_token):
    try:
        resp = requests.get(
            f"{CHECKLIST_SERVICE_URL}/checklist-analytics/",
            params={"user_id": user_id, "project_id": project_id, "role": role},
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


class ClientUserListAPIView(generics.ListAPIView):
    serializer_class = UserSerializer

    def get_queryset(self):
        return User.objects.filter(is_client=True, has_access=True)


def fetch_org_project_user_summary(auth_token):
    try:    
        resp = requests.get(
            f"{PROJECT_SERVICE_URL}/org-project-user-summary/",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


class UserDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        auth_token = request.META.get(
            "HTTP_AUTHORIZATION", "").replace(
            "Bearer ", "")
        dashboard = {}

        if user.is_staff or user.is_manager:
            total_users = User.objects.count()
            total_makers = UserAccessRole.objects.filter(role="MAKER").count()
            total_checkers = UserAccessRole.objects.filter(
                role="CHECKER").count()
            try:
                projects_resp = requests.get(
                    f"{PROJECT_SERVICE_URL}/projects/",
                    headers={
                        "Authorization": f"Bearer {auth_token}"},
                    timeout=5)
                total_projects = len(projects_resp.json())
            except Exception:
                total_projects = None
            try:
                checklists_resp = requests.get(
                    f"{CHECKLIST_SERVICE_URL}/checklists/",
                    headers={
                        "Authorization": f"Bearer {auth_token}"},
                    timeout=5)
                total_checklists = len(checklists_resp.json())
            except Exception:
                total_checklists = None

            org_summary = fetch_org_project_user_summary(auth_token)
            dashboard.update({
                "role": "SUPER_ADMIN" if user.is_staff else "MANAGER",
                "total_users": total_users,
                "total_projects": total_projects,
                "total_makers": total_makers,
                "total_checkers": total_checkers,
                "total_checklists": total_checklists,
                "org_project_user_summary": org_summary,  
            })

        elif user.is_client:
            try:
                projects_resp = requests.get(
                    f"{PROJECT_SERVICE_URL}/projects/?created_by={user.id}",
                    headers={
                        "Authorization": f"Bearer {auth_token}"},
                    timeout=5)
                user_projects = projects_resp.json()
            except Exception:
                user_projects = []
            dashboard.update({
                "role": "CLIENT",
                "created_projects": user_projects,
                "created_project_count": len(user_projects),
            })

        else:
            accesses = UserAccess.objects.filter(user=user, active=True)
            roles_data = []
            for access in accesses:
                project_id = access.project_id
                for role in access.roles.values_list("role", flat=True):
                    if role not in [
                        "SUPERVISOR",
                        "MAKER",
                        "CHECKER",
                            "Intializer"]:
                        continue
                    analytics = fetch_checklist_analytics(
                        user.id, project_id, role, auth_token)
                    roles_data.append({
                        "project_id": project_id,
                        "role": role,
                        "analytics": analytics
                    })
            dashboard.update({
                "role": "USER",
                "projects_roles_analytics": roles_data
            })

        org_count = 0
        company_count = 0
        entity_count = 0
        try:
            org_resp = requests.get(
                f"{ORG_SERVICE_URL}/organizations/?created_by={user.id}",
                headers={
                    "Authorization": f"Bearer {auth_token}"},
                timeout=5)
            if org_resp.ok:
                org_count = len(org_resp.json())
        except Exception:
            pass

        dashboard.update({
            "organizations_created": org_count,
            "companies_created": company_count,
            "entities_created": entity_count,
        })
        print(dashboard)
        return Response({
            "user_id": user.id,
            "dashboard": dashboard,
        })


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=400)
        self.perform_create(serializer)
        return Response(serializer.data, status=201)


class UserAccessViewSet(viewsets.ModelViewSet):
    queryset = UserAccess.objects.all()
    serializer_class = UserAccessSerializer
    permission_classes = [permissions.IsAuthenticated]


class UserAccessRoleViewSet(viewsets.ModelViewSet):
    queryset = UserAccessRole.objects.all()
    serializer_class = UserAccessRoleSerializer
    permission_classes = [permissions.IsAuthenticated]


class CustomTokenView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from copy import deepcopy


class UserAccessFullPatchView(APIView):
    """
    PATCH /api/v2/users/access-full/<user_id>/

    Accepts a payload like:
    {
      "user": {...},                 # optional
      "access": {...},               # optional (targeted by access.id or project_id)
      "roles": [{"role": "CHECKER"}] # optional (replaces roles for that access)
    }
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, user_id: int):
        data = deepcopy(request.data)

        with transaction.atomic():
            # 1) USER
            user = get_object_or_404(User, pk=user_id)

            if "user" in data and isinstance(data["user"], dict):
                user_payload = data["user"].copy()

                # handle password specially
                raw_password = user_payload.pop("password", None)

                user_ser = UserSerializer(user, data=user_payload, partial=True)
                user_ser.is_valid(raise_exception=True)
                user = user_ser.save()

                if raw_password:
                    user.set_password(raw_password)
                    user.save(update_fields=["password"])

            # 2) ACCESS (by access.id OR project_id)
            access_obj = None
            access_ser = None

            if "access" in data and isinstance(             data["access"], dict):
                access_payload = data["access"].copy()
                access_id = access_payload.get("id")
                project_id = access_payload.get("project_id")

                if access_id:
                    access_obj = get_object_or_404(UserAccess, pk=access_id, user=user)
                elif project_id is not None:
                    access_obj = UserAccess.objects.filter(user=user, project_id=project_id).first()
                    if access_obj is None:
                        # create an access row if not present
                        access_obj = UserAccess.objects.create(user=user, project_id=project_id)

                if access_obj:
                    # make sure we never try to swap the linked user via payload
                    access_payload["user"] = user.id
                    access_ser = UserAccessSerializer(access_obj, data=access_payload, partial=True)
                    access_ser.is_valid(raise_exception=True)
                    access_ser.save()

            # 3) ROLES (replace set for the access we just patched/created)
            roles_ser = []
            if "roles" in data and isinstance(data["roles"], list) and access_obj:
                incoming_roles = [r.get("role") for r in data["roles"] if isinstance(r, dict) and r.get("role")]
                incoming_roles = list({str(r).upper() for r in incoming_roles})  # normalize & dedupe

                existing_roles = set(
                    UserAccessRole.objects.filter(user_access=access_obj).values_list("role", flat=True)
                )

                # add missing
                to_add = [UserAccessRole(user_access=access_obj, role=r) for r in incoming_roles if r not in existing_roles]
                if to_add:
                    UserAccessRole.objects.bulk_create(to_add)

                # remove extras
                UserAccessRole.objects.filter(user_access=access_obj).exclude(role__in=incoming_roles).delete()

                roles_qs = UserAccessRole.objects.filter(user_access=access_obj).order_by("role")
                roles_ser = UserAccessRoleSerializer(roles_qs, many=True).data

            # Build response
            resp = {
                "user": UserSerializer(user).data,
                "access": access_ser.data if access_ser else (
                    UserAccessSerializer(access_obj).data if access_obj else None
                ),
                "roles": roles_ser if roles_ser else None,
            }
            return Response(resp, status=status.HTTP_200_OK)


class UserAccessFullCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        mutable_data = copy.deepcopy(request.data)

        # Extract raw password from nested 'user' dictionary
        raw_password = None
        if "user" in request.data:
            raw_password = request.data["user"].get("password")

        # Set password into mutable_data if available
        if raw_password:
            if "user" in mutable_data:
                mutable_data["user"]["password"] = raw_password
            else:
                mutable_data["password"] = raw_password

        # Set created_by
        if "user" in mutable_data:
            mutable_data["user"]["created_by"] = request.user.id
        else:
            mutable_data["created_by"] = request.user.id

        # ✅ Ensure all_cat default (False) so create accepts/propagates it
        if "access" in mutable_data:
            mutable_data["access"].setdefault("all_cat", False)

        serializer = UserAccessFullSerializer(data=mutable_data)
        if serializer.is_valid():
            objs = serializer.save()
            user = objs["user"]
            user_email = user.email
            user_name = user.username
            project = objs["access"].project_id
            user_fullname = user.get_full_name() or user.username

            # --- Password Reset Link ---
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"https://konstruct.world/users/password-reset?uid={uid}&token={token}"

            email_subject = "Welcome to Project Portal"
            email_body = f"""
Hello {user_fullname},

Your account has been created!

Username: {user_name}
Password: {raw_password or "N/A"}
Project ID: {project}

To set your password, click the link below:
{reset_url}

If you did not request this account, please ignore this email.

Thanks,
Your Team
"""

            try:
                send_mail(
                    subject=email_subject,
                    message=email_body,
                    from_email=None,  # uses DEFAULT_FROM_EMAIL from settings.py
                    recipient_list=[user_email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Failed to send email: {e}")

            return Response({
                "user": UserSerializer(user).data,
                "access": UserAccessSerializer(objs["access"]).data,
                "roles": UserAccessRoleSerializer(objs["roles"], many=True).data,
                "email_sent": True,
                "reset_link": reset_url,
            }, status=status.HTTP_201_CREATED)
        else:
            print("UserAccessFullSerializer validation errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserAccessListByUserView(APIView):
    def get(self, request, user_id):
        accesses = UserAccess.objects.filter(user__id=user_id)
        serializer = UserAccessSerializer(accesses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserAccessRoleDeleteView(APIView):
    def delete(self, request, user_id, role_id):
        try:
            user_access_role = UserAccessRole.objects.select_related(
                'user_access').get(id=role_id)
            if user_access_role.user_access.user.id != user_id:
                return Response(
                    {'detail': 'Role does not belong to this user.'}, status=status.HTTP_403_FORBIDDEN)
            user_access_role.delete()
            return Response({'detail': 'Role deleted successfully.'},
                            status=status.HTTP_204_NO_CONTENT)
        except UserAccessRole.DoesNotExist:
            return Response({'detail': 'Role not found.'},
                            status=status.HTTP_404_NOT_FOUND)


class AddRolesToUserAccessView(APIView):
    def post(self, request, access_id):
        """ Expects: { "roles": [ { "role": "ADMIN" }, { "role": "CHECKER" } ] } """
        try:
            user_access = UserAccess.objects.get(id=access_id)
        except UserAccess.DoesNotExist:
            return Response({'detail': 'UserAccess not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        roles_data = request.data.get('roles')
        if not isinstance(roles_data, list) or not roles_data:
            return Response({'detail': 'roles must be a non-empty list'},
                            status=status.HTTP_400_BAD_REQUEST)

        created_roles = []
        errors = []
        for role_data in roles_data:
            serializer = UserAccessRoleSerializer(data=role_data)
            if serializer.is_valid():
                obj, created = UserAccessRole.objects.get_or_create(
                    user_access=user_access, role=serializer.validated_data['role'], defaults={
                        'assigned_at': serializer.validated_data.get('assigned_at')})
                if created:
                    created_roles.append(obj)
                else:
                    errors.append(
                        f"Role '{obj.role}' already exists for this UserAccess.")
            else:
                errors.append(serializer.errors)
        response = {'created_roles': UserAccessRoleSerializer(
            created_roles, many=True).data, 'errors': errors}
        return Response(
            response,
            status=status.HTTP_201_CREATED if created_roles else status.HTTP_400_BAD_REQUEST)

class UsersWithAccessesAndRolesByCreatorAPIView(APIView):
    """
    Returns users with accesses and roles, filtered by creator.
    - Staff: all clients
    - Client: only users they created
    - Manager: all users in their org EXCEPT clients
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.is_staff:
            print('is_staff: showing all clients')
            users = User.objects.filter(is_client=True).prefetch_related(
                'accesses__roles').order_by('id')
        elif user.is_client:
            print('is_client: showing users created by this client')
            users = User.objects.filter(created_by=user).prefetch_related(
                'accesses__roles').order_by('id')
        elif user.is_manager:
            print('is_manager: showing all users in org except clients')
            users = User.objects.filter(
                org=user.org
            ).exclude(is_client=True).exclude(id=user.id).prefetch_related(
                'accesses__roles'
            ).order_by('id')

        else:
            users = User.objects.none()

        data = []
        for u in users:
            user_data = UserSerializer(u).data
            accesses = []
            for access in u.accesses.all():
                access_data = UserAccessSerializer(access).data
                access_data["roles"] = UserAccessRoleSerializer(
                    access.roles.all(), many=True).data
                accesses.append(access_data)
            user_data["accesses"] = accesses
            data.append(user_data)
        return Response(data, status=200)

class UserAccessListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        user_id = request.query_params.get("user_id")
        project_id = request.query_params.get("project_id")
        if not user_id or not project_id:
            return Response(
                {"detail": "user_id and project_id required."}, status=400)

        qs = UserAccess.objects.filter(
            user_id=user_id, project_id=project_id, active=True)
        serializer = UserAccessSerializer(qs, many=True)
        print(serializer.data,'this is am snding')
        return Response(serializer.data, status=200)


class ProjectCategoryUserAccessAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        print("🔥 ProjectCategoryUserAccessAPIView HIT!")
        print("📋 Query params:", dict(request.query_params))

        # Collect all query params
        project_id = request.query_params.get("project_id")
        category = request.query_params.get("category_id")  # Change this to match frontend
        building_id = request.query_params.get("building_id")
        zone_id = request.query_params.get("zone_id")
        flat_id = request.query_params.get("flat_id")
        levels = [request.query_params.get(f"CategoryLevel{i}") for i in range(1, 7)]

        # --- VALIDATION ---
        errors = {}
        if not project_id:
            errors["project_id"] = "This parameter is required."
        if not category:
            errors["category_id"] = "This parameter is required."

        if errors:
            print("❌ VALIDATION ERROR:", errors)
            print("📋 QUERY PARAMS RECEIVED:", dict(request.query_params))
            return Response({
                "status": "error",
                "message": "Validation failed.",
                "errors": errors,
                "query_params": dict(request.query_params)
            }, status=400)

        print(f"🔍 Looking for project_id={project_id}, category={category}")

        # --- FILTER LOGIC ---
        # ✅ Include users with (category == requested) OR (all_cat=True) for the same project
        access_filter = Q(project_id=project_id, active=True) & (Q(category=category) | Q(all_cat=True))

        # location scopes (still honored for both sides of the OR)
        if building_id:
            access_filter &= (Q(building_id=building_id) | Q(building_id__isnull=True))
        if zone_id:
            access_filter &= (Q(zone_id=zone_id) | Q(zone_id__isnull=True))
        if flat_id:
            access_filter &= (Q(flat_id=flat_id) | Q(flat_id__isnull=True))

        # Levels only constrain specific category grants; with all_cat=True, user is included anyway by the OR
        for idx, val in enumerate(levels):
            if val:
                key = f"CategoryLevel{idx+1}"
                access_filter &= (Q(**{key: val}) | Q(**{f"{key}__isnull": True}))

        # Query and group by role
        matching_accesses = (
            UserAccess.objects
            .filter(access_filter)
            .select_related('user')
            .prefetch_related('roles')
        )

        print(f" Found {matching_accesses.count()} matching user accesses")

        role_dict = defaultdict(list)
        user_seen_by_role = defaultdict(set)

        for access in matching_accesses:
            user = access.user
            user_data = UserSerializer(user).data
            user_data["access_id"] = access.id
            user_data["project_id"] = access.project_id
            user_data["category"] = access.category
            user_data["all_cat"] = getattr(access, "all_cat", False)  # 👈 expose flag per item

            for role in access.roles.all():
                role_name = role.role.upper()
                if user.id not in user_seen_by_role[role_name]:
                    role_dict[role_name].append(user_data)
                    user_seen_by_role[role_name].add(user.id)
                    print(f" Added {user.username} to {role_name}")

        # Ensure all expected roles exist in response
        final_result = {
            "CHECKER": role_dict.get("CHECKER", []),
            "MAKER": role_dict.get("MAKER", []),
            "SUPERVISOR": role_dict.get("SUPERVISOR", [])
        }

        print(f" Final result: {final_result}")
        return Response(final_result, status=200)


class UserRoleForProjectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.query_params.get('user_id')
        project_id = request.query_params.get('project_id')

        if not user_id or not project_id:
            return Response({'detail': 'user_id and project_id are required.'}, status=400)

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User does not exist.'}, status=404)

        # Single highest-priority role (manager > client > staff > project role > None)
        role = None
        if user.is_manager:
            role = 'manager'
        elif user.is_client:
            role = 'client'
        elif user.is_staff:
            role = 'staff'
        else:
            # Check for project-specific roles (independent of category)
            user_access_qs = UserAccess.objects.filter(user=user, project_id=project_id, active=True)
            print(user_access_qs)
            access_role = (
                UserAccessRole.objects
                .filter(user_access__in=user_access_qs)
                .order_by('id')
                .first()
            )
            if access_role:
                role = access_role.role
        print({
            'user_id': user_id,
            'project_id': project_id,
            'role': role  # single role string, or null if none
        })
        return Response({
            'user_id': user_id,
            'project_id': project_id,
            'role': role  # single role string, or null if none
        })






