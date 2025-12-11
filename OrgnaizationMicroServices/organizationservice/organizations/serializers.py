from rest_framework import serializers
from .models import Organization, Company, Entity

class EntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Entity
        fields = '__all__'

class CompanySerializer(serializers.ModelSerializer):
    entities = EntitySerializer(many=True, read_only=True)
    class Meta:
        model = Company
        fields = '__all__'


class OrganizationSerializer(serializers.ModelSerializer):
    companies = CompanySerializer(many=True, read_only=True)
    class Meta:
        model = Organization
        fields = '__all__'
