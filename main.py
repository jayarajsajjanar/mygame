#!/usr/bin/env python

"""main.py - This file contains handlers that are called by taskqueue and/or
cronjobs."""
import logging

import webapp2
from google.appengine.api import mail, app_identity
from api import Quizz

from models import User,Game


class SendReminderEmail(webapp2.RequestHandler):
    def get(self):
        """Send a reminder email to each User with an email about games.
        Called every hour using a cron job"""
        app_id = app_identity.get_application_id()
       
        #Checks if a game is pending. If it is, then a reminder mail is sent to the user.
        games=Game.query(Game.game_over==False) #self.user.get().name
        
        for game in games:
            subject = 'This is a reminder!'
            body = 'Hello {}, try out Guess A Number!'.format(game.user.get().name)
            # This will send test emails, the arguments to send_mail are:
            # from, to, subject, body
            mail.send_mail('jayarajsajjanar2010@gmail.com',#noreply@{}.appspotmail.com'.format(app_id),
                           game.user.get().email,
                           subject,
                           body)
        


class UpdateAverageMovesRemaining(webapp2.RequestHandler):
    def post(self):
        """Update game listing announcement in memcache."""
        Quizz._cache_average_attempts()
        self.response.set_status(204)
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('Hello !!')



app = webapp2.WSGIApplication([
    ('/crons/send_reminder', SendReminderEmail),
    ('/tasks/cache_average_attempts', UpdateAverageMovesRemaining),
], debug=True)
