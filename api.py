"""api.py - Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users."""


import logging
import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from models import User, Game, Score
from models import StringMessage, NewGameForm, GameForm, MakeMoveForm,\
    ScoreForms, GameForms, HighScoreForms, TopRankingForms, AllMovesForm
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
NUMBER_OF_HIGH_SCORES_SCORECARDS = endpoints.ResourceContainer(number_of_high_scores=messages.IntegerField(1),)
NUMBER_OF_HIGH_SCORES_USERS = endpoints.ResourceContainer(number_of_high_scores=messages.IntegerField(1),)

MEMCACHE_MOVES_REMAINING = 'MOVES_REMAINING'


Questions = ['How many states are there in USA?', 'What is the first name of current president of America?', 
              'Who won football world cup of 2014? ', 'In which year did first world war start?',
              'What is the currency of Bangladesh?', 'What is the capital of England?',
              'Bangkok is the capital of which country?', 'What is the number of days in a leap year?']
Answers = ['50','barack','germany','1911','taka','london','thailand','365']

@endpoints.api(name='Quizzzz!', version='v1')
class GuessANumberApi(remote.Service):

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
        user = User(name=request.user_name, email=request.email,total_average_points=0, total_guesses=0)
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

        random_number = random.randint(0, len(Questions) - 1)

        try:
            game = Game(parent = user.key).new_game(user.key,request.attempts,random_number)
        except ValueError:
            raise endpoints.BadRequestException('Maximum must be greater '
                                                'than minimum!')
        
        game.radom_number_assigned=random_number
        game.put()
        
        message_to_send="Your question is : "+Questions[random_number]+"  Please use make_move api to proceed."
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
        #Real game object is returned using key.
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_form('Time to make a move!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    #************************delete_game***************************************
    @endpoints.method(request_message=DELETE_GAME_REQUEST,
                      response_message=StringMessage,
                      path='game/delete',
                      name='delete_game',
                      http_method='POST')
    def delete_game(self, request):
        """Deletes a game."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)

        if game.game_over == False:
          game.key.delete()
          msg="The game is cancelled."
        else:
          msg="The game is already over. Cannot cancel now."


        return StringMessage(message=msg)
        
    #************************user_games***************************************
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='game/user_games/{user_name}',
                      name='user_games',
                      http_method='GET')
    def user_games(self, request):
        """returns user games."""
        cur_usr = User.query(User.name == request.user_name).get()
        
        return GameForms(items=[game.to_form('user games!') for game in Game.query(Game.user == cur_usr.key)])

    #**********************make_move*****************************************
    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)

        if game.game_over:
            return game.to_form('Game already over!')
        
        game.all_movess.append(str(request.guess))

        game.attempts_remaining -= 1
        game.put()

        if str(request.guess) == str(Answers[game.random_number_assigned]):
            game.end_game(True)
            game.put()
            #Below is done because of design constraints.
            for score in Score.query():
              score.cal_toprankings()

            return game.to_form('You win!')
        else:
          if game.attempts_remaining >= 1:
            return game.to_form('Try again!')

        if game.attempts_remaining < 1:
            game.end_game(False)
            return game.to_form( 'Attempts over. Game over!')
        
    #**********************all_moves*****************************************

    @endpoints.method(request_message=ALL_MOVES_REQUEST,
                      response_message=AllMovesForm,
                      path='game/all_moves/{urlsafe_game_key}',
                      name='all_moves',
                      http_method='GET')
    def all_moves(self, request):
        """Returns all moves of a current game"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)

        return game.to_all_moves_form()


    #************************get_top_rankings***************************************
    @endpoints.method(request_message=RANK_REQUEST,
                      response_message=StringMessage,
                      path='toprankings',
                      name='get_top_rankings',
                      http_method='GET')
    def get_top_rankings(self, request):
        """Return all top rankings"""

        for score in Score.query():
          score.cal_toprankings()

        ranks = []

        for user in User.query().order((-User.total_average_points)):
          ranks.append(user.name)

        rank = ranks.index(request.user_name) + 1



        return StringMessage(message='Rank is {}'.format(rank))

    #************************get_scores***************************************
    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

    #************************get_high_scores_scorecards***************************************
    @endpoints.method(request_message=NUMBER_OF_HIGH_SCORES_SCORECARDS,
                      response_message=HighScoreForms,
                      path='highscores_scorecards',
                      name='get_high_scores_scorecards',
                      http_method='GET')
    def get_high_scores_scorecards(self, request):
        """Return high scores (scorecards with highest scores in descending order)"""
        if not request.number_of_high_scores:
            raise endpoints.NotFoundException(
                    'Please specify the number of high scores!!')
  
        return HighScoreForms(high_scores=[score.to_highscore_form() for score in Score.query().order(Score.guesses).fetch(request.number_of_high_scores)])


    #************************get_high_scores_users***************************************
    @endpoints.method(request_message=NUMBER_OF_HIGH_SCORES_USERS,
                      response_message=StringMessage,
                      path='highscores_users',
                      name='get_high_scores_users',
                      http_method='GET')
    def get_high_scores_users(self, request):
        """Return high scores (users with highest scores in descending order)"""
        if not request.number_of_high_scores:
            raise endpoints.NotFoundException(
                    'Please specify the number of high scores!!')
        topscores=[]

        for score in Score.query().order(Score.guesses).fetch(request.number_of_high_scores):
          topscores.append(score.user.get().name)

        return StringMessage(message='Leader board in descending order is  {}'.format(topscores))

    #************************get_user_scores***************************************
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
        scores = Score.query(Score.user == user.key)
        return ScoreForms(items=[score.to_form() for score in scores])


    #*********************get_average_attempts******************************************
    @endpoints.method(response_message=StringMessage,
                      path='games/average_attempts',
                      name='get_average_attempts_remaining',
                      http_method='GET')
    def get_average_attempts(self, request):
        """Get the cached average moves remaining"""
        return StringMessage(message=memcache.get(MEMCACHE_MOVES_REMAINING) or '')


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
                         'The average moves remaining is {:.2f}'.format(average))


api = endpoints.api_server([GuessANumberApi])