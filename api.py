"""api.py - This contains the game API exposing the resources.
The game logic is also implemented here. The models are imported."""


import logging
import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from models import User, Game, Score
from models import StringMessage, NewGameForm, GameForm, MakeMoveForm,\
    ScoreForms, GameForms, HighScoreForms, Moves, MoveForm, MoveForms,\
    get_user_rankings_form, get_high_scores_form, get_high_scores_forms
from utils import get_by_urlsafe
import random

# Resource container supports various other kinds of message passsing when compared to message.message;
# Define a message class that has all the arguments that will be passed in the request body.
# Message class is defined in models.py and imported here.
# Visit models.py
NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1),)
DELETE_GAME_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
ALL_MOVES_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))
RANK_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),)
NUMBER_OF_HIGH_SCORES_SCORECARDS = endpoints.ResourceContainer(
    number_of_high_scores=messages.IntegerField(1),)
NUMBER_OF_HIGH_SCORES_USERS = endpoints.ResourceContainer(
    number_of_high_scores=messages.IntegerField(1),)

MEMCACHE_MOVES_REMAINING = 'MOVES_REMAINING'

# Database for the quiz.
Questions = ['How many states are there in USA?',
             'What is the first name of current president of America?',
             'Who won football world cup of 2014? ',
             'In which year did first world war start?',
             'What is the currency of Bangladesh?',
             'What is the capital of England?',
             'Bangkok is the capital of which country?',
             'What is the number of days in a leap year?',
             'Which is the largest planet in our solar system?']
Answers = ['50', 'barack', 'germany', '1911',
           'taka', 'london', 'thailand', '366', 'jupiter']

# the name of the endpoint cannot contain upper case letters.


