from __future__ import unicode_literals
from django.contrib.auth.models import User
from django.db import models
from channels import Group
import json
import datetime
from datetime import timedelta
from django.db.models import *
from django.shortcuts import redirect
from django.http import HttpResponse, HttpResponseNotFound, Http404,  HttpResponseRedirect

class Game(models.Model):
    winner = models.ForeignKey(
        User, related_name='winner', null=True, blank=True, on_delete=models.DO_NOTHING)
    creator = models.ForeignKey(User, related_name='creator', on_delete=models.DO_NOTHING)
    opponent = models.ForeignKey(
        User, related_name='opponent', null=True, blank=True, on_delete=models.DO_NOTHING)
    cols = models.IntegerField(default=9)
    rows = models.IntegerField(default=9)
    score = models.IntegerField(null=True, blank=True)
    current_turn = models.ForeignKey(User, related_name='current_turn', on_delete=models.DO_NOTHING)
    pass_chance = models.ForeignKey(User, related_name='pass_chance',null=True, blank=True, on_delete=models.DO_NOTHING)

    # dates
    completed = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return 'Game #{0}'.format(self.pk)

    @staticmethod
    def get_available_games():
        return Game.objects.filter(opponent=None, completed=None)

    @staticmethod
    def get_past_games(user):
        from django.db.models import Q
        return Game.objects.filter(~Q(completed=None) & Q(opponent=user) | Q(creator=user))

    @staticmethod
    def created_count(user):
        return Game.objects.filter(creator=user).count()

    @staticmethod
    def get_games_for_player(user):
        from django.db.models import Q
        return Game.objects.filter(Q(opponent=user) | Q(creator=user))

    @staticmethod
    def get_by_id(id):
        try:
            return Game.objects.get(pk=id)
        except Game.DoesNotExist:
            # TODO: Handle this Exception
            pass

    @staticmethod
    def create_new(user):
        """
        Create a new game and game squares
        :param user: the user that created the game
        :return: a new game object
        """
        # make the game's name from the username and the number of
        # games they've created
        new_game = Game(creator=user, current_turn=user)
        new_game.save()
        # for each row, create the proper number of cells based on rows
        for row in range(new_game.rows):
            for col in range(new_game.cols):
                new_square = GameSquare(
                    game=new_game,
                    row=row,
                    col=col
                )
                new_square.save()
        # put first log into the GameLog
        new_game.add_log('Game created by {0}'.format(new_game.creator.username))

        return new_game

    def add_log(self, text, user=None):
        """
        Adds a text log associated with this game.
        """

        entry = GameLog(game=self, text=text, player=user).save()
        return entry

    def get_all_game_squares(self):
        """
        Gets all of the squares for this Game
        """
        return GameSquare.objects.filter(game=self).order_by('id')

    def get_game_square(row, col):
        """
        Gets a square for a game by it's row and col pos
        """
        try:
            return GameSquare.objects.get(game=self, cols=col, rows=row)
        except GameSquare.DoesNotExist:
            return None

    def get_square_by_coords(self, coords):
        """
        Retrieves the cell based on it's (x,y) or (row, col)
        """
        try:
            square = GameSquare.objects.get(row=coords[1],
                                            col=coords[0],
                                            game=self)
            return square
        except GameSquare.DoesNotExist:
            # TODO: Handle exception for gamesquare
            return None

    def get_game_log(self):
        """
        Gets the entire log for the game
        """
        return GameLog.objects.filter(game=self)

    def send_game_update(self):
        """
        Send the updated game information and squares to the game's channel group
        """
        # imported here to avoid circular import
        from .serializers import GameSquareSerializer, GameLogSerializer, GameSerializer

        squares = self.get_all_game_squares()
        square_serializer = GameSquareSerializer(squares, many=True)

        # get game log
        log = self.get_game_log()
        log_serializer = GameLogSerializer(log, many=True)

        game_serilizer = GameSerializer(self)

        message = {'game': game_serilizer.data,
                   'log': log_serializer.data,
                   'squares': square_serializer.data}

        game_group = 'game-{0}'.format(self.id)
        Group(game_group).send({'text': json.dumps(message)})

    def next_player_turn(self):
        """
        Sets the next player's turn
        """
        self.current_turn = self.creator if self.current_turn != self.creator else self.opponent
        self.save()

    def mark_complete(self, winner):
        """
        Sets a game to completed status and records the winner
        """
        self.winner = winner
        self.score = self.get_all_game_squares().filter(owner=winner).count()
        self.completed = datetime.datetime.now()
        self.save()
        self.send_game_update()

    def passChance(self, user):
        """
        Claims the square for the user
        """
        if(self.pass_chance == None or self.pass_chance.id == user.id):
            self.pass_chance = user
            self.save(update_fields=['pass_chance'])
            self.add_log('{0} has passed his turn'.format(user.username))
            self.next_player_turn()
            self.send_game_update()
        elif(self.pass_chance != None and self.pass_chance.id != user.id):
            creator_count = self.get_all_game_squares().filter(owner=self.creator).count()
            opponent_count = self.get_all_game_squares().filter(owner=self.opponent).count()
            if(creator_count>opponent_count):
                self.winner = self.creator
                self.score = creator_count
            else:
                self.winner = self.opponent
                self.score = opponent_count
            self.completed = datetime.datetime.now()
            self.save()
            self.add_log('{0} has won the game'.format(self.winner))
            self.send_game_update()

