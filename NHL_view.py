from tkinter import *
master = Tk()
master.title('NHL View')

import datetime

#Only seems to work before importing datetime from datetime???
local = str(datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo)

from dateutil import tz
from datetime import datetime, timedelta
import time
import json
import requests
import pandas as pd

#default values before config file is read
refresh = 3
games_height = 14
win_percentage_as_default = True
live_games_only = False
no_spoilers_only = False

#API Links
main_url = 'https://statsapi.web.nhl.com/api/v1'
score_url = 'http://live.nhle.com/GameData/RegularSeasonScoreboardv3.jsonp?'


def readsettings():
	#Read config file
	global refresh, games_height, win_percentage_as_default, live_games_only, no_spoilers_only
	with open('settings.txt') as json_file:  
		data = json.load(json_file)[0]
		refresh = data['refresh']
		games_height = data['games_height']
		live_games_only = data['live_games_only']
		no_spoilers_only = data['no_spoilers_only']

def writesettings():
	#write config file
	data = []
	data.append({
		'refresh' : refresh,
		'games_height' : games_height,
		'live_games_only' : live_games_only,
		'no_spoilers_only' : no_spoilers_only,
		})
	with open('settings.txt', 'w') as outfile:  
		json.dump(data, outfile)

#Read or write config file if not read
try:
	readsettings()
except:
	writesettings()


def get_game_id(sched, name):
	#Game ID into list
	game_info = []
	for games in sched:
		game_info.append(games[name])
	return game_info

def get_live(sched):
	#Live or final (finished) status into list
	game_info = []
	for games in sched:
		if games['status']['abstractGameState'] == 'Live':
			game_info.append('Live')
		elif games['status']['abstractGameState'] == 'Final':
			game_info.append('Final')
		else:
			game_info.append(None)
	return game_info

def get_live_time(ident, local, score):
	#compare games IDs and check if today and live and return scoreboard clock or game start time
	game_info = [None for blank in range(len(ident))]
	for games in range(len(ident)):
		for status in score:
			if ident[games] == status['id']:
				game_info[games] = local[games]
				if status['ts'] != 'TODAY':
					game_info[games] = status['ts']
				if status['bs'] == 'FINAL' or status['bs'] == 'FINAL OT' or status['bs'] == 'FINAL SO':
					game_info[games] = status['bs']
	return game_info

def get_live_time_no_spoil(ident, local, score):
	#Compare games IDs and check if today and return active status or game start time
	game_info = [None for blank in range(len(ident))]
	for games in range(len(ident)):
		for status in score:
			if ident[games] == status['id']:
				game_info[games] = local[games]
				if status['ts'] != 'TODAY':
					game_info[games] = 'LIVE'
				#Extra important for spoilers if it went into extra time or not
				if status['bs'] == 'FINAL' or status['bs'] == 'FINAL OT' or status['bs'] == 'FINAL SO':
					game_info[games] = 'FINAL'
	return game_info

def get_no_live_time(sched, local):
	#Games not live and check if Final (finished) or yet to be played to display local start time
	game_info = []
	for games in range(len(sched)):
		if sched[games]['status']['abstractGameState'] == 'Final':
			game_info.append('Final')
		else:
			game_info.append(local[games])
	return game_info

def get_team_id(sched, home_or_away):
	#Team IDs into list for logo display
	game_info = []
	for games in sched:
		game_info.append(games['teams'][home_or_away]['team']['id'])
	return game_info

def get_team_name(sched, home_or_away):
	#Team names into list
	game_info = []
	for games in sched:
		game_info.append(games['teams'][home_or_away]['team']['name'])
	return game_info

def get_team_score(sched, home_or_away):
	#Team scores into list
	game_info = []
	for games in sched:
		game_info.append(games['teams'][home_or_away]['score'])
	return game_info

