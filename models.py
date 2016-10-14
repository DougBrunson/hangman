"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Because these classes are also regular Python
classes they can include methods (such as 'to_form' and 'new_game')."""

import random
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb


WORDS = ['book', 'desk', 'glass', 'laptop', 'pen', 'paper',
         'window', 'cellphone', 'printer', 'headphones', 'coffee']


def get_random_word():
    # TODO: integrate rand word api
    return random.choice(WORDS)


# --------------- data models ----------------------

class User(ndb.Model):
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()
    wins = ndb.IntegerProperty(default=0)
    games_played = ndb.IntegerProperty(default=0)
    win_ratio = ndb.FloatProperty(default=0)

    def to_form(self):
        return UserForm(user_name=self.name,
                        wins=self.wins,
                        loses=self.games_played - self.wins,
                        win_ratio=self.win_ratio)


class Game(ndb.Model):
    user = ndb.KeyProperty(required=True, kind='User')
    game_over = ndb.BooleanProperty(required=True, default=False)
    word = ndb.StringProperty(required=True)
    word_status = ndb.StringProperty(required=True)
    attempts_allowed = ndb.IntegerProperty(required=True)
    attempts_remaining = ndb.IntegerProperty(required=True, default=5)
    guesses = ndb.StringProperty(repeated=True)

    @classmethod
    def new_game(cls, user, attempts):
        """Creates and returns a new game"""

        # use word len as arg?
        word = get_random_word()

        # make sure attempt >= len(word)
        if attempts < len(word):
            attempts = len(word)

        game = Game(user=user,
                    attempts_allowed=attempts,
                    attempts_remaining=attempts,
                    word=word,
                    word_status='-'*len(word),
                    game_over=False)
        game.put()
        return game

    def check_win(self):
        return self.word == self.word_status

    def guess(self, char):
        self.guesses.append(char)
        if char in self.word:
            for i in range(len(self.word)):
                a, b = list(self.word), list(self.word_status)
                if a[i] == char:
                    b[i] = char
                    self.word_status = ''.join(b)

    def to_form(self, message=''):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.user.get().name
        form.attempts_remaining = self.attempts_remaining
        form.word_status = self.word_status
        form.game_over = self.game_over
        form.message = message
        return form

    def end_game(self, won=False):
        self.game_over = True
        self.put()

        # score is word len / attempts normed to 1
        score = float(len(self.word)) / \
            float(self.attempts_allowed - self.attempts_remaining)
        score = score if score <= 1.0 else 1.0
        score = Score(user=self.user, date=date.today(), won=won,
                      score=score)
        score.put()

        u = self.user.get()
        u.games_played += 1
        if won:
            u.wins += 1
        u.win_ratio = float(u.wins)/float(u.games_played)
        u.put()


class Score(ndb.Model):
    user = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateProperty(required=True)
    won = ndb.BooleanProperty(required=True)
    score = ndb.FloatProperty(required=True)

    def to_form(self):
        return ScoreForm(user_name=self.user.get().name, won=self.won,
                         date=str(self.date), score=self.score)


# ----------------- forms -----------------------------

class StringMessage(messages.Message):
    message = messages.StringField(1, required=True)


class UserForm(messages.Message):
    user_name = messages.StringField(1, required=True)
    wins = messages.IntegerField(2, required=True)
    loses = messages.IntegerField(3, required=True)
    win_ratio = messages.FloatField(4, required=True)


class UserForms(messages.Message):
    items = messages.MessageField(UserForm, 1, repeated=True)


class GameForm(messages.Message):
    urlsafe_key = messages.StringField(1, required=True)
    attempts_remaining = messages.IntegerField(2, required=True)
    word_status = messages.StringField(3, required=True)
    game_over = messages.BooleanField(4, required=True)
    message = messages.StringField(5, required=True)
    user_name = messages.StringField(6, required=True)


class NewGameForm(messages.Message):
    user_name = messages.StringField(1, required=True)
    attempts = messages.IntegerField(2, default=5)


class GameForms(messages.Message):
    items = messages.MessageField(GameForm, 1, repeated=True)


class GameHistoryForm(messages.Message):
    moves = messages.StringField(1, repeated=True)


class MoveForm(messages.Message):
    guess = messages.StringField(1, required=True)


class ScoreForm(messages.Message):
    user_name = messages.StringField(1, required=True)
    date = messages.StringField(2, required=True)
    won = messages.BooleanField(3, required=True)
    score = messages.FloatField(4, required=True)


class ScoreForms(messages.Message):
    items = messages.MessageField(ScoreForm, 1, repeated=True)