class GameSquare(models.Model):
    STATUS_TYPES = (
        ('Free', 'Free'),
        ('Selected', 'Selected'),
        ('Surrounding', 'Surrounding')
    )
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    owner = models.ForeignKey(User, null=True, blank=True, on_delete=models.DO_NOTHING)
    status = models.CharField(choices=STATUS_TYPES,
                              max_length=25,
                              default='Free')
    row = models.IntegerField()
    col = models.IntegerField()

    # dates
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '{0} - ({1}, {2})'.format(self.game, self.col, self.row)

    @staticmethod
    def get_by_id(id):
        try:
            return GameSquare.objects.get(pk=id)
        except GameSquare.DoesNotExist:
            # TODO: Handle exception for gamesquare
            return None

    def get_surrounding(self):
        """
        Returns this square's surrounding neighbors that are still Free
        """
        # TODO:
        # http://stackoverflow.com/questions/2373306/pythonic-and-efficient-way-of-finding-adjacent-cells-in-grid
        results = []
        
        if self.row==3 and self.col==5:
            gamesq = GameSquare.objects.get(game=self.game, row=4, col=5)
            gamesq.status = 'Free'
            gamesq.owner = None
            gamesq.save(update_fields=['status', 'owner'])
            self.game.add_log('Square at ({0}, {1}) is captured by {2}'
                          .format(gamesq.col, gamesq.row, self.owner.username))

        return results


    def claim(self, status_type, user):
        """
        Claims the square for the user
        """

        log = GameLog.objects.filter(game=self.game).aggregate(Max('id'))
        print(log)
        if(log['id__max'] != None):
            log2 = GameLog.objects.get(id=log['id__max'])

            datetimeFormat = '%Y-%m-%d %H:%M:%S.%f'
            date1 = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            date2 = log2.created.strftime('%Y-%m-%d %H:%M:%S.%f')
            diff = datetime.datetime.strptime(date1, datetimeFormat) - datetime.datetime.strptime(date2, datetimeFormat)
 
            print("Seconds:", diff.seconds)

            if(diff.seconds>180):
                print("inside the loop ")
                self.game.current_turn = self.game.creator if self.game.current_turn != self.game.creator else self.game.opponent
                self.game.add_log('Game was forfeited because of session timeout. {0} has won the game'.format(self.game.current_turn))
                self.game.send_game_update()
                self.game.mark_complete(self.game.current_turn)
                return

        self.owner = user
        self.status = status_type
        self.save(update_fields=['status', 'owner'])

        # get surrounding squares and update them if they can be updated
        surrounding = self.get_surrounding()


        # add log entry for move
        self.game.add_log('Square claimed at ({0}, {1}) by {2}'
                          .format(self.col, self.row, self.owner.username))

        # set the current turn for the other player if there are still free
        # squares to claim
        if self.game.get_all_game_squares().filter(status='Free'):
            self.game.next_player_turn()
        else:
            self.game.mark_complete(winner=user)
        # let the game know about the move and results
        self.game.send_game_update()


class GameLog(models.Model):
    game = models.ForeignKey(Game, on_delete=models.DO_NOTHING)
    text = models.CharField(max_length=300)
    player = models.ForeignKey(User, null=True, blank=True, on_delete=models.DO_NOTHING)

    created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return 'Game #{0} Log'.format(self.game.id)


