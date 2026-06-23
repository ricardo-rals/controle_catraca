from rest_framework.exceptions import AuthenticationFailed

class AuthService:
    @staticmethod
    def validate_user_for_token(user):
        """
        Regras de negócio isoladas para validação do usuário
        antes da emissão do token JWT.
        """
        if not user.is_active:
            raise AuthenticationFailed('Usuário inativo. Acesso negado.', code='user_inactive')
        
        return True
