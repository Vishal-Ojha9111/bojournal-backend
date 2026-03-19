"""
Custom permission classes for object-level permissions.
"""
from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to access it.
    Assumes the object has a `user` attribute.
    """
    message = "You must be the owner of this object to perform this action."
    
    def has_object_permission(self, request, view, obj):
        # Check if object has user attribute and matches request user
        return hasattr(obj, 'user') and obj.user == request.user
