from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .services import AuthService


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        AuthService.validate_user_for_token(self.user)

        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token["username"] = user.username
        token["email"] = user.email
        token["is_staff"] = user.is_staff

        return token