@endpoints.api(name='quizz', version='v1')
class quizz(remote.Service):

    #************************create_user***************************************
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

        if not request.user_name:
            raise endpoints.NotFoundException(
                'Please input user_name field.')

        user = User(name=(request.user_name).lower(), email=(
            request.email).lower(), total_points=0, total_guesses=0)
        user.put()
        return StringMessage(message='User {} created!'.format(
            request.user_name))

    #************************new_game***************************************
    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game and assigns random questions."""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')

        # Below logic implements random question assignment for each game.
        random_number = random.randint(0, len(Questions) - 1)

        try:
            game = Game(parent=user.key).new_game(user.key, random_number)
        except ValueError:
            raise endpoints.BadRequestException('Maximum must be greater '
                                                'than minimum!')

        game.radom_number_assigned = random_number
        game.put()

        message_to_send = "Your question is : " + \
            Questions[random_number]+"  Please use make_move api to proceed."
        # Use a task queue to update the average attempts remaining.
        # This operation is not needed to complete the creation of a new game
        # so it is performed out of sequence.
        taskqueue.add(url='/tasks/cache_average_attempts')
        return game.to_form(message_to_send)

    #************************get_game***************************************
    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        # Real game object is returned using its key.
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            if game.game_over == False:
                return game.to_form('Time to make a move!')
            else:
                return game.to_form('Game already over!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    #************************cancel_game***************************************
    @endpoints.method(request_message=DELETE_GAME_REQUEST,
                      response_message=StringMessage,
                      path='game/cancel',
                      name='cancel_game',
                      http_method='POST')
    def cancel_game(self, request):
        """Cancels/deletes an unfinished game."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)

        # Game can be cancelled only if its still not completed.
        if game.game_over == False:
            game.key.delete()
            msg = "The game is cancelled."
        else:
            msg = "The game is already over. Cannot cancel now."

        return StringMessage(message=msg)

    #************************get_user_games***********************************
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='game/get_user_games/{user_name}',
                      name='get_user_gamess',
                      http_method='GET')
    def get_user_games(self, request):
        """Returns all ACTIVE games of the user."""
        cur_usr = User.query(User.name == request.user_name).get()

        return GameForms(
            items=[game.to_form('user game!')
                   for game in Game.query
                   (Game.user == cur_usr.key, Game.game_over == False)])

    #**********************make_move*****************************************
    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)

        if not request.guess:
            raise endpoints.NotFoundException(
                'Please input guess field.')

        if game.game_over:
            return game.to_form('Game already over!')

        game.attempts_remaining -= 1
        game.put()

        # This 'if' implies that the game is won.
        if (((str(request.guess)).lower()) ==
                (str(Answers[game.random_number_assigned])).lower()):

            game.end_game(True)

            # To store the move made.
            game.insert_move(move=str(request.guess), result='You win!')

            game.put()

            user = User.query(User.name == game.user.get().name).get()
            # Since game is won. Update both total_points and total_guesses.
            user.total_points = user.total_points+10
            user.total_guesses = user.total_guesses+5-game.attempts_remaining

            user.put()

            return game.to_form('You win!')
        else:
            if game.attempts_remaining >= 1:

                game.insert_move(
                    move=(str(request.guess)).lower(), result='Try Again!')
                game.put()

                return game.to_form('Try again!')

        if game.attempts_remaining < 1:
            game.end_game(False)  # No need to commit here.

            # Since the game was not won. Total_points is not updated.
            user = User.query(User.name == game.user.get().name).get()
            user.total_guesses = user.total_guesses+5-game.attempts_remaining

            user.put()

            return game.to_form('Attempts over. Game over!')

    #**********************get_game_history***********************************

    @endpoints.method(request_message=ALL_MOVES_REQUEST,
                      # response_message=AllMovesForm,
                      response_message=MoveForms,
                      path='game/get_game_history/{urlsafe_game_key}',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Returns all moves of a current game"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)

        # All moves are filtered by particular 'game'. Then sorted by their
        # datetime created.
        moves_of_game = Moves.query(
            Moves.game == game.key).order(Moves.time_created)

        return MoveForms(
            items=[individual_move.to_form()
                   for individual_move in moves_of_game])

    #************************get_user_rankings********************************
    @endpoints.method(request_message=RANK_REQUEST,
                      response_message=get_user_rankings_form,
                      path='game/get_user_rankings/{user_name}',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Returns the ranking of the current user."""

        # Stores all the Users in sequence of their ranking.
        ranks = []

        # Logic - Users are sorted based on their total points. If total points
        # clash, total_guesses is used.
        for user in\
                User.query().\
                order((-User.total_points)).order(User.total_guesses):
            ranks.append(user.name)

        rank = ranks.index(request.user_name) + 1

        user_object = User.query(User.name == request.user_name).get()

        return user_object.to_get_user_rankings_form(ranking=rank)

    #************************get_scores***************************************
    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all score cards."""
        return ScoreForms\
            (score_cards=[score.to_form()
                          for score in Score.query()])

    #************************get_high_scores**********************************
    @endpoints.method(request_message=NUMBER_OF_HIGH_SCORES_USERS,
                      response_message=get_high_scores_forms,
                      path='get_highscores',
                      name='get_high_scores',
                      http_method='GET')
    def get_high_scores(self, request):
        """Return high scoring users (users with cumulative 
          highest total points in descending order, tie broken by 
          lesser guesses.)"""
        if not request.number_of_high_scores:
            raise endpoints.NotFoundException(
                'Please specify the number of high scoring users!!')

        return get_high_scores_forms(high_scores=[
            user.to_get_high_scores_form()
            for user in
            User.query().
            order(-User.total_points).
            order(User.total_guesses).
            fetch(request.number_of_high_scores)])

    #************************get_user_scores**********************************
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='scores/user/{user_name}',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Returns all of an individual User's score cards"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')
        scores = Score.query(Score.user == user.key)
        return ScoreForms(score_cards=[score.to_form() for score in scores])

    #*********************get_average_attempts********************************
    @endpoints.method(response_message=StringMessage,
                      path='games/average_attempts',
                      name='get_average_attempts_remaining',
                      http_method='GET')
    def get_average_attempts(self, request):
        """Get the cached average moves remaining"""
        return StringMessage\
            (message=memcache.get(MEMCACHE_MOVES_REMAINING) or '')

    #***************************************************************
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
                         'The average moves remaining is {:.2f}'
                         .format(average))


api = endpoints.api_server([quizz])
