import praw
from time import time, sleep
from sys import exc_clear
from urllib import quote
import json
 
def main():
    configfile = open('flairbot.json','r')
    settings = json.loads(configfile.read())

    username = settings['username']
    password = settings['password']

    subreddit_name = "mod"

    #Bot Settings
    sleep_time = settings['sleep_time'] # e.g. 300 time (in seconds) the bot sleeps before performing a new check
    time_until_message = settings['time_until_message'] # e.g. 180 - time (in seconds) a person has to add flair before a initial message is sent
    time_until_remove = settings['time_until_remove'] # e.g. 600 - time (in seconds) after a message is sent that a person should flair before the post is removed and they have to resubmit it

    post_grab_limit = settings['post_grab_limit'] #20 # how many new posts to check at a time.
    post_memory_limit = settings['post_memory_limit'] #100 # how many posts the bot should remember before rewriting over it

    #Initial Message that tells then that they need to flair their post
    add_flair_message = settings['add_flair_message']

    #Second message telling them to resubmit their post since they have not flaired in time
    remove_post_message = settings['remove_post_message']

    no_flair = {}
    already_done = []
    post_age = time_until_message + time_until_remove
    user_agent = ( "Auto flair moderator for reddit created by /u/kooldawgstar [modified by /u/thorax]") # tells reddit the bot's purpose.
    session = praw.Reddit( user_agent = user_agent )

    #Loop
    while True:
        # memory clean up code
        # keeps arrays at reasonable sizes
        if len( already_done ) >= post_memory_limit:
            i = 0
            posts_to_forget = post_memory_limit - post_grab_limit
            while i < posts_to_forget:
                already_done.pop( 0 )
                i += 1
        # try-catch runtime issues. Prevents bot from crashing when a problem is encountered. 
        # Most frequent trigger is a connection problemsuch as when reddit is down
        try:
            # refresh the login
            session.login( username = username, password = password, disable_warning=True )
            acceptmodinvites(session)
            subreddit=session.get_subreddit( subreddit_name )

            # get newest submissions
            newcount = 0
            for submission in subreddit.get_new( limit = post_grab_limit ):
                # if post has not already been processed
                if submission.id not in already_done:
                    # if post is older than specified age and not too old, check it
                    age = time() - submission.created_utc
                    print "+", age, submission.id, "by", submission.author, "\n+\tTitle:", submission.title
                    if age > time_until_message:
                        newcount+=1
                        if age < post_age + time_until_message:
                            print "\nChecking:", submission.id
                            # if post does not have flair
                            if ( submission.link_flair_text is None ):
                                # if post has not already been flagged for not having flair
                                if submission.id not in no_flair.keys():
                                    # reply with distinguished message about the flair, then remove post
                                    final_add_flair_message = add_flair_message.format( post_url = submission.short_link, removal_time = formatTimeString( time_until_remove ))
                                    replyobj = submission.add_comment(final_add_flair_message)
                                    replyobj.distinguish()
                                    submission.remove()
                                    #save comment so we can edit it later
                                    no_flair[submission.id]=replyobj.id
                                    print "\tFlair warning sent on post", submission.id
                            else:
                                print "\tFlair existed:", submission.link_flair_text
                        already_done.append(submission.id)
                        #if the post has flair, it is added to already_done
                        print "Done checking:", submission.id
                    else:
                        print "Not ready yet:", submission.id, age
            print "Reviewed mod queue (" + str(newcount) + " new)"
            print "Checking known unflaired links (" + str(len(no_flair)) + " watched)"
            for postid in list(no_flair):
                replyid = no_flair[postid]
                # get the post and comment objects
                submission = session.get_info(thing_id="t3_" + postid)
                repl = session.get_info(thing_id="t1_" + replyid)
                if submission is not None:
                    if ( submission.link_flair_text is not None ):
                        print "Flair exists for:", submission.id, submission.author
                        # if there is a flair, let's approve it and delete our response
                        submission.approve()
                        if repl is not None:
                            repl.delete()
                        else:
                            print "\nWARNING: Couldn't delete comment:", replyid
                        del no_flair[postid]
                    else:                   
                        #checks if the post is past the set age
                        if ( ( time() - submission.created_utc ) > post_age ):
                            print "Flair timeout, permanent removal:", submission.id, submission.author
                            final_remove_post_message = remove_post_message.format( post_url = submission.short_link )
                            #update our message, keep the post removed
                            if repl is not None:
                                repl.edit(final_remove_post_message)
                            else:
                                print "Couldn't edit comment:", replyid
                            del no_flair[postid]
                else:
                    print "\nWARNING: Couldn't find submission:", postid
        #handles runtime errors.
        except Exception, e:
            #clears the exception
            print e
            exc_clear()
        sleep( sleep_time )

#Auto accept mod invites
def acceptmodinvites(r):
    for message in r.get_unread():
        if message.body.startswith('**gadzooks!'):
            sr = r.get_info(thing_id=message.subreddit.fullname)
            try:
                sr.accept_moderator_invite()
            except praw.errors.InvalidInvite:
                continue
            message.mark_as_read()

# turn a time in seconds into a human readable string
def formatTimeString(time_in):
     minutes, seconds = divmod( time_in, 60 )
     hours, minutes = divmod( minutes, 60 )
     time_string = ""
     if hours > 0:
          time_string += "{0} hour".format(hours)
          if hours > 1:
               time_string += "s"
          time_string += " "
     if minutes > 0:
          time_string += "{0} minute".format(minutes)
          if minutes > 1:
               time_string += "s"
          time_string += " "
     if seconds > 0:
          time_string += "{0} second".format(seconds)
          if seconds > 1:
               time_string += "s"
          time_string += " "
     return time_string[:-1]



#call main fuctions
main()
