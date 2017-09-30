from django.conf.urls import url

from . import views

urlpatterns = [
  url(r'^(?P<leagueId>[0-9]+)/(?P<year>[0-9]+)/teams/$', views.getTeams),
  url(r'^(?P<leagueId>[0-9]+)/(?P<year>[0-9]+)/teams/(?P<teamId>[0-9]+)/$', views.getTeam),
  url(r'^(?P<leagueId>[0-9]+)/(?P<year>[0-9]+)/power-rankings/$', views.getPowerRankings),
  url(r'^(?P<leagueId>[0-9]+)/(?P<year>[0-9]+)/scoreboard/$', views.getScoreboard),
]