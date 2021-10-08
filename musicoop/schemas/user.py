"""
    Módulo com o schema do usuário
"""

from musicoop.schemas.base_schema import BaseSchema

class UserSchema(BaseSchema):
    """
        Classe que contém os atributos de um Usuário
    """
    email: str
    username: str
    name : str

class CreateUserSchema(UserSchema):
    """
        Classe que contém os atributos para criar um usuário
    """
    password: str
