# -*- coding: utf-8 -*-

from datetime import datetime

from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import render

from espnff import League

from rest_framework import authentication, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from threading import Lock, Thread

#############################
#
# General Utils
#
#############################
mutex = Lock()

def getCurrentYear():
  now = datetime.now()

  if (now.month < 8):
    return now.year - 1

  return now.year

def toDict(obj):
  return obj.__dict__

#############################
#
# ESPN FF API Utils
#
#############################

def createLeagueObject(leagueId, year=getCurrentYear()):
  return League(leagueId, year)

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

def serializeMatchup(matchup):
  matchup.home_team = serializeBasicTeam(matchup.home_team)
  matchup.away_team = serializeBasicTeam(matchup.away_team)
  return toDict(matchup)

def serializeRankings(rankings):
  return map(lambda pair: { 'score': float(pair[0]), 'team': serializeBasicTeam(pair[1]) }, rankings)

def serializeTeam(team):
  team.schedule = list(map(lambda t: serializeBasicTeam(t), team.schedule))
  return toDict(team)

def threadedBuildHistoryFromMatchups(league, teamHistory, teamId):
  for week in list(range(1, 18)):
    try:
      scoreboard = league.scoreboard(week=week)
    except:
      break
    else:
      matchup = None
      opponentOwner = None
      opponentId = None
      opponentSide = None
      side = None
      for m in scoreboard:
        if (m.home_team.team_id == int(teamId)):
          matchup = m
          side = 'home'
          opponentOwner = m.away_team.owner
          opponentId = str(m.away_team.team_id)
          opponentSide = 'away'
        elif (m.away_team.team_id == int(teamId)):
          matchup = m
          side = 'away'
          opponentOwner = m.home_team.owner
          opponentId = str(m.home_team.team_id)
          opponentSide = 'home'

      if (matchup and matchup.data['winner'] != 'undecided'):
        mutex.acquire()
        try:
          if (not opponentId in teamHistory['matchupHistory']):
            teamHistory['matchupHistory'][opponentId] = {
              'margin': 0,
              'marginOfDefeat': 0,
              'marginOfVictory': 0,
              'opponentName': opponentOwner,
              'losses': 0,
              'ties': 0,
              'wins': 0
            }

          if (matchup.data['winner'] == side):
            teamHistory['wins'] += 1
            teamHistory['margin'] += abs(m.home_score - m.away_score)
            teamHistory['marginOfVictory'] += abs(m.home_score - m.away_score)
            teamHistory['matchupHistory'][opponentId]['wins'] += 1
            teamHistory['matchupHistory'][opponentId]['margin'] += abs(m.home_score - m.away_score)
            teamHistory['matchupHistory'][opponentId]['marginOfVictory'] += abs(m.home_score - m.away_score)
          elif (matchup.data['winner'] == opponentSide):
            teamHistory['losses'] += 1
            teamHistory['margin'] += (-1 * abs(m.home_score - m.away_score))
            teamHistory['marginOfDefeat'] += (-1 * abs(m.home_score - m.away_score))
            teamHistory['matchupHistory'][opponentId]['losses'] += 1
            teamHistory['matchupHistory'][opponentId]['margin'] += (-1 * abs(m.home_score - m.away_score))
            teamHistory['matchupHistory'][opponentId]['marginOfDefeat'] += (-1 * abs(m.home_score - m.away_score))
          else:
            teamHistory['ties'] += 1
            teamHistory['matchupHistory'][opponentId]['ties'] += 1
        finally:
          mutex.release()

#############################
#
# Views
#
#############################

@api_view(['GET'])
def getTeams(request, leagueId, year=getCurrentYear()):
  league = createLeagueObject(leagueId, year)
  teams = list(map(lambda team: serializeTeam(team), league.teams))
  response = { 'teams': teams }
  return Response(response)

@api_view(['GET'])
def getTeam(request, leagueId, teamId, year=getCurrentYear()):
  league = createLeagueObject(leagueId, year)
  team = None
  for t in league.teams:
    if t.team_id == int(teamId):
      team = t

  if not team:
    raise Http404('Team does not exist')

  return Response(serializeTeam(team))

@api_view(['GET'])
def getPowerRankings(request, leagueId, year=getCurrentYear()):
  league = createLeagueObject(leagueId, year)
  week = league.teams[0].wins + league.teams[0].losses
  rankings = league.power_rankings(week=week)
  return Response({ 'rankings': serializeRankings(rankings), 'week': week })

@api_view(['GET'])
def getScoreboard(request, leagueId, year=getCurrentYear()):
  league = createLeagueObject(leagueId, year)
  scoreboard = map(lambda matchup: serializeMatchup(matchup), league.scoreboard())
  return Response({ 'scoreboard': scoreboard })

@api_view(['GET'])
def getTeamHistory(request, leagueId, teamId):
  error = None
  teamHistory = {
    'margin': 0,
    'marginOfDefeat': 0,
    'marginOfVictory': 0,
    'losses': 0,
    'ties': 0,
    'wins': 0,
    'matchupHistory': {}
  }
  year = getCurrentYear()

  listOfThreads = []

  while (not error):
    try:
      league = createLeagueObject(leagueId, year)
    except:
      error = True
    else:
      if (int(leagueId) == 336358 and year == 2010):
        error = True
        continue;
      team = None
      for t in league.teams:
        if t.team_id == int(teamId):
          team = t

      if (team):
        t = Thread(target = threadedBuildHistoryFromMatchups, args=(league, teamHistory, teamId))
        t.start()
        listOfThreads.append(t)

      year -= 1

  for thread in listOfThreads:
    thread.join()

  games = teamHistory['wins'] + teamHistory['losses'] + teamHistory['ties']
  teamHistory['margin'] = round(teamHistory['margin'] / games, 2)
  teamHistory['marginOfDefeat'] = round(teamHistory['marginOfDefeat'] / teamHistory['losses'], 2)
  teamHistory['marginOfVictory'] = round(teamHistory['marginOfVictory'] / teamHistory['wins'], 2)

  for matchup in teamHistory['matchupHistory']:
    matchup = teamHistory['matchupHistory'][matchup]
    games = matchup['wins'] + matchup['losses'] + matchup['ties']
    matchup['margin'] = round(matchup['margin'] / games, 2)
    matchup['marginOfDefeat'] = round(matchup['marginOfDefeat'] / matchup['losses'], 2)
    matchup['marginOfVictory'] = round(matchup['marginOfVictory'] / matchup['wins'], 2)

  return Response(teamHistory)

