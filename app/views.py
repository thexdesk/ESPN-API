# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import render

from espnff import League

import json

from rest_framework import authentication, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

def createLeagueObject(leagueId, year):
  return League(leagueId, year)

def toDict(obj):
  return obj.__dict__

def serializeBasicTeam(team):
  if not team:
    return {}

  return {
    'team_id': team.team_id,
    'team_name': team.team_name,
    'wins': int(team.wins),
    'losses': int(team.losses),
    'owner': team.owner
  }

def serializeTeam(team):
  team.schedule = list(map(lambda t: serializeBasicTeam(t), team.schedule))
  return toDict(team)

def serializeMatchup(matchup):
  matchup.home_team = serializeBasicTeam(matchup.home_team)
  matchup.away_team = serializeBasicTeam(matchup.away_team)
  return toDict(matchup)

def serializeRankings(rankings):
  return map(lambda pair: { 'score': float(pair[0]), 'team': serializeBasicTeam(pair[1]) }, rankings)

@api_view(['GET'])
def getTeams(request, leagueId, year):
  league = createLeagueObject(leagueId, year)
  teams = list(map(lambda team: serializeTeam(team), league.teams))
  response = { 'teams': teams }
  return Response(response)

@api_view(['GET'])
def getTeam(request, leagueId, year, teamId):
  league = createLeagueObject(leagueId, year)
  team = None
  for t in league.teams:
    if t.team_id == int(teamId):
      team = t

  if not team:
    raise Http404('Team does not exist')

  return Response(serializeTeam(team))

@api_view(['GET'])
def getPowerRankings(request, leagueId, year):
  league = createLeagueObject(leagueId, year)
  week = league.teams[0].wins + league.teams[0].losses
  rankings = league.power_rankings(week=week)
  return Response({ 'rankings': serializeRankings(rankings), 'week': week })

@api_view(['GET'])
def getScoreboard(request, leagueId, year):
  league = createLeagueObject(leagueId, year)
  scoreboard = map(lambda matchup: serializeMatchup(matchup), league.scoreboard())
  return Response({ 'scoreboard': scoreboard })
