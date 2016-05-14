#Full Stack Nanodegree Project 4 - quizz

## Set-Up Instructions:
1.  Update the value of application in app.yaml to the app ID you have registered
 in the App Engine admin console and would like to use to host your instance of this sample.
1.  Run the app with the devserver using dev_appserver.py DIR, and ensure it's
 running by visiting the API Explorer - by default localhost:8080/_ah/api/explorer. 
 
 
##Game Description:
`quizz` is a single player quiz game where random general knowledge questions from a database are asked to the player. Maximum of 5 attempts are allowed for the player to guess the correct answer. If the player guesses correctly, 10 points are assigned. If all the 5 attempts are consumed, game is ended and 0 points are awarded. 

A user can have multiple games active at the same time. The games can be retrieved or played by using the path parameter
`urlsafe_game_key`.

##Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.

##Endpoints Included:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional)
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will 
    raise a ConflictException if a User with that user_name already exists.
    
 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: user_name, min, max, attempts
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. user_name provided must correspond to an
    existing user - will raise a NotFoundException if not. Min must be less than
    max. Also adds a task to a task queue to update the average moves remaining
    for active games.
     
 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game.

- **cancel_game**
    - Path: 'game/cancel'
    - Method: POST
    - Parameters: urlsafe_game_key
    - Returns: StringMessage.
    - Description: Cancels/Deletes a currently unfinished game.

- **user_games**
    - Path: 'game/user_games/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: GameForms.
    - Description: Returns all games played by the user.
    
- **make_move**
    - Path: 'game/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key, guess
    - Returns: GameForm with new game state.
    - Description: Accepts a 'guess' and returns the updated state of the game.
    If this causes a game to end, a corresponding Score entity will be created.

- **all_moves**
    - Path: 'game/all_moves/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: AllMovesForm.
    - Description: Returns all moves made by user in the current game.

- **ranking_of_user**
    - Path: 'game/ranking_of_user'
    - Method: GET
    - Parameters: user_name
    - Returns: StringMessage
    - Description: Returns the ranking of the current user.

- **high_scores_users**
    - Path: 'highscores_users'
    - Method: GET
    - Parameters: number of high scores 
    - Returns: StringMessage
    - Description: Return high scoring users (users with cumulative highest total points in descending order, tie broken by lesser guesses.)
    
- **get_user_scores**
    - Path: 'scores/user/{user_name}''
    - Method: GET
    - Parameters: user_name
    - Returns: ScoreForms
    - Description: Returns all of an individual User's score cards

- **get_scores**
    - Path: 'scores'
    - Method: GET
    - Parameters: None
    - Returns: ScoreForms.
    - Description: Returns all Scores cards in the database (unordered).
    
- **get_user_scores**
    - Path: 'scores/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: ScoreForms. 
    - Description: Returns all Scores recorded by the provided player (unordered).
    Will raise a NotFoundException if the User does not exist.
    
- **get_average_attempts**
    - Path: 'games/average_attempts'
    - Method: GET
    - Parameters: None
    - Returns: StringMessage
    - Description: Gets the average number of attempts remaining for all games
    from a previously cached memcache key.

##Models Included:
 - **User**
    - Stores unique user_name and (optional) email address.
    - total_points and total_guesses are used while querying leader board.
    
 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.
    
 - **Score**
    - Records completed games. Associated with Users model via KeyProperty.
    
##Forms Included:
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, attempts_remaining,
    game_over flag, message, user_name).
 - **GameForms**
    - Multiple GameForm container. 
 - **NewGameForm**
    - Used to create a new game (user_name, attempts)
 - **MakeMoveForm**
    - Inbound make move form (guess).
 - **AllMovesForm**
    - Stores all moves made during a game.
 - **ScoreForm**
    - Representation of a completed game's Score (user_name, date, won flag,
    guesses, score_gained).
 - **ScoreForms**
    - Multiple ScoreForm container.
 - **HighScoreForm**
    - Acts as a container for outbound high score information.
 - **HighScoreForms**
    - Multiple HighScoreForm container.
 - **StringMessage**
    - General purpose String container.
