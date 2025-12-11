from rest_framework.routers import DefaultRouter
from .views import UserViewSet, UserAccessViewSet, UserAccessRoleViewSet,UserAccessFullCreateView,UserAccessRoleDeleteView,UserAccessListByUserView,UserAccessListAPIView,ProjectCategoryUserAccessAPIView,UsersWithAccessesAndRolesByCreatorAPIView,UserDashboardAPIView,ClientUserListAPIView,UserRoleForProjectAPIView,PasswordResetRequestView,PasswordResetConfirmView
from .views import UserAccessFullPatchView
from django.urls import path
from .views import *

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'accesses', UserAccessViewSet)
router.register(r'roles', UserAccessRoleViewSet)

urlpatterns = [


   


   # path("attendance/", StaffAttendanceListCreateView.as_view(), name="attendance-list-create"),
   # path("attendance/<int:pk>/", StaffAttendanceDetailView.as_view(), name="attendance-detail"),
    path("attendance/", StaffAttendanceListCreateView.as_view(), name="attendance-list-create"),
    path('staffs/', StaffListCreateView.as_view(), name='staff-list-create'),
    path('staffs/<int:pk>/', StaffDetailView.as_view(), name='staff-detail'),
    path('user/<int:user_id>/role/<int:role_id>/delete/', UserAccessRoleDeleteView.as_view(), name='useraccessrole-delete'),
    path("users/access-full-patch/<int:user_id>/", UserAccessFullPatchView.as_view(), name="user-access-full-patch"),
    path('user/<int:user_id>/accesses/', UserAccessListByUserView.as_view(), name='useraccess-list-by-user'),
    path('user-access-role/',UserAccessFullCreateView.as_view(),name='User_name_role'),
    path('user-access/', UserAccessListAPIView.as_view(), name='user-access-list'),
    path("project-category-user-access/", ProjectCategoryUserAccessAPIView.as_view()),
    path("users-by-creator/", UsersWithAccessesAndRolesByCreatorAPIView.as_view(), name="users-by-creator"),
    path('user-dashboard/', UserDashboardAPIView.as_view(), name='user-dashboard'),
    path('clients/', ClientUserListAPIView.as_view(), name='client-user-list'),
    path('user-role-for-project/', UserRoleForProjectAPIView.as_view(), name='user-role-for-project'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),


]


urlpatterns += router.urls

