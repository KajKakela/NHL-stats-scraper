from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import pandas as pd

# Getting yesterday's date as formatted
# Modifying the timedelta() we can search for different days. timedelta(1) means yesterday, timedelta(2) means the day before yesterday etc.
yesterdays_date = datetime.today()-timedelta(1)
yesterday_formatted_date = yesterdays_date.strftime("%Y%m%d")

# espn_url is the first part of the url which will never change, the rest of the url will change
espn_url = "https://www.espn.com"
# Second part of the URL. This will be used with "yesterday_formatted_date" variable to get the URL of yesterday's games
first_page_url = "/nhl/scoreboard/_/date/"

# Assigning empty list for the links of gameid's the program is going to get from scraping the first page
gameid_links = []
# Assigning empty lists for later use. These will contain lists of results, away and home team stats for every game of yesterday
all_results = []
all_away_stats = []
all_home_stats = []
# Assigning empty dict for team names the program is scraping from every game of yesterday
team_names = {}


try:
    # The very first HTML page the program is going to scrape
    url = f"{espn_url}{first_page_url}{yesterday_formatted_date}"
    # Some websites raises HTTPError if not using headers, so the program is pretending to be Mozilla client to get the wanted data
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    # variable containing full URL request and calling function read() to read the HTML
    website = urlopen(req).read()
    # BeautifulSoup constructor and lxml parser to parse the website
    soup = BeautifulSoup(website, "lxml")

# Handling exceptions and saving the error messages to errors.txt for later inspecting
except HTTPError as hE:
    with open("errors.txt", "a") as errors:
        errors.write(f"{datetime.today()}: {hE}")

except URLError as uE:
    with open("errors.txt", "a") as errors:
        errors.write(f"{datetime.today()}: {uE}")

# Looping through the whole HTML page to find <a> tags with attribute "href" containing the word "boxscore".
# When program finds a wanted link, it will append it to the gameid_links list.
for link in soup.find_all("a", href=re.compile(".*boxscore.*")):
    gameid_links.append(link.get("href"))

# Function to scrape team names from every game
def get_team_names():
    i = 0
    x = 1
    y = 2
    for game in gameid_links:
        # Changing the URL so we cand loop through every game of yesterday
        url = f"{espn_url}{gameid_links[i]}"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        website = urlopen(req).read()
        soup = BeautifulSoup(website, "lxml")

        # Finding all divs which have class named "BoxscoreItem__TeamName h5"
        teams = soup.find_all("div", {"class":"BoxscoreItem__TeamName h5"})
        # .get_text() returns all the text from the div and saves it to teams_strings variable 
        teams_strings = [team.get_text() for team in teams]

        # Assigning team1, team2.. to team_names dict as keys and giving the scraped team names to them as values
        team_names["team" + str(x)] = teams_strings[0]
        team_names["team" + str(y)] = teams_strings[1]

        i += 1
        x += 2
        y += 2

# Function to scrape the result of every game and store them to list called all_results
def get_result():
    i = 0
    for game in gameid_links:
        # Reading the html page of every game and storing all the html tables to df_result list dataframe
        df_result = pd.read_html(f"{espn_url}{gameid_links[i]}")

        # Creating new pandas dataframe and storing the very first table to it.
        # Inspecting the HTML page we know the first table contains the result of the game
        result = df_result[0]

        # The result table will have 5 or 6 columns depending if the went to overtime or not.
        # Checking if the table have column for the overtime so we can rename the colums correctly
        if len(result.columns) == 5:
            result.set_axis(["Team", "1", "2", "3", "Final"], axis="columns", inplace=True)
        else:
            result.set_axis(["Team", "1", "2", "3", "OT", "Final"], axis="columns", inplace=True)
        
        # Appending all the data from result dataframe to all_results list
        all_results.append(result)
        i += 1

