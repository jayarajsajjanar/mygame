"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Major models are User,Game and Score. Functions are defined to operate on these models."""

import random
from datetime import date
import datetime
from protorpc import messages
from google.appengine.ext import ndb

#*********************User Model*********************


class User(ndb.Model):

    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()
    # The below are used in leaderboard/rankings.
    total_points = ndb.IntegerProperty(required=True)
    total_guesses = ndb.IntegerProperty(required=True)

    def to_get_user_rankings_form(self, ranking):
        """Used to return user ranking"""
        form = get_user_rankings_form()
        form.name = self.name
        form.ranking = ranking
        form.total_points = self.total_points
        return form

    def to_get_high_scores_form(self):
        """Used to return high score information"""
        form = get_high_scores_form()
        form.name = self.name
        form.total_points = self.total_points
        form.total_guesses = self.total_guesses
        return form


class get_user_rankings_form(messages.Message):

    """Used to return user ranking"""
    name = messages.StringField(1, required=True)
    ranking = messages.IntegerField(2, required=True)
    total_points = messages.IntegerField(3, required=True)


class get_high_scores_form(messages.Message):

    """Used to return high score information"""
    name = messages.StringField(1, required=True)
    total_points = messages.IntegerField(2, required=True)
    total_guesses = messages.IntegerField(3, required=True)


class get_high_scores_forms(messages.Message):

    """Used to return high score information"""
    high_scores = messages.MessageField(get_high_scores_form, 1, repeated=True)

#*********************Moves Model*********************


class Moves(ndb.Model):

    """User profile"""
    move = ndb.StringProperty(required=True)
    result = ndb.StringProperty(required=True)
    game = ndb.KeyProperty(required=True, kind='Game')
    time_created = ndb.DateTimeProperty(required=True)
    # user = ndb.KeyProperty(required=True, kind='User')

    def to_form(self):
        """Returns a MoveForm representation of the Move"""
        form = MoveForm()
        form.move = self.move
        form.result = self.result
        return form


class MoveForm(messages.Message):

    """MoveForm for outbound move state information"""
    move = messages.StringField(1, required=True)
    result = messages.StringField(2, required=True)


class MoveForms(messages.Message):

    """Return multiple MoveForms"""
    items = messages.MessageField(MoveForm, 1, repeated=True)

#*********************Game Model*********************


class Game(ndb.Model):

    """Game object"""
    # Matching is done using the database itself.(Q&A database). So no need of target.
    #target = ndb.IntegerProperty(required=True)
    attempts_allowed = ndb.IntegerProperty(required=True)
    attempts_remaining = ndb.IntegerProperty(required=True, default=5)
    game_over = ndb.BooleanProperty(required=True, default=False)
    user = ndb.KeyProperty(required=True, kind='User')
    random_number_assigned = ndb.IntegerProperty(required=True)

    @classmethod
    # classmethod is like static method(can call with class and instance as
    # well) with 'cls' implicitly passed.
    def new_game(cls, user, random_number_assigned):
        """Creates and returns a new game"""
        # moves = []
        game = Game(user=user,
                    attempts_allowed=5,
                    attempts_remaining=5,
                    game_over=False,
                    parent=user,
                    random_number_assigned=random_number_assigned)
        game.put()
        return game

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        # Has to be urlsafe...else unicode some error.
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.user.get().name
        form.attempts_remaining = self.attempts_remaining
        form.game_over = self.game_over
        form.message = message
        return form

    # def to_all_moves_form(self):
    #     """Returns a AllMovesForm to display all moves of a game"""
    #     form = AllMovesForm()
    #     form.all_movess = self.all_movess
    #     form.results=self.results
    #     return form

    def end_game(self, won=False):
        """Ends the game - if won is True, the player won. - if won is False,
        the player lost."""
        self.game_over = True
        self.put()
        # Add the game to the score 'board' and since
        if won == True:
            score = Score(user=self.user, date=date.today(), won=won,
                          guesses=self.attempts_allowed -
                          self.attempts_remaining,
                          score_gained=10)
        else:
            score = Score(user=self.user, date=date.today(), won=won,
                          guesses=self.attempts_allowed -
                          self.attempts_remaining,
                          score_gained=0)
        score.put()

    def insert_move(self, move, result):
        """inserts move"""
        moves = Moves(
            game=self.key, move=move, result=result,
            time_created=datetime.datetime.now())
        moves.put()

    def delete_game(self):
        """Deletes the game."""
        self.delete()


class GameForm(messages.Message):

    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    attempts_remaining = messages.IntegerField(2, required=True, default=5)
    game_over = messages.BooleanField(3, required=True)
    message = messages.StringField(4, required=True)
    user_name = messages.StringField(5, required=True)


class GameForms(messages.Message):

    """Return multiple ScoreForms"""
    items = messages.MessageField(GameForm, 1, repeated=True)


class NewGameForm(messages.Message):

    """Used to create a new game"""
    user_name = messages.StringField(1, required=True)
    # attempts = messages.IntegerField(4, default = 5)


#*********************Score Model*********************

class Score(ndb.Model):

    """Score object"""
    user = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateProperty(required=True)
    won = ndb.BooleanProperty(required=True)
    guesses = ndb.IntegerProperty(required=True)
    score_gained = ndb.IntegerProperty(required=True)

    def to_form(self):
        return ScoreForm(user_name=self.user.get().name, won=self.won,
                         date=str(self.date),
                         guesses=self.guesses, score_gained=self.score_gained)

    def to_highscore_form(self):
        if self.won:
            game_score = 10
        else:
            game_score = 0
        return HighScoreForm(game_score=game_score,
                             user_name=self.user.get().name, won=self.won,
                             date=str(self.date),
                             guesses=self.guesses,
                             score_gained=self.score_gained)


class ScoreForm(messages.Message):

    """ScoreForm for outbound Score information"""
    user_name = messages.StringField(1, required=True)
    date = messages.StringField(2, required=True)
    won = messages.BooleanField(3, required=True)
    guesses = messages.IntegerField(4, required=True)
    score_gained = messages.IntegerField(5, required=True)


class ScoreForms(messages.Message):

    """Return multiple ScoreForms"""
    score_cards = messages.MessageField(ScoreForm, 1, repeated=True)


class HighScoreForm(messages.Message):

    """ScoreForm for outbound high Score information"""
    game_score = messages.IntegerField(1, required=True)
    user_name = messages.StringField(2, required=True)
    date = messages.StringField(3, required=True)
    won = messages.BooleanField(4, required=True)
    guesses = messages.IntegerField(5, required=True)
    score_gained = messages.IntegerField(6, required=True)


class HighScoreForms(messages.Message):

    """Return multiple HighScoreForm forms"""
    high_scores = messages.MessageField(HighScoreForm, 1, repeated=True)

#******************************************************


class MakeMoveForm(messages.Message):

    """Used to make a move in an existing game"""
    guess = messages.StringField(1, required=True)


class StringMessage(messages.Message):

    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
