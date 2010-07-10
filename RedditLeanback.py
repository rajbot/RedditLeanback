#!/usr/bin/python

"""
Usage: ./RedditLeanback.py user@gmail.com password

Requires the Google Data Python Library:
http://code.google.com/apis/gdata/articles/python_client_lib.html
"""

import gdata.youtube
import gdata.youtube.service

import sys
import os
import json
import urllib
import re
import time
from urlparse import urlparse

# configuration globals
#_______________________________________________________________________________
devKeyFile = os.path.expanduser('~/.youtubeDevKey')

#unfortunately, youtube leanback only shows up to three playlists...
playlistDict = {'Reddit Videos': ['/r/videos'], 
                'Reddit Happy' : ['/r/aww', '/r/funny'],
                'Reddit Music' : ['/r/futurefunkairlines', '/r/idm', '/r/electronicmusic', '/r/dnb/', '/r/breakcore/', '/r/dubstep', '/r/darkstep', '/r/raggajungle/'],
               }

# error checking 
#_______________________________________________________________________________
if not os.path.exists(devKeyFile):
    print "You need to provide a Youtube API Developer Key. It should be placed in " + devKeyFile
    sys.exit()

if 3 != len(sys.argv):
    print "You must supply an email address and password as arguments to this script!"
    sys.exit()

# login()
#_______________________________________________________________________________
def login():
    yt_service = gdata.youtube.service.YouTubeService()
    
    # The YouTube API does not currently support HTTPS/SSL access.
    yt_service.ssl = False
    
    yt_service.email = sys.argv[1]
    yt_service.password = sys.argv[2]
    yt_service.source = 'RedditLeanback'
    yt_service.client_id = 'RedditLeanback'
    
    f = open(devKeyFile)
    devKey = f.read().strip()
    f.close()
    yt_service.developer_key = devKey
    
    yt_service.ProgrammaticLogin()
    return yt_service

# getUriForPlaylist()
#_______________________________________________________________________________
def getUriForPlaylist(playlist, playlistFeed):
    """
    Returns the URI for the specified playlist in playlistFeed.
    Returns None if the playlist was not found.
    """
    for entry in playlistFeed.entry:
        if entry.title.text == playlist:
            
            o = urlparse(entry.id.text)
            playlistId = os.path.basename(o.path)
            playlistUri = "http://gdata.youtube.com/feeds/api/playlists/" + playlistId            
            return playlistUri

    return None

# getPlaylistUris()
#_______________________________________________________________________________
def getPlaylistUris(yt_service):
    """
    Retrieve a playlistUri for each playlist in playlistDict.
    If a playlist has not already been created, we will create one for you.
    """
    
    print 
    print "Gathering playlist information"
    print "______________________________"

    playlistFeed = yt_service.GetYouTubePlaylistFeed(uri='http://gdata.youtube.com/feeds/api/users/default/playlists')

    playlistUris = {}
    
    for playlist in playlistDict:
        print "Looking for URI for playlist " + playlist
        playlistUri = getUriForPlaylist(playlist, playlistFeed)
        
        if None != playlistUri:
            print "  Found uri " + playlistUri
        else:
            print "  Playlist not found. Creating new playlist!"
            newPlaylist = yt_service.AddPlaylist(playlist, 'Automatically created playlist for Reddit Leanback')
            playlistUri = newPlaylist.id.text
            print "  Created new playlist with URI " + playlistUri
            
        playlistUris[playlist] = playlistUri
    
    print "\n"
    return playlistUris


# parseVideoId()
#_______________________________________________________________________________
def parseVideoId(url):
    """
    find youtube video id, using regex from http://stackoverflow.com/questions/2597080/regex-to-parse-youtube-yid/2601838#2601838
    I added a hash to the terminating charset in the regex to work with timestamps
    """
    m = re.search('(?<=v=)[a-zA-Z0-9-]+(?=&)|(?<=[0-9]/)[^&#\n]+|(?<=v=)[^&#\n]+', url)
    return m.group(0)
    

# processSubreddit()
#_______________________________________________________________________________
def processSubreddit(subreddit, yt_service, playlistUri, playlistContents):
    print "  Adding videos for " + subreddit
    f = urllib.urlopen("http://www.reddit.com" + subreddit + ".json")
    c = f.read()
    f.close()
    links = json.loads(c)

    for link in links[u'data'][u'children']:
        if 'youtube.com' == link[u'data'][u'domain']:
            url = link[u'data'][u'url']
            
            videoId = parseVideoId(url)
            
            if videoId in playlistContents:
                print "    already added " + videoId
                continue
                
            print "    adding " + videoId + " to playlist " + playlistUri
            time.sleep(1)
            
            title = link[u'data'][u'title'][:100]
            description = "score: " + str(link[u'data'][u'score'])
            
            entry = yt_service.AddPlaylistVideoEntryToPlaylist(
                playlistUri, videoId, title, description)

    print "\n"
    
# getPlaylistContents()
#_______________________________________________________________________________
def getPlaylistContents(playlistUri):
    playlistContents = []
    
    feed = yt_service.GetYouTubePlaylistVideoFeed(uri=playlistUri)

    if None == feed:
        return playlistContents
        
    for entry in feed.entry:
        url = entry.GetHtmlLink().href
        videoId = parseVideoId(url)
        playlistContents.append(videoId)    

    return playlistContents
    
    
# addNewVideos()
#_______________________________________________________________________________
def addNewVideos(yt_service, playlistUris):
    """
    For each playlist in playlistDict, fetch youtube links for all subreddits
    """
    print "Fetching new videos"
    print "___________________\n"
    
    for (playlist, subreddits) in playlistDict.iteritems():
        print "Processing playlist " + playlist
        
        playlistContents = getPlaylistContents(playlistUris[playlist])
        
        for subreddit in subreddits:
            processSubreddit(subreddit, yt_service, playlistUris[playlist], playlistContents)
            

# __main__
#_______________________________________________________________________________

yt_service = login()

playlistUris = getPlaylistUris(yt_service)

addNewVideos(yt_service, playlistUris)