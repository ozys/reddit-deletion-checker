import urllib.request
import sqlite3
import json
import time
from datetime import datetime

# Whoever is running the bot, put your reddit username here.
# This is important for following the API rules.
# More info here: https://github.com/reddit/reddit/wiki/API
bot_operator = ""
longtail = False # "True" if you want to watch the top 1000 instead of the top 100.

def get_json(url):
    while True:
        header_dictionary = {"User-agent": "Post deletion checker v0.2 operated by /u/" + bot_operator}
        try:
            url_handle = urllib.request.urlopen(urllib.request.Request(url, headers=header_dictionary))
            url_data = url_handle.read()
            json_data = json.loads(url_data.decode())
            # Don't spam the reddit servers *too* badly:
            time.sleep(0.5)
            return json_data
        except:
            # Network error. Try again in 10 seconds.
            time.sleep(10)
            continue

def get_posts(subreddit):
    global longtail
    posts = []
    url = "http://reddit.com/r/" + subreddit + "/.json?limit=100"
    now = datetime.now()
    json_data = get_json(url)
    counter = 1
    for post in json_data["data"]["children"]:
        post_dict = {
            "id": post["data"]["id"],
            "subreddit": post["data"]["subreddit"],
            "rank": counter,
            "title": post["data"]["title"],
            "author": post["data"]["author"],
            "score": post["data"]["score"],
            "created": post["data"]["created"],
            "permalink": "http://reddit.com" + post["data"]["permalink"],
            "link_flair_text": post["data"]["link_flair_text"],
            "num_comments": post["data"]["num_comments"],
            "last_checked": now
        }
        posts.append(post_dict)
        counter += 1
    after = json_data["data"]["children"][-1]["data"]["name"]

    # Ugghh I hate the way I have to access the next pages.
    # I wish I could just say "&page=x" to get an arbitrary page
    # instead of having to go through each page like a fucking linked list.
    pages = 4
    if longtail:
        pages = 14
    for x in range(pages):
        url = "http://reddit.com/r/" + subreddit + "/.json?limit=100&after=" + after
        json_data = get_json(url)
        for post in json_data["data"]["children"]:
            post_dict = {
                "id": post["data"]["id"],
                "subreddit": post["data"]["subreddit"],
                "rank": counter,
                "title": post["data"]["title"],
                "author": post["data"]["author"],
                "score": post["data"]["score"],
                "created": post["data"]["created"],
                "permalink": "http://reddit.com" + post["data"]["permalink"],
                "link_flair_text": post["data"]["link_flair_text"],
                "num_comments": post["data"]["num_comments"],
                "last_checked": now
            }
            posts.append(post_dict)
            counter += 1
        after = json_data["data"]["children"][-1]["data"]["name"]
    return posts

def set_up_database(c):
    c.execute('''CREATE TABLE IF NOT EXISTS watched (
                    i INTEGER PRIMARY KEY AUTOINCREMENT,
                    id CHAR(10) NOT NULL,
                    subreddit CHAR(50) NOT NULL,
                    rank INTEGER NOT NULL,
                    title CHAR(200) NOT NULL,
                    author CHAR(50) NOT NULL,
                    score INTEGER NOT NULL,
                    created INTEGER NOT NULL,
                    permalink CHAR(200) NOT NULL,
                    link_flair_text CHAR(50),
                    num_comments INTEGER NOT NULL,
                    last_checked TIMESTAMP NOT NULL
                    )''')
    c.execute('''DELETE FROM watched''')

def add_to_watched(conn, c, post):
    # This is kinda messy. It's just inserting one post into the "watched" table as one row.
    c.execute('''INSERT INTO watched
        (id, subreddit, rank, title, author, score, created, permalink, link_flair_text, num_comments, last_checked)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (post["id"], post["subreddit"], post["rank"], post["title"], post["author"], post["score"],
            int(post["created"]), post["permalink"], post["link_flair_text"], post["num_comments"], post["last_checked"]))
    conn.commit()

if __name__ == "__main__":
    if bot_operator == "":
        print("Please set the \"bot_operator\" variable as your username at the top of the script.")
    else:
        subreddit = "all"

        conn = sqlite3.connect('watched.sqlite')
        c = conn.cursor()
        set_up_database(c)

        # Initialize the database with some threads to watch
        print("Initializing posts for /r/" + subreddit)
        posts = get_posts(subreddit)
        for post in posts[0:100]:
            add_to_watched(conn, c, post)

        print("")
        print("Sleeping for 5 minutes.")
        # Wait 5 minutes; nothing is likely to change in this time.
        # Please don't change this to anything lower.
        time.sleep(5*60)

        # Now, we can check if any posts have been deleted (in a loop).
        while True:
            print("")
            
            c.execute('''SELECT * FROM watched''')
            print("Checking /r/" + subreddit + "")
            previous_posts = c.fetchall()
            posts = get_posts(subreddit)
            for prev in previous_posts:
                alive = False
                for post in posts:
                    if post["id"] == prev[1]:
                        alive = True
                if not alive:
                    print("DETECTED DELETION:")
                    print("    Subreddit: /r/" + prev[2])
                    print("    Author: /u/" + prev[5])
                    print("    #" + str(prev[3]) + " with " + str(prev[6]) + " karma and " + str(prev[10]) + " comments:")
                    print("    \"" + prev[4] + "\"")
                    print("    " + prev[8])
                    print("    Deleted sometime around " + prev[11])
                    print("")
            print("Done with /r/" + subreddit)
            print("")

            # Re-initialize this subreddit; we only care about the top 100 (or 1000 if longtail).
            c.execute('''DELETE FROM watched''')
            conn.commit()
            number_to_watch = 100
            if longtail:
                number_to_watch = 1000
            for post in posts[0:number_to_watch]:
                add_to_watched(conn, c, post)

            print("Sleeping for 5 minutes.")
            # Wait 5 minutes; nothing is likely to change in this time.
            # Please don't change this to anything lower.
            time.sleep(5*60)
