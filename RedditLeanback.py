#!/usr/bin/python

"""
Usage: ./RedditLeanback.py user@gmail.com password

This script creates YouTube playlists of interesting videos from Reddit.
These playlists can then be viewed on a home theater setup using Youtube Leanback.

Requires the Google Data Python Library and a youtube dev key:
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
import getpass


# configuration globals
#_______________________________________________________________________________
devKeyFile = os.path.expanduser('~/.youtubeDevKey')

#note: only the first four of my playlists are showing up in the Leanback interface...
playlistDict = {'Reddit Videos' : ['/r/videos'], 
                'Reddit Happy'  : ['/r/aww', '/r/funny'],
                'Reddit Music'  : ['/r/futurefunkairlines', '/r/idm', '/r/electronicmusic'],
                'Reddit DnB'    : ['/r/dnb/', '/r/breakcore/', '/r/dubstep', '/r/darkstep', '/r/raggajungle/'],
                'Reddit Lecures': ['/r/lectures', '/r/science'],
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
    
    #Captcha handler by Ryan Tucker
    #http://github.com/rtucker/gdata-captcha/blob/master/gdata-captcha.py
    try:
        yt_service.ProgrammaticLogin()
    except gdata.service.CaptchaRequired:
        captcha_token = yt_service._GetCaptchaToken()
        url = yt_service._GetCaptchaURL()
        print "Please go to this Captcha URL:"
        print "  " + url
        captcha_response = raw_input("Type the captcha image here: ")
        yt_service.ProgrammaticLogin(captcha_token, captcha_response)
        print "Done!"    
    
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
            
            playlistId = os.path.basename(entry.id.text)
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

    #print "processing url " + url
    #print "got video id " + m.group(0)
    
    
    if None == m:
        return None

    videoId = m.group(0)
    
    if 11 != len(videoId):
        print "error?! got a videoId that is not 11 chars long: " + videoId
        print "original url: " + url
        sys.exit()
        
    return videoId
    

# processSubreddit()
#_______________________________________________________________________________
def processSubreddit(subreddit, yt_service, playlistUri, playlistContents):
    print "  Adding videos for " + subreddit
    f = urllib.urlopen("http://www.reddit.com" + subreddit + ".json")
    c = f.read()
    f.close()
    links = json.loads(c)

    vids = links[u'data'][u'children']
    vids.reverse()
    
    for link in vids:
        if 'youtube.com' == link[u'data'][u'domain']:
            url = link[u'data'][u'url']
            
            videoId = parseVideoId(url)
            
            if None == videoId:
                print "    couldn't parse videoId from url " + url
                continue
            
            if videoId in playlistContents:
                print "    already added " + videoId
                continue
                
            print "    adding " + videoId + " to playlist " + playlistUri

            time.sleep(5)
            
            title = link[u'data'][u'title'][:100]
            description = "score: " + str(link[u'data'][u'score'])
            print "      with title: " + title
            
            #add to playlist
            entry = yt_service.AddPlaylistVideoEntryToPlaylist(
                playlistUri, videoId, title, description)

            entryId = os.path.basename(entry.id.text)
            print "    added to playlist with id: " + entryId
            
            #move to top of playlist
            newEntry = yt_service.UpdatePlaylistVideoEntryMetaData(
                playlistUri, entryId, title, description, 1)            
            
    print "\n"
    
# getPlaylistContents()
#_______________________________________________________________________________
def getPlaylistContents(playlistUri, playlistContents):
    
    print "  Getting Contents of playlist " + playlistUri
    
    feed = yt_service.GetYouTubePlaylistVideoFeed(uri=playlistUri)

    if None == feed:
        return

    print "  .. got %d entries" % len(feed.entry)
        
    for entry in feed.entry:

        htmlLink = entry.GetHtmlLink()
        if None == htmlLink:
            continue #suspended video
            
        url = htmlLink.href
        videoId = parseVideoId(url)
        playlistContents.append(videoId)    

    next = feed.GetNextLink()
    
    if None != next:
        getPlaylistContents(feed.GetNextLink().href, playlistContents)
    else:
        print "  playlist has %d videos\n" % len(playlistContents)
    
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
        
        playlistContents = []
        getPlaylistContents(playlistUris[playlist], playlistContents)

        for subreddit in subreddits:
            processSubreddit(subreddit, yt_service, playlistUris[playlist], playlistContents)
            

# __main__
#_______________________________________________________________________________

yt_service = login()

playlistUris = getPlaylistUris(yt_service)

addNewVideos(yt_service, playlistUris)