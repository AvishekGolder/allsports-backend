from flask import Flask, render_template, jsonify
import requests
from time import time
from flask_cors import CORS
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__)
CORS(app)


PORT = int(os.environ.get("PORT", 5001))
mydomain = "http://127.0.0.1:" + str(PORT)


old_time = 0
raw_data = None
parsed_matches = None

def home_parse_matches(html_content):
    global cachelink
    """Parse match data from HTML content"""
    soup = BeautifulSoup(html_content, 'html.parser')
    matches = soup.select('.widget-content .match-event')
    
    result = []
    for match in matches:
        try:
            link_element = match.select_one('a#match-live')
            link = link_element['href'] if link_element else ""
            cachelink[re.sub(r'^(https?://[^/]+)', "", link)] = link
            link = re.sub(r'^(https?://[^/]+)', mydomain, link)
            title = link_element['title'] if link_element else ""
            
            team1_name_element = match.select_one('.first-team .team-name')
            team1_name = team1_name_element.text.strip() if team1_name_element else ""
            
            team1_logo_element = match.select_one('.first-team .team-logo img')
            team1_logo = team1_logo_element['src'] if team1_logo_element else ""
            
            team2_name_element = match.select_one('.left-team .team-name')
            team2_name = team2_name_element.text.strip() if team2_name_element else ""
            
            team2_logo_element = match.select_one('.left-team .team-logo img')
            team2_logo = team2_logo_element['src'] if team2_logo_element else ""
            
            match_time_element = match.select_one('.match-timing #match-hour')
            match_time = match_time_element.text.strip() if match_time_element else ""
            
            round_element = match.select_one('.match-info li span')
            round_info = round_element.text.strip() if round_element else ""
            
            match_data = {
                'title': title,
                'link': link,
                'team1_name': team1_name,
                'team1_logo': team1_logo,
                'team2_name': team2_name,
                'team2_logo': team2_logo,
                'match_time': match_time,
                'round': round_info
            }
            
            result.append(match_data)
        except Exception as e:
            print(f"Error parsing match: {e}")
    
    return result

def fetch_home_data():
    """Fetch and cache data from epicsports.me"""
    global old_time, raw_data, parsed_matches
    
    current_time = time()
    if raw_data is None or current_time - old_time > 120:  # Cache for 2 minutes
        print("Fetching fresh data from epicsports.me")
        old_time = current_time
        raw_data = requests.get('https://www.epicsports.online/').text
        parsed_matches = home_parse_matches(raw_data)
    
    return raw_data, parsed_matches


@app.route('/api/matches')
def match_data():
    """Return parsed match data as JSON"""
    _, matches = fetch_home_data()
    return jsonify(matches)








def get_match_lineups_and_links(url):
    response = requests.get(url)
    if response.status_code != 200:
        return "Failed to fetch the page"
    soup = BeautifulSoup(response.content, 'html.parser')
    lineups = []
    links = []

    lineup_elements = soup.find_all('div', class_='post-share text-center m-1')
    for element in lineup_elements:
        lineup_text = element.get_text(strip=True)
        if "XI:" in lineup_text:
            lineups.append(lineup_text)

    link_elements = soup.find_all('a', class_='fa fa-play')
    for element in link_elements:
        link = element.get('href')
        if link:
            links.append(link)

    return {
        'lineups': lineups,
        'links': links
    }


def fetch_page_data(path):
    match_data = get_match_lineups_and_links(cachelink[path])
    return render_template('pages.html', lineups=match_data['lineups'], links=match_data['links'])



pages = dict()
@app.route('/p/<path:path>')
def proxy(path):
    path = "/p/" + path
    global pages
    if path not in pages or time() - pages[path][0] > 120:
        if path not in cachelink:
            fetch_home_data()
        pages[path] = [time(), fetch_page_data(path)]

    return pages[path][1]

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=True)