# Function to get stats of the away team
def get_away_stats():
    i = 0
    for game in gameid_links:
        # Creating dataframe for storing all the html tables and scraping the website.
        # We need to skip the very first row, otherwise in the later stage the first row will cause problems when 
        # concatenating two tables by having two rows of headers
        df = pd.read_html(f"{espn_url}{gameid_links[i]}",skiprows=[1])
        
        # Storing player names and their stats to two different dataframes
        away_players = df[1]
        away_stats = df[2]

        # Using iloc to select by index which stats to keep when creating the final table
        away_stats_we_want = away_stats.iloc[:,[0,1,2,3,7,12,13,14,16,17,18]]

        # Concatenating the tables to get one dataframe with player names and their stats
        away_frames = [away_players, away_stats_we_want]
        away_final_stats = pd.concat(away_frames, axis=1, ignore_index=True)
        # Renaming the columns. Without renaming the names would be just index numbers
        away_final_stats.set_axis(["Forwards","G","A","+/-","S","PIM","TOI","PPTOI","SHTOI","FW","FL","FO%"], axis="columns", inplace=True)
        # Appending the dataframe to list
        all_away_stats.append(away_final_stats)
        i += 1

# This function works exactly like the last one but for the Home team
def get_home_stats():
    i = 0
    for game in gameid_links:
        df = pd.read_html(f"{espn_url}{gameid_links[i]}",skiprows=[1])
        home_players = df[5]
        home_stats = df[6]

        home_stats_we_want = home_stats.iloc[:,[0,1,2,3,7,12,13,14,16,17,18]]
        home_frames = [home_players, home_stats_we_want]

        home_final_stats = pd.concat(home_frames, axis=1, ignore_index=True)
        home_final_stats.set_axis(["Forwards","G","A","+/-","S","PIM","TOI","PPTOI","SHTOI","FW","FL","FO%"], axis="columns", inplace=True)
        
        all_home_stats.append(home_final_stats)
        i += 1
   
# Function to save all the scraped data to HTML file
def join_game_stats():
    i = 0
    x = 1
    y = 2
    
    # Looping through the gameid_links list to assign team1 and team2 variables as many times as there are games 
    for game in gameid_links:
        team1 = team_names.get("team"+str(x))
        team2 = team_names.get("team"+str(y))
        
        # Creating HTML file using naming rule: yesterday's date + away team + home team, Joined by underscore
        # The program creates own HTML file for each game
        with open(f"{yesterday_formatted_date}_{team1}_{team2}.html", "w") as save_file:
            save_file.write(all_results[i].to_html() + "<br>" + all_away_stats[i].to_html() + "<br>" + all_home_stats[i].to_html())
            
        i += 1
        x += 2
        y += 2

# Function to edit the HTML files to make them little bit more readable
def edit_html():
    i = 0
    x = 1
    y = 2

    for game in gameid_links:
        team1 = team_names.get("team"+str(x))
        team2 = team_names.get("team"+str(y))

        # Opening the HTML file
        with open(f"{yesterday_formatted_date}_{team1}_{team2}.html", "r+") as html:
            # Reading through the HTML
            soup = BeautifulSoup(html.read(), features="html.parser")

            # Finding all <tr> tags which have "style" attribute and storing them to list
            # There are 2 tags to find and those are the header rows for each table
            trs = soup.find_all("tr", style=True)
            # Looping through the list and modifying the style attribute so the text in table is centered
            for tr in trs:
                tr["style"] = "text-align: center"

            # Finding all two <td> tags which have word "defensemen" in it and storing them to list
            defs = soup.find_all("td", string="defensemen")
            # Looping through the <td> tags and selecting their parent element which is <tr> tag and giving bold and centered text to them
            # This <tr> tag is header row for the stats of defensemen
            for td in defs:
                td.parent["style"] = "font-weight:bold;text-align:center"

        # Saving the file with the same name
        with open(f"{yesterday_formatted_date}_{team1}_{team2}.html", "w") as save_new_file:
            save_new_file.write(str(soup))

        i += 1
        x += 2
        y += 2


get_team_names()
get_result()
get_away_stats()
get_home_stats()
join_game_stats()
edit_html()