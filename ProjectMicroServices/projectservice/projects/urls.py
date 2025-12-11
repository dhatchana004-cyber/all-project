from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    ProjectViewSet, PurposeViewSet, PhaseViewSet, StageViewSet,
    BuildingViewSet, LevelViewSet, ZoneViewSet,
    FlattypeViewSet, FlatViewSet,PhaseListByProject,PurposeListByProject,StageListByProject,PhaseCreateView,
      PurposeListByProject, PhaseListByProject, StageListByPhase,
    BuildingListByProject, LevelListByBuilding,
    ZoneListByBuilding, ZoneListByLevel,
    FlattypeListByProject,
    FlatListByBuilding, FlatListByLevel, FlatListByFlattype,GetProjectsByUser,BuildingWithLevelsByProject    ,BuildingsWithLevelsAndZonesByProject,SubzoneViewSet,BulkLevelZonesSubzonesCreateAPIView,RoomViewSet,
    CategoryViewSet, CategoryLevel1ViewSet, CategoryLevel2ViewSet, CategoryLevel3ViewSet,
    CategoryLevel4ViewSet, CategoryLevel5ViewSet, CategoryLevel6ViewSet,
    CategoriesByProjectView,FLatssbyProjectId,BuildingToFlatsByProject,TransferRuleViewSet,
    LevelsWithFlatsByBuilding,ProjectsByOrganizationView,CategorySimpleViewSet,ProjectsByIdsAPIView,ProjectsByOwnershipParamView,
    OrgProjectUserSummaryAPIView,UnitListAPIView,
AllPurposeListCreateAPIView,StageInfoAPIView,
    ClientPurposeCreateAPIView,
    ClientPurposeListAPIView,
    ClientPurposeSoftDeleteAPIView,
        CategoryLevel1SimpleViewSet,
    CategoryLevel2SimpleViewSet,
    CategoryLevel3SimpleViewSet,
    CategoryLevel4SimpleViewSet,
    CategoryLevel5SimpleViewSet,
    CategoryLevel6SimpleViewSet,
ActivateProjectPurposeView,NextStageAPIView,
    CategoryTreeByProjectAPIView,ProjectNestedAPIView
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet)                     # No basename needed (has queryset)
router.register(r'purposes', PurposeViewSet)                     # No basename needed
router.register(r'phases', PhaseViewSet)                         # No basename needed
router.register(r'stages', StageViewSet)                         # No basename needed
router.register(r'buildings', BuildingViewSet)                   # No basename needed
router.register(r'levels', LevelViewSet)                         # No basename needed
router.register(r'zones', ZoneViewSet)                           # No basename needed
router.register(r'flattypes', FlattypeViewSet)                   # No basename needed
router.register(r'flats', FlatViewSet)                           # No basename needed

router.register(r'transfer-rules', TransferRuleViewSet, basename='transfer-rule') # <--- NEEDS BASENAME (custom/non-model view)

router.register(r'subzones', SubzoneViewSet)                     # No basename needed
router.register(r'rooms', RoomViewSet, basename='rooms')         # <--- NEEDS BASENAME if no queryset

router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'category-level1', CategoryLevel1ViewSet, basename='category-level1')
router.register(r'category-level2', CategoryLevel2ViewSet, basename='category-level2')
router.register(r'category-level3', CategoryLevel3ViewSet, basename='category-level3')
router.register(r'category-level4', CategoryLevel4ViewSet, basename='category-level4')
router.register(r'category-level5', CategoryLevel5ViewSet, basename='category-level5')
router.register(r'category-level6', CategoryLevel6ViewSet, basename='category-level6')
router.register(r'category-level1-simple', CategoryLevel1SimpleViewSet)
router.register(r'category-level2-simple', CategoryLevel2SimpleViewSet)
router.register(r'category-level3-simple', CategoryLevel3SimpleViewSet)
router.register(r'category-level4-simple', CategoryLevel4SimpleViewSet)
router.register(r'category-level5-simple', CategoryLevel5SimpleViewSet)
router.register(r'category-level6-simple', CategoryLevel6SimpleViewSet)
router.register(r'categories-simple', CategorySimpleViewSet, basename='categories-simple'),


