from rest_framework import routers
# from .views import OrganizationViewSet, CompanyViewSet, EntityViewSet,UserAlloriginazitionINfo,CompanyInfoWithEntities,EntityInfoWithParents,OrganizationByUserView,CompanyDetailsByOrganizationId
from .views import *
from django.urls import path

router = routers.DefaultRouter()
router.register(r'organizations', OrganizationViewSet)
router.register(r'companies', CompanyViewSet)
router.register(r'entities', EntityViewSet)


urlpatterns = [

   


    path('user-orgnizationn-info/<int:user_id>/', UserAlloriginazitionINfo.as_view(), name='user-summary'),
    path('All-Info-Through-company-info/<int:company_id>/', CompanyInfoWithEntities.as_view()),
    path('entity-info/<int:user_id>/<int:entity_id>/', EntityInfoWithParents.as_view()),
    path('organizations/by-user/<int:user_id>/', OrganizationByUserView.as_view(), name='organizations-by-user'),
    path('company/get-company-details-by-organization-id/',CompanyDetailsByOrganizationId.as_view(),name='get-company-details-by-organization-id'),
]

urlpatterns += router.urls