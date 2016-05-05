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
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
ALL_MOVES_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))
NUMBER_OF_HIGH_SCORES = endpoints.ResourceContainer(number_of_high_scores=messages.IntegerField(1),)

MEMCACHE_MOVES_REMAINING = 'MOVES_REMAINING'


Questions = ['Guess my age', 'Q2', 'Q3']
Answers = ['23','jayaraj2','jayaraj3']

@endpoints.api(name='guess_a_number', version='v1')
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
        user = User(name=request.user_name, email=request.email,total_points=0, total_guesses=0)
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
        """Creates new game"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        try:
            game = Game(parent = user.key).new_game(user.key, request.min,
                                 request.max, request.attempts)
        except ValueError:
            raise endpoints.BadRequestException('Maximum must be greater '
                                                'than minimum!')
        random_number = random.choice(range(0, len(Questions)-1))
        game.radom_number_assigned=random_number
        message_to_send="Your question is : "+Questions[random_number]+"Please use make_move api to proceed."
        # Use a task queue to update the average attempts remaining.
        # This operation is not needed to complete the creation of a new game
        # so it is performed out of sequence.
        taskqueue.add(url='/tasks/cache_average_attempts')
        return game.to_form(message_to_send)
        # return game.to_form('Good luck playing Guess a Number!')


    #************************get_game***************************************
    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_form('Time to make a move!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    #************************delete_game***************************************
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='game/delete/{user_name}',
                      name='delete_game',
                      http_method='GET')
    def delete_game(self, request):
        """Deletes a game."""
        # all_games = ndb.query_descendants(request.user_name.get())
        # g=ndb.query(Game).all()
        # g.ancestor(request.user_name.get())

        # # game = get_by_urlsafe(request.urlsafe_game_key, Game)
        # # if all_games:
        # mess=''
        # # for games in Game.all():
        # ndb.query
        # # for games in ndb.query(Game).all():
        #   mess=mess+games.user
        # # else:
        # #     raise endpoints.NotFoundException('Game not found!')
        # # temp = Game()
        # return temp.to_form('deleted')
        #ahBkZXZ-Z2FtZWFwaS0xMjUzciILEgRVc2VyGICAgICAgIAKDAsSBEdhbWUYgICAgICAgAsM
        #ahBkZXZ-Z2FtZWFwaS0xMjUzciILEgRVc2VyGICAgICAgIAKDAsSBEdhbWUYgICAgICAwAoM
        # jayaraj9 - ahBkZXZ-Z2FtZWFwaS0xMjUzciILEgRVc2VyGICAgICAgMALDAsSBEdhbWUYgICAgICAoAgM
        #jayaraj10 - ahBkZXZ-Z2FtZWFwaS0xMjUzciILEgRVc2VyGICAgICAgKAKDAsSBEdhbWUYgICAgICAoAkM
        #ahBkZXZ-Z2FtZWFwaS0xMjUzciILEgRVc2VyGICAgICAgKAKDAsSBEdhbWUYgICAgICA4AgM
        #ahBkZXZ-Z2FtZWFwaS0xMjUzciILEgRVc2VyGICAgICAgKAKDAsSBEdhbWUYgICAgICA4AkM
        #ahBkZXZ-Z2FtZWFwaS0xMjUzciILEgRVc2VyGICAgICAgKAKDAsSBEdhbWUYgICAgICA4AsM
        #jayaraj11- ahBkZXZ-Z2FtZWFwaS0xMjUzciILEgRVc2VyGICAgICAgJAKDAsSBEdhbWUYgICAgICAkAsM
        #ahBkZXZ-Z2FtZWFwaS0xMjUzciILEgRVc2VyGICAgICAgJAKDAsSBEdhbWUYgICAgICA0AgM
        #######User is : #######
        cur_usr = User.query(User.name == request.user_name).get()
        game_cur_usr=[]
        game_cur_usr_2=[]
        j=0
        for i in Score.query(Score.user == cur_usr.key):
        #k=i.get()
          if i:
            i.key.delete()

        for i in Game.query(Game.user == cur_usr.key):
          if i:
            i.key.delete()

        #for i in Game.query(Game.user == cur_usr.key):
          #i.delete()
          #game_cur_usr.append(i)
          #game_cur_usr_2.append(game_cur_usr[j].get())
          #j=j+1
        return StringMessage(message='Games and scores deleted')
        #return StringMessage(message='user is  : {}'.format(game_cur_usr.name))
        #return game_cur_usr[0].to_form("gsme returned is this!")        

#************************user_games***************************************
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='game/user_games/{user_name}',
                      name='user_games',
                      http_method='GET')
    def user_games(self, request):
        """returns user games."""
        # all_games = ndb.query_descendants(request.user_name.get())
        # g=ndb.query(Game).all()
        # g.ancestor(request.user_name.get())

        # # game = get_by_urlsafe(request.urlsafe_game_key, Game)
        # # if all_games:
        # mess=''
        # # for games in Game.all():
        # ndb.query
        # # for games in ndb.query(Game).all():
        #   mess=mess+games.user
        # # else:
        # #     raise endpoints.NotFoundException('Game not found!')
        # # temp = Game()
        # return temp.to_form('deleted')
        #jayaraj12 - ahBkZXZ-Z2FtZWFwaS0xMjUzciILEgRVc2VyGICAgICAgNAKDAsSBEdhbWUYgICAgICA0AkM
        #ahBkZXZ-Z2FtZWFwaS0xMjUzciILEgRVc2VyGICAgICAgNAKDAsSBEdhbWUYgICAgICAsAgM
        #######User is : #######
        cur_usr = User.query(User.name == request.user_name).get()
        game_cur_usr=[]
        game_cur_usr_2=[]
        j=0
        # for i in Game.query(Game.user == cur_usr.key):
        # #k=i.get()
        #   if i:
        #     i.key.delete()
        #for i in Game.query(Game.user == cur_usr.key):
          #i.delete()
          #game_cur_usr.append(i)
          #game_cur_usr_2.append(game_cur_usr[j].get())
          #j=j+1
        return GameForms(items=[game.to_form('user games!') for game in Game.query(Game.user == cur_usr.key)])
        ######return StringMessage(message='deleted')
        #return StringMessage(message='user is  : {}'.format(game_cur_usr.name))
        #return game_cur_usr[0].to_form("gsme returned is this!")        


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
        if request.guess == Answers[game.radom_number_assigned]:
            game.end_game(True)
            return game.to_form('You win!')

        if request.guess < Answers[game.radom_number_assigned]:
            msg = 'Too low!'
        else:
            msg = 'Too high!'

        if game.attempts_remaining < 1:
            game.end_game(False)
            return game.to_form(msg + ' Game over!')
        else:
            game.put()
            return game.to_form(msg)

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
    @endpoints.method(response_message=TopRankingForms,
                      path='toprankings',
                      name='get_top_rankings',
                      http_method='GET')
    def get_top_rankings(self, request):
        """Return all top rankings"""

        for score in Score.query():
          score.cal_toprankings()

        return TopRankingForms(toprankings=[user.to_form_toprankings() for user in User.query().order((User.total_points))])


    #************************get_scores***************************************
    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

    #************************get_high_scores***************************************
    @endpoints.method(request_message=NUMBER_OF_HIGH_SCORES,
                      response_message=HighScoreForms,
                      path='highscores',
                      name='get_high_scores',
                      http_method='GET')
    def get_high_scores(self, request):
        """Return high scores"""
        #user = User.query(User.name == request.user_name).get()
        if not request.number_of_high_scores:
            raise endpoints.NotFoundException(
                    'Please specify the number of high scores!!')
        
        # temp_least_num=5
        # for score in Score.query():
        #   if score.guesses<temp_least_num:
        #     temp_least_num=score.guesses

        # for score in Score.query():
        #   high_scores=score.to_highscore_form()


        # return HighScoreForms()
        return HighScoreForms(high_scores=[score.to_highscore_form() for score in Score.query().order(Score.guesses).fetch(request.number_of_high_scores)])

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