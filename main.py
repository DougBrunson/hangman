#!/usr/bin/env python

"""main.py - This file contains handlers that are called by taskqueue and/or
cronjobs."""

import webapp2
from google.appengine.api import mail, app_identity
from api import HangmanApi

from google.appengine.ext import ndb
from models import User, Game


class SendReminderEmail(webapp2.RequestHandler):

    def get(self):
        """Send a reminder email to each User with an email about games.
        Called every hour using a cron job"""
        app_id = app_identity.get_application_id()

        # filter for open games & fetch 
        games = Game.query(Game.game_over == False)
        notify = set()
        for game in games:
            notify.add(game.user)
        users = ndb.get_multi(notify)

        for user in users:
            subject = 'Hangman is waiting for you!'
            body = 'Hello {}, You have an open game of Hangman. Come back and play now'.format(
                user.name)
            mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                           user.email,
                           subject,
                           body)


class UpdateAverageMovesRemaining(webapp2.RequestHandler):

    def post(self):
        """Update game listing announcement in memcache."""
        HangmanApi._cache_average_attempts()
        self.response.set_status(204)


app = webapp2.WSGIApplication([
    ('/crons/send_reminder', SendReminderEmail),
    ('/tasks/cache_average_attempts', UpdateAverageMovesRemaining),
], debug=True)
