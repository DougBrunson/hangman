# -*- coding: utf-8 -*-`
"""api.py - Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users."""


import logging
import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import *
from utils import get_by_urlsafe

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
CANCEL_GAME_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1),)

GET_GAME_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1),)

MOVE_REQUEST = endpoints.ResourceContainer(
    MoveForm, urlsafe_game_key=messages.StringField(1),)

USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))

HIGH_SCORE_REQUEST = endpoints.ResourceContainer(
    number_of_results=messages.IntegerField(1))


MEMCACHE_MOVES_REMAINING = 'MOVES_REMAINING'


@endpoints.api(name='hangman', version='v1')
class HangmanApi(remote.Service):

    """Game API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                'A User with that name already exists!')
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message='User {} created!'.format(
            request.user_name))

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')
        try:
            game = Game.new_game(user.key, request.attempts)
        except ValueError:
            raise endpoints.BadRequestException('Error creating a new game')

        # Use a task queue to update the average attempts remaining.
        # This operation is not needed to complete the creation of a new game
        # so it is performed out of sequence.
        taskqueue.add(url='/tasks/cache_average_attempts')
        return game.to_form('Good luck playing hangman!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game and not game.game_over:
            return game.to_form('Time to make a move!')
        elif game:
            return game.to_form('Game over.')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game.game_over:
            return game.to_form('Game already over!')

        elif request.guess in game.guesses:
            return game.to_form('Already guessed')

        else:
            game.attempts_remaining -= 1
            game.guess(request.guess.lower())
            win = game.check_win()
            game.put()
            if win:
                game.end_game(won=True)
                return game.to_form('You win!')

            elif game.attempts_remaining == 0:
                game.end_game()
                return game.to_form('You lost')
            else:
                return game.to_form('Guess again')

    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""

        # score != ranking. All players are ranked. Players are only
        # scored once they have played a game
        return ScoreForms(items=[score.to_form() for score in
                                 Score.query().order(-Score.score)])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='scores/user/{user_name}',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Returns all of an individual User's scores"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')
        scores = Score.query(Score.user == user.key).order(-Score.score)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(response_message=StringMessage,
                      path='games/average_attempts',
                      name='get_average_attempts_remaining',
                      http_method='GET')
    def get_average_attempts(self, request):
        """Get the cached average moves remaining"""
        return StringMessage(message=memcache.get(
            MEMCACHE_MOVES_REMAINING) or '')


# -------------------- begin added endpoints ----------------------- #

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='games/user/{user_name}',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Returns all of an individual User's games"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')
        games = Game.query(Game.user == user.key)
        return GameForms(items=[game.to_form() for game in games])

    @endpoints.method(request_message=CANCEL_GAME_REQUEST,
                      response_message=StringMessage,
                      path='game/{urlsafe_game_key}/cancel',
                      name='cancel_game',
                      http_method='POST')
    def cancel_game(self, request):
        """Cancels game"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
            raise endpoints.NotFoundException("Game Not Found")

        if not game.game_over:
            game.key.delete()
            return StringMessage(message="Game cancelled!")
        else:
            return StringMessage(message="Cant cancel completed game".format(
                game.key.urlsafe()))

    @endpoints.method(request_message=HIGH_SCORE_REQUEST,
                      response_message=ScoreForms,
                      path='scores/highscore',
                      name='get_high_scores',
                      http_method='GET')
    def get_high_scores(self, request):
        """Gets highscores"""
        scores = Score.query(Score.won == True).order(
            -Score.score).fetch(request.number_of_results)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(response_message=UserForms,
                      path='ranking',
                      http_method='GET',
                      name='get_user_rankings')
    def get_user_rankings(self, request):
        """Gets user rankings"""
        users = User.query(User.win_ratio >= 0).order(-User.win_ratio)
        return UserForms(items=[user.to_form() for user in users])

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameHistoryForm,
                      path='game/history/{urlsafe_game_key}',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Gets game history """
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
            raise endpoints.NotFoundException('Game not found!')
        return MoveHistoryForm(moves=game.guesses)


# -------------------- end added endpoints ------------------------- #

    @staticmethod
    def _cache_average_attempts():
        """Populates memcache with the average moves remaining of Games"""
        games = Game.query(Game.game_over == False).fetch()
        if games:
            count = len(games)
            total_attempts_remaining = sum([game.attempts_remaining
                                            for game in games])
            average = float(total_attempts_remaining)/count
            memcache.set(MEMCACHE_MOVES_REMAINING,
                         'The average moves remaining is \
                         {:.2f}'.format(average))


api = endpoints.api_server([HangmanApi])
