from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import DashboardAPIView

router = DefaultRouter()
router.register(r'checklists', views.ChecklistViewSet)
router.register(r'items', views.ChecklistItemViewSet)
router.register(r'submissions', views.ChecklistItemSubmissionViewSet)
router.register(r'options', views.ChecklistItemOptionViewSet)
# router.register(r'checklist-access', views.ChecklistAccessViewSet)


urlpatterns = [

    path('dashboard-summary/', DashboardAPIView.as_view(), name='dashboard-summary'),



    #path('dashboard/',views.DashboardAPIView.as_view(), name='dashboard'),
   # path('', include(router.urls)),
    path("checklists/stagehistory/summary/", views.StageHistorySummaryAPIView.as_view()),

    path("checklists/stagehistory/crm-update/", views.StageHistoryCRMUpdateAPIView.as_view()),
    path("stage-history/",views.StageHistoryListView.as_view(), name="stage-history-list"),
    path('checklistitem/start/<int:user_id>/<int:item_id>/',
         views.StartChecklistItemAPIView.as_view()),
    path('checklistitems/inprogress/<int:user_id>/',
         views.ChecklistItemInProgressByUserView.as_view()),
    path('checklistitems/completed/<int:user_id>/',
         views.ChecklistItemCompletedByUserView.as_view()),
    path('checklistitems/by-category-status/<int:cat_or_subcat_id>/',
         views.ChecklistItemByCategoryStatusView.as_view()),
    path(
        'accessible-checklists/',
        views.AccessibleChecklistsAPIView.as_view(),
        name='accessible-checklists'),
    # path('accessible-checklists-In-progress/', views.AccessibleChecklistsInProgressAPIView.as_view(), name='accessible-checklists-in-progress'),
    # path('my-inprogress-checklistitem-submissions/',
    #      views.MyInProgressChecklistItemSubmissions.as_view()),
    path("flat-report/<int:flat_id>/", views.FlatReportAPIView.as_view(), name="flat-report"),
    path(
        "accessible-checklists-unreviewed/",
        views.AccessibleChecklistsWithPendingCheckerSubmissionsAPIView.as_view(),
        name="accessible-checklists-unreviewed"),
    path("create-checklistitemsubmissions-assign/",
         views.CreateSubmissionsForChecklistItemsAPIView.as_view(),
         name="bulk-create-checklistitemsubmissions"),
    path("patch-checklistitemsubmission/",
         views.PatchChecklistItemSubmissionAPIView.as_view(),
         name="patch-checklistitemsubmission"),
    path("my-hierarchical-verifications/",
         views.MyHierarchicalVerificationsAPIView.as_view(),
         name="my-hierarchical-verifications"),
    path(
        "bulk-verify-submissions/",
        views.BulkVerifyChecklistItemSubmissionsAPIView.as_view(),
        name="bulk-verify-submissions"),

    path("verify-checklist-item-submission/",
         views.VerifyChecklistItemSubmissionAPIView.as_view(),
         name="verify-checklist-item-submission"),
         
    path('checker-verified-inspector-pending/',
         views.VerifiedByCheckerPendingInspectorAPIView.as_view()),
    # added now
    path('my-submissions/', views.MyChecklistItemSubmissions.as_view()),
    # path('pending-checker/', views.PendingVerificationsForCheckerAPIView.as_view()),
    path(
        'pending-supervisor/',
        views.PendingVerificationsForSupervisorAPIView.as_view()),
    # path('<int:checklist_id>/patch-roles/', views.PatchChecklistRolesJsonAPIView.as_view(), name='patch-checklist-roles'),



    # for daaaashboard
    path(
        'checklist-analytics/',
        views.ChecklistRoleAnalyticsAPIView.as_view(),
        name='checklist-analytics'),

    # for all
    path('checklist-items/<int:checklist_id>/',
         views.ChecklistItemsByChecklistAPIView.as_view(),
         name='checklist-items-by-checklist'),
    path(
        'checklists/filter/',
        views.ChecklistByCreatorAndProjectAPIView.as_view(),
        name='checklist-filter'),

    # for intializer
    path(
        'start-checklist/<int:checklist_id>/',
        views.IntializeChechklistView.as_view(),
        name='start-checklist'),

    path(
        'Chechker-New-checklist/',
        views.CheckerInprogressAccessibleChecklists.as_view(),
        name='CHecker-View-checklist'),

    # supervisor
    path(
        'Decsion-makeing-forSuer-Inspector/',
        views.VerifyChecklistItemForCheckerNSupervisorAPIView.as_view(),
        name='Decision_api'),


    path(
        'pending-for-maker/',
        views.PendingForMakerItemsAPIView.as_view(),
        name='pending-for-maker-items'),
    path(
        'mark-as-done-maker/',
        views.MAker_DOne_view.as_view(),
        name="MArker_save"),
# main
    path(
        'Transafer-Rule-getchchklist/',
        views.RoleBasedChecklistTRANSFERRULEAPIView.as_view(),
        name="MArker_save"),

    path(
        'Supervisor-Pending-work/',
        views.PendingForSupervisorItemsAPIView.as_view(),
        name="pending-supervsiorr-view"),

    path('create/unit-chechklist/',
         views.CreateChecklistforUnit.as_view(),
         name='create-checklist-for-unit'),

        path('user-generated-checklists/', views.UserGeneratedChecklist.as_view(), name='user-generated-checklist'),
]
