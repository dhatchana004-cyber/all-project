from rest_framework_simplejwt.authentication import JWTAuthentication

class JWTProxyUser:
    def __init__(self, user_id=None, username="", email="", phone_number="", has_access=False, is_client=False,
                 user_access_id=None, project_id=None, building_id=None, zone_id=None, flat_id=None, roles=None):
        self.id = user_id
        self.username = username
        self.email = email
        self.phone_number = phone_number
        self.has_access = has_access
        self.is_client = is_client
        self.user_access_id = user_access_id
        self.project_id = project_id
        self.building_id = building_id
        self.zone_id = zone_id
        self.flat_id = flat_id
        self.roles = roles or []
        self.is_authenticated = True 

class JWTRemoteAuth(JWTAuthentication):
    def get_user(self, validated_token):

        return JWTProxyUser(
            user_id=validated_token.get("user_id"),
            username=validated_token.get("username"),
            email=validated_token.get("email"),
            phone_number=validated_token.get("phone_number"),
            has_access=validated_token.get("has_access", False),
            is_client=validated_token.get("is_client", False),
            user_access_id=validated_token.get("user_access_id"),
            project_id=validated_token.get("project_id"),
            building_id=validated_token.get("building_id"),
            zone_id=validated_token.get("zone_id"),
            flat_id=validated_token.get("flat_id"),
            roles=validated_token.get("roles", []),
        )