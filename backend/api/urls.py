from django.urls import path

from api.views.health import HealthView
from api.views.messages import ThreadMessagesView
from api.views.threads import ThreadsView
from api.views.users import UsersView

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("users", UsersView.as_view(), name="users"),
    path("threads", ThreadsView.as_view(), name="threads"),
    path(
        "threads/<str:thread_id>/messages",
        ThreadMessagesView.as_view(),
        name="thread-messages",
    ),
]
