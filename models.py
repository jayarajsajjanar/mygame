"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Because these classes are also regular Python
classes they can include methods (such as 'to_form' and 'new_game')."""

import random
from datetime import date
from protorpc import messages   
from google.appengine.ext import ndb


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email =ndb.StringProperty()
    total_average_points=ndb.IntegerProperty(required=True)
    total_guesses=ndb.IntegerProperty(required=True)

    def to_form_toprankings(self):
        return TopRankingForm(name=self.name, email=self.email, total_average_points=self.total_average_points, total_guesses=self.total_guesses)


class Game(ndb.Model):
    """Game object"""
    #Matching is done using the database itself.(Q&A database). So no need of target.
    #target = ndb.IntegerProperty(required=True)
    attempts_allowed = ndb.IntegerProperty(required=True)
    attempts_remaining = ndb.IntegerProperty(required=True, default = 5)
    game_over = ndb.BooleanProperty(required=True, default=False)
    user = ndb.KeyProperty(required=True, kind='User')
    all_movess = ndb.StringProperty(repeated = True)
    random_number_assigned = ndb.IntegerProperty(required=True)


    @classmethod
    #classmethod is like static method(can call with class and instance as well) with 'cls' implicitly passed.
    def new_game(cls, user,attempts,random_number_assigned):
        """Creates and returns a new game"""
        game = Game(user=user,
                    attempts_allowed=attempts,
                    attempts_remaining=attempts,
                    game_over=False,
                    parent=user,
                    random_number_assigned=random_number_assigned)
        game.put()
        return game

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()#Has to be urlsafe...else unicode some error.
        form.user_name = self.user.get().name
        form.attempts_remaining = self.attempts_remaining
        form.game_over = self.game_over
        form.message = message
        return form

    def to_all_moves_form(self):
        """Returns a AllMovesForm to display all moves of a game"""
        form = AllMovesForm()
        form.all_movess = self.all_movess
        return form

    def end_game(self, won=False):
        """Ends the game - if won is True, the player won. - if won is False,
        the player lost."""
        self.game_over = True
        self.put()
        # Add the game to the score 'board'
        score = Score(user=self.user, date=date.today(), won=won,
                      guesses=self.attempts_allowed - self.attempts_remaining)
        score.put()

    def delete_game(self):
        """Ends the game - if won is True, the player won. - if won is False,
        the player lost."""
        self.delete()


class Score(ndb.Model):
    """Score object"""
    user = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateProperty(required=True)
    won = ndb.BooleanProperty(required=True)
    guesses = ndb.IntegerProperty(required=True)

    def to_form(self):
        return ScoreForm(user_name=self.user.get().name, won=self.won,
                         date=str(self.date), guesses=self.guesses)

    def to_highscore_form(self):
        if self.won:
            game_score=12-2*self.guesses
        else: 
            game_score=0
        return HighScoreForm(game_score=game_score,user_name=self.user.get().name, won=self.won,
                         date=str(self.date), guesses=self.guesses)
    
    def cal_toprankings(self):
        if self.won == True:
            game_score=12-2*self.guesses
            self.user.get().total_guesses=self.user.get().total_guesses+self.guesses
            self.user.get().total_average_points=(self.user.get().total_average_points+game_score)/self.user.get().total_guesses
            self.user.get().put()

    def to_form_toprankings(self):
        return TopRankingForm(name=self.user.get().name, email=self.user.get().email, total_average_points=self.user.get().total_average_points, total_guesses=self.user.get().total_guesses)




class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    attempts_remaining = messages.IntegerField(2, required=True, default = 5)
    game_over = messages.BooleanField(3, required=True)
    message = messages.StringField(4, required=True)
    user_name = messages.StringField(5, required=True)

class GameForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(GameForm, 1, repeated=True)

class NewGameForm(messages.Message):
    """Used to create a new game"""
    user_name = messages.StringField(1, required=True)
    attempts = messages.IntegerField(4, default = 5)


class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    guess = messages.StringField(1, required=True)

class AllMovesForm(messages.Message):
    """Used to display all moves of an existing game"""
    all_movess = messages.StringField(1,repeated=True)


class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    user_name = messages.StringField(1, required=True)
    date = messages.StringField(2, required=True)
    won = messages.BooleanField(3, required=True)
    guesses = messages.IntegerField(4, required=True)

class TopRankingForm(messages.Message):
    """TopRankingForm for outbound top ranking information"""
    name = messages.StringField(1, required=True)
    email = messages.StringField(2, required=True)
    total_average_points = messages.IntegerField(3, required=True, default=0)
    total_guesses = messages.IntegerField(4, required=True, default=0)

class TopRankingForms(messages.Message):
    """Return multiple ScoreForms"""
    toprankings = messages.MessageField(TopRankingForm, 1, repeated=True)

class HighScoreForm(messages.Message):
    """ScoreForm for outbound high Score information"""
    game_score=messages.IntegerField(1, required=True)
    user_name = messages.StringField(2, required=True)
    date = messages.StringField(3, required=True)
    won = messages.BooleanField(4, required=True)
    guesses = messages.IntegerField(5, required=True)



class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)

class HighScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    high_scores = messages.MessageField(HighScoreForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
