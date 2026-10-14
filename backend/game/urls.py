from django.urls import path

from game import views

urlpatterns = [
    path("board/", views.board, name="board"),
    path("games/", views.games, name="games"),
    path("games/<str:code>/", views.game_detail, name="game-detail"),
    path("games/<str:code>/join/", views.join, name="game-join"),
    path("games/<str:code>/me/", views.me, name="game-me"),
    path("games/<str:code>/start/", views.start, name="game-start"),
    path("games/<str:code>/players/<int:player_id>/", views.kick, name="game-kick"),
]