def get_team_combined_record(sched):
	#Combined records into list
	game_info = []
	for games in sched:
		home_record = ((games['teams']['home']['leagueRecord']['wins']*2)+games['teams']['home']['leagueRecord']['ot'])
		home_total = ((games['teams']['home']['leagueRecord']['wins']+games['teams']['home']['leagueRecord']['losses']+games['teams']['home']['leagueRecord']['ot'])*2)
		away_record = ((games['teams']['away']['leagueRecord']['wins']*2)+games['teams']['away']['leagueRecord']['ot'])
		away_total = ((games['teams']['away']['leagueRecord']['wins']+games['teams']['away']['leagueRecord']['losses']+games['teams']['away']['leagueRecord']['ot'])*2)
		game_info.append((home_record+away_record)/(home_total+away_total))
	return game_info

def get_team_record(sched, home_or_away):
	#Team records into list
	game_info = []
	for games in sched:
		team_record = ((games['teams'][home_or_away]['leagueRecord']['wins']*2)+games['teams'][home_or_away]['leagueRecord']['ot'])
		team_total = ((games['teams'][home_or_away]['leagueRecord']['wins']+games['teams'][home_or_away]['leagueRecord']['losses']+games['teams'][home_or_away]['leagueRecord']['ot'])*2)
		game_info.append(team_record/team_total)
	return game_info

def get_team_difference_record(sched):
	#Combined records into list
	game_info = []
	for games in sched:
		home_record = ((games['teams']['home']['leagueRecord']['wins']*2)+games['teams']['home']['leagueRecord']['ot'])
		home_total = ((games['teams']['home']['leagueRecord']['wins']+games['teams']['home']['leagueRecord']['losses']+games['teams']['home']['leagueRecord']['ot'])*2)
		away_record = ((games['teams']['away']['leagueRecord']['wins']*2)+games['teams']['away']['leagueRecord']['ot'])
		away_total = ((games['teams']['away']['leagueRecord']['wins']+games['teams']['away']['leagueRecord']['losses']+games['teams']['away']['leagueRecord']['ot'])*2)
		record = (home_record/home_total)-(away_record/away_total)
		if record < 0:
			record = record * -1
		record = 1 - record
		game_info.append(record)
	return game_info

def get_local_time(foreign_date):
	#Convert game start times (in Zulu) time to local time
	game_info = []
	for date in foreign_date:
		local_time = datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=tz.gettz('UTC')).astimezone(tz.gettz(local))
		game_info.append(local_time.strftime('%H:%M'))
	return game_info

def change_option_menu(*args):
	#When dropdown menu is selected to change variable
	global main_option, main_option_select
	main_option_select = main_option.get()

def refresh_logos():
	#Change logos to match rest of columns
	global logo_labels, logo_list, Data_Frame
	for games in range(size):
		logo_labels[games] = Label(master, image=logo_list[0]).grid(row=games)
	for games in range(len(Data_Frame['Away Team ID'])):
		logo_labels[games] = Label(master, image=logo_list[Data_Frame['Away Team ID'][games]]).grid(row=games*3)
		logo_labels[games] = Label(master, image=logo_list[Data_Frame['Home Team ID'][games]]).grid(row=(games*3)+1)

def add_day():
	#Button press to go back a date to change link in API
	global set_date
	set_date = set_date + timedelta(days=1)
	game_date.set(set_date.strftime('%d-%m-%Y'))
	refresh = 0

def minus_day():
	#Button press to go forward a date to change link in API
	global set_date
	set_date = set_date - timedelta(days=1)
	game_date.set(set_date.strftime('%d-%m-%Y'))
	refresh = 0

#Open team logo files and convert them into a list for Label reference
file_list = []
for i in range(55): #54 being highest number in team IDs
	file_list.append("logos/%s.gif" % i)
logo_list = []
for i in range(len(file_list)):
	try:
		logo_list.append(PhotoImage(file=file_list[i]))
	except:
		logo_list.append(PhotoImage(file=file_list[0]))

#Number of rows to display
size = games_height * 3

#Create logo labels
logo_labels = []
for i in range(size):
	logo_labels.append(Label(master, image=logo_list[0]).grid(row=i))

#To help with refreshing images, uses as comparison of data change and if images need changing or not
logo_holder = None
logo_holder2 = 0
logo_holder3 = None

