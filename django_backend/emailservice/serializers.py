from rest_framework import serializers


class AdminEmailSerializer(serializers.Serializer):
    to_email = serializers.EmailField()
    data = serializers.DictField(child=serializers.CharField(), required=False)
    locale = serializers.CharField(default='en')
    from_email = serializers.EmailField(required=False)
    reply_to = serializers.EmailField(required=False)
    use_ssl = serializers.BooleanField(default=False)


class AdminOTPSerializer(AdminEmailSerializer):
    otp = serializers.CharField(required=True)