urlpatterns = [

    



    path('by-ids/', ProjectsByIdsAPIView.as_view(), name='projects-by-ids'),
    path('stages/<int:stage_id>/next/', NextStageAPIView.as_view(), name='next-stage'),
    path('category-tree-by-project/', CategoryTreeByProjectAPIView.as_view()),
    path('phases/by-project/<int:project_id>/', PhaseListByProject.as_view(), name='phases-by-project'),
    path('purpose/get-purpose-details-by-project-id/<int:project_id>/', PurposeListByProject.as_view(), name='purpose-by-project'),
    path('get-stage-details-by-project-id/<int:project_id>/', StageListByProject.as_view(),name='stage_list_project'),
    path('phase/create-phases/', PhaseCreateView.as_view(), name='create-phase'),
    path('purposes/by_project/<int:project_id>/', PurposeListByProject.as_view(), name='purpose-list-by-project'),
    path('phases/by_project/<int:project_id>/', PhaseListByProject.as_view(), name='phase-list-by-project'),
    path('stages/by_phase/<int:phase_id>/', StageListByPhase.as_view(), name='stage-list-by-phase'),
    path('buildings/by_project/<int:project_id>/', BuildingListByProject.as_view(), name='building-list-by-project'),
    path('stages/<int:stage_id>/info/', StageInfoAPIView.as_view()),
    path('levels/by_building/<int:building_id>/', LevelListByBuilding.as_view(), name='level-list-by-building'),
    path('zones/by_building/<int:building_id>/', ZoneListByBuilding.as_view(), name='zone-list-by-building'),
    path('zones/by_level/<int:level_id>/', ZoneListByLevel.as_view(), name='zone-list-by-level'),
    path('flattypes/by_project/<int:project_id>/', FlattypeListByProject.as_view(), name='flattype-list-by-project'),
    path('flats/by_building/<int:building_id>/', FlatListByBuilding.as_view(), name='flat-list-by-building'),
    path('flats/by_level/<int:level_id>/', FlatListByLevel.as_view(), name='flat-list-by-level'),
    path('flats/by_flattype/<int:flattype_id>/', FlatListByFlattype.as_view(), name='flat-list-by-flattype'),
    path('user-stage-role/get-projects-by-user/', GetProjectsByUser.as_view(), name='get-projects-by-user'),
    path('buildings/with-levels/by_project/<int:project_id>/', BuildingWithLevelsByProject.as_view(), name='buildings-with-levels-by-project'),
    path('buildings/with-levels-and-zones/by_project/<int:project_id>/', BuildingsWithLevelsAndZonesByProject.as_view(), name='buildings-with-levels-zones'),
    path('buildings/with-levels-zones/bulk-create/', BulkLevelZonesSubzonesCreateAPIView.as_view(), name='buildings-levels-zones-bulk-create'),
    # path('categories/project/<int:project_id>/', CategoriesByProjectView.as_view(), name='categories-by-project'),  
    path('flats/by_project/<int:project_id>/', FLatssbyProjectId.as_view(), name='flattype-list-by-project'),
    path('projects/<int:project_id>/buildings-details/', BuildingToFlatsByProject.as_view(), name='buildings-details-by-project'),
    path('levels-with-flats/<int:building_id>/', LevelsWithFlatsByBuilding.as_view(), name='levels-with-flats'),
    path('projects/by_organization/<int:organization_id>/', ProjectsByOrganizationView.as_view(), name='projects-by-organization'),
    path('projects/by_ownership/', ProjectsByOwnershipParamView.as_view(), name='projects-by-user-ownership'),
    path('org-project-user-summary/', OrgProjectUserSummaryAPIView.as_view(), name='org-project-user-summary'),
    path('units-by-id/', UnitListAPIView.as_view(), name='unit-list-api'),

    path('all-purposes/', AllPurposeListCreateAPIView.as_view(), name='all-purpose-list-create'),
    path("projects/<int:project_id>/activate-purpose/", ActivateProjectPurposeView.as_view(), name="activate-project-purpose"),
    # Assign a purpose to a client (POST)
    path('client-purpose/', ClientPurposeCreateAPIView.as_view(), name='client-purpose-create'),

    # Get all purposes for a client (GET)
    path('client-purpose/<int:client_id>/', ClientPurposeListAPIView.as_view(), name='client-purpose-list'),

    # Soft delete a client-purpose mapping (PATCH recommended)
    path('client-purpose/<int:pk>/soft-delete/', ClientPurposeSoftDeleteAPIView.as_view(), name='client-purpose-soft-delete'),

    path('projects/<int:project_id>/nested/', ProjectNestedAPIView.as_view(), name='project-nested-detail'),

]
urlpatterns += router.urls


# GET /category-level1/?category=5