#Create lists to append to as Label string variables will be used for text
column_1 = []
column_2 = []
column_3 = []
column_4 = []

for games in range(size):
	column_1.append((StringVar()))
	column_2.append((StringVar()))
	column_3.append((StringVar()))
	column_4.append((StringVar()))
	Label(master, textvariable=column_1[games]).grid(row=(games), column=1, sticky=W)
	Label(master, textvariable=column_2[games]).grid(row=(games), column=2)
	Label(master, textvariable=column_3[games]).grid(row=(games), column=3)
	Label(master, textvariable=column_4[games]).grid(row=(games), column=4)

#Using for testing to see if labels are changing on every cycle
test_count = IntVar()
test_count_set = 1
Label(master, textvariable=test_count).grid(row=size+1, column=(1))

#Set variables based on config file and checkbuttons for live games only
if live_games_only == True:
	live_games = IntVar(value=1)
else:
	live_games = IntVar()
Checkbutton(master, text="Live games only", variable=live_games).grid(row=size+1, column=3)

#Set variables based on config file and checkbuttons for spoilers
if no_spoilers_only == True:
	no_spoilers = IntVar(value=1)
else:
	no_spoilers = IntVar()
Checkbutton(master, text="No Spoilers", variable=no_spoilers).grid(row=size+1, column=4)

#Dropdown menu for stats column and sorting
main_option_select = None
main_option = StringVar()
main_option.set("Choose from stats")
OptionMenu(master, main_option, "Combined Win Percentage", "Home Win Percentage", "Away Win Percentage", "Win Percentage Difference").grid(row=1, column=6)

