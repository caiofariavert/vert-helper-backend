from rest_framework import serializers

from apps.user.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("email", "name", "password")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserViewSerializer(serializers.ModelSerializer):

    name_initials = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "name", "is_active", "name_initials", "image")

    def get_name_initials(self, obj) -> str:
        def calculate_name_initial(name: str) -> str:
            names = obj.name.split(" ")

            def get_initial(name) -> str:
                if len(name) > 0:
                    return name[0].upper()
                return ""

            if len(names) >= 2:
                return f"{get_initial(names[0])}{get_initial(names[1])}"
            elif len(names) == 1:
                return get_initial(names[0])

            return ""

        try:
            return calculate_name_initial(obj.name)
        except Exception:
            return ""