#Initial Date and convert from Zulu to EST for initial API link
schedule = requests.get(main_url + '/schedule').json()['dates'][0]['games']
set_date = datetime.strptime(schedule[0]['gameDate'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=tz.gettz('UTC')).astimezone(tz.gettz('EST'))

#Date Label and string variable
game_date = StringVar()
Label(master, textvariable=game_date).grid(row=0, column=6)
game_date.set(set_date.strftime('%d-%m-%Y'))

#Buttons to change date
Button(master, text='<', command=minus_day).grid(row=0, column=5, pady=4)
Button(master, text='>', command=add_day).grid(row=0, column=7, pady=4)

#Checks dropdown menu
main_option.trace('w', change_option_menu)

#refreshed data in loop
def continual_loop():
	#Globals to bring in outside variables into function
	global main_url, score_url, test_count_set, set_date, refresh, logo_holder, logo_holder2, logo_holder3, live_games_only, main_option, Data_Frame

	#Date format used in API link
	request_date = set_date.strftime('%Y-%m-%d')

	#Counting up after every complete loop
	test_count_set +=1
	test_count.set(test_count_set)

	#Lame attempt to prevent crashing from dropouts
	for attempts in range(5):
		try:
			schedule = requests.get(main_url + '/schedule/?expand=schedule.teams,schedule.linescore,schedule.scoringplays,schedule.game.content.media.epg&date='+request_date).json()['dates'][0]['games']
			break
		except:
			print ('timeout')
			time.sleep(5)

	# Create dataframe lists
	ID = get_game_id(schedule, 'gamePk')
	game_date_time = get_game_id(schedule, 'gameDate')
	local_game_time = get_local_time(game_date_time)
	live_or_not = get_live(schedule)

	#Get live scoreboard clock for live games
	if 'Live' in live_or_not:
		for attempts in range(5):
			try:
				scoreboard = json.loads(requests.get(score_url).text.replace("loadScoreboard(","").replace(")",""))['games']
				live_time = get_live_time(ID, local_game_time, scoreboard)
				live_time_no_spoil = get_live_time_no_spoil(ID, local_game_time, scoreboard)
				break
			except:
				print ('scoreboard timeout')
				time.sleep(5)
	else:
		live_time = get_no_live_time(schedule, local_game_time)
		live_time_no_spoil = get_no_live_time(schedule, local_game_time)

	away_team_id = get_team_id(schedule, 'away')
	away_team_name = get_team_name(schedule, 'away')
	away_team_score = get_team_score(schedule, 'away')

	home_team_id = get_team_id(schedule, 'home')
	home_team_name = get_team_name(schedule, 'home')
	home_team_score = get_team_score(schedule, 'home')

	combined_team_percentage = get_team_combined_record(schedule)
	home_win_percentage = get_team_record(schedule, 'home')
	away_win_percentage = get_team_record(schedule, 'away')
	win_percentage_difference = get_team_difference_record(schedule)

	#Create dictionary for dataframe
	Data_Frame = {
		'ID': ID,
		'Live' : live_or_not,
		'Live Time' : live_time,
		'Live Time No Spoil' : live_time_no_spoil,
		'Away Team ID' : away_team_id,
		'Away Team Name' : away_team_name,
		'Away Team Score' : away_team_score,
		'Home Team ID' : home_team_id,
		'Home Team Name' : home_team_name,
		'Home Team Score': home_team_score,
		'Game Date - Time' : game_date_time,
		'Local Game Time' : local_game_time,
		'Combined Win Percentage' : combined_team_percentage,
		'Home Win Percentage' : home_win_percentage,
		'Away Win Percentage' : away_win_percentage,
		'Win Percentage Difference' : win_percentage_difference
		}

	#Convert to pandas dataframe
	Data_Frame = pd.DataFrame(Data_Frame)

	#Clean refresh on GUI
	for games in range(size):
		column_1[games].set(" ")
		column_2[games].set(" ")
		column_3[games].set(" ")
		column_4[games].set(" ")

	#Data Frame to show only live games
	if live_games.get() == 1:
		Data_Frame = Data_Frame[Data_Frame['Live'] == 'Live']
		if len(Data_Frame) == 0:
			column_1[0].set("No Live Games")

	#Data Frame to sort by requested option
	try:
		Data_Frame = Data_Frame.sort_values(by=[main_option_select], ascending=False).reset_index(drop=True)
		column_4_set = []
		for games in range(len(Data_Frame['Away Team Name'])):
			column_4_set.append(" ")
			column_4_set.append(Data_Frame[main_option_select][games])
			column_4_set.append(" ")
		for games in range(len(column_4_set)):
			column_4[games].set(column_4_set[games])
	except:
		pass

	#Assign Logos only if any data changed (to avoid flickering)
	if logo_holder != ID or logo_holder2 != len(Data_Frame) or logo_holder3 != main_option_select:
		refresh_logos()
		logo_holder = ID
		logo_holder2 = len(Data_Frame)
		logo_holder3 = main_option_select

	#Label Team names
	column_1_set = []
	for games in range(len(Data_Frame['Away Team Name'])):
		column_1_set.append(Data_Frame['Away Team Name'][games])
		column_1_set.append(Data_Frame['Home Team Name'][games])
		column_1_set.append(" ")

	#No Spoilers or Spoilers and show scores and game time if enabled
	if no_spoilers.get() == 1:
		column_2_set = [" " for blank in range(len(column_1_set))]
		column_3_set = []
		for games in Data_Frame['Live Time No Spoil']:
			column_3_set.append(" ")
			column_3_set.append(games)
			column_3_set.append(" ")
	else:
		column_2_set = []
		column_3_set = []
		for games in range(len(Data_Frame['Away Team Name'])):
			column_2_set.append(Data_Frame['Away Team Score'][games])
			column_2_set.append(Data_Frame['Home Team Score'][games])
			column_2_set.append(" ")
			column_3_set.append(" ")
			column_3_set.append(Data_Frame['Live Time'][games])
			column_3_set.append(" ")

	#Assign values to columns
	for games in range(len(column_1_set)):
		column_1[games].set(column_1_set[games])
		column_2[games].set(column_2_set[games])
		column_3[games].set(column_3_set[games])

	#Restart loop
	master.after((refresh*1000), continual_loop)

#Main
if __name__ == '__main__':
	continual_loop()

#Quit button
Button(master, text='Quit', command=master.destroy).grid(row=size+1, column=0, sticky=W, pady=4)

#For Tkinter to run
mainloop()