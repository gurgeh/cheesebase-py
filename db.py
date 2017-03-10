# coding: utf-8

import pickle
import os
import time
import resource

from collections import defaultdict, Counter, namedtuple

import dateutil.parser

import chess.pgn

import cpyext
cpyext.load_module('dbcorepp.so', 'dbcore')
import dbcore

Header = namedtuple('Header', ['WhiteElo', 'BlackElo', 'Result', 'Date'])

MAX_GAME_DEPTH = 50
RES2SCORE = {
    '1-0': 1,
    '0-1': -1,
    '1/2-1/2': 0,
}
"""
checka in kod
-
webgränssnitt
Forwarda port från Zurg, eller dra igång på Zurg
-
Beräkna en mjukare (bayesisk) funktion
-
en egen FrozenDB som laddar mer minnessnålt
plocka mer data från https://github.com/rozim/ChessData/tree/master/ChessNostalgia.com
"""


def predict(wins, losses, draws):
    pass


def make_move(gnode):
    if gnode.is_end():
        return 0, 0, 0
    p = gnode.move.promotion
    if p is None:
        p = 0
    else:
        p -= 2
    return gnode.move.from_square, gnode.move.to_square, p


def fenhash(fen):
    h = ' '.join(fen.split()[:3])
    return abs(hash(h))


def poshash(b):
    h = ' '.join(b.fen().split()[:3])
    return abs(hash(h))


def parse_header(h):
    if h.get('Result') not in RES2SCORE:
        print h.get('Result'), 'not a valid result'
    try:
        dt = dateutil.parser.parse(h.get('Date'))
    except:
        print(h.get('Date'), 'is not a valid date')
        dt = dateutil.parser.parse('1970-01-01')
    return Header(
        WhiteElo=int(h.get('WhiteElo', 0)),
        BlackElo=int(h.get('BlackElo', 0)),
        Date=dt,
        Result=RES2SCORE.get(h.get('Result'), 0))


def check_elo(e):
    return 2000 < e < 2900


class DB:
    def __init__(self, fname=None):
        self.headers = []
        self.gdb = dbcore.GraphDB()

        self.wweight = dbcore.ScoreDB()
        #self.wwrep = dbcore.ScoreDB()

        self.bweight = dbcore.ScoreDB()
        #self.bwrep = dbcore.ScoreDB()

        self.minmax = dbcore.ScoreDB()
        #self.mmrep = dbcore.ScoreDB()

        if fname:
            self.load(fname)

    def load(self, fname):
        with open(fname + '-head.p', 'rb') as inf:
            self.headers = pickle.load(inf)

        self.gdb.load(fname + '.dat')

    def save(self, fname):
        self.gdb.save(fname + '.dat')
        with open(fname + '-head.p', 'wb') as outf:
            pickle.dump(self.headers, outf, -1)

    def save_scores(self, fname):
        self.wweight.save(fname + '-ww.dat')
        self.bweight.save(fname + '-bw.dat')
        self.minmax.save(fname + '-mm.dat')

        #self.wwrep.save(fname + '-wwr.dat')
        #self.bwrep.save(fname + '-bwr.dat')
        #self.mmrep.save(fname + '-mmr.dat')

    def load_scores(self, fname):
        self.wweight.load(fname + '-ww.dat')
        self.bweight.load(fname + '-bw.dat')
        self.minmax.load(fname + '-mm.dat')

        #self.wwrep.load(fname + '-wwr.dat')
        #self.bwrep.load(fname + '-bwr.dat')
        #self.mmrep.load(fname + '-mmr.dat')

    def average(self, idxs, key):
        return sum(getattr(self.headers[i], key)
                   for i in idxs) / float(len(idxs))

    def draws(self, idxs):
        return sum(1 for i in idxs
                   if self.headers[i].Result == 0) / float(len(idxs))

    def performance_delta(self, idxs):
        winloss = 0
        blackrat = 0
        whiterat = 0
        for i in idxs:
            h = self.headers[i]
            winloss += h.Result
            blackrat += h.BlackElo
            whiterat += h.WhiteElo

        perf = (blackrat + 400 * winloss - whiterat) / len(idxs)

        return perf

    def read_directory(self, path):
        fnames = os.listdir(path)
        print len(fnames)
        i = 0
        for fname in fnames:
            print time.ctime(), i, fname
            kept, skipped = self.read_pgn(os.path.join(path, fname))
            print kept, skipped, len(self.headers), len(self.gdb),\
                  resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1000
            i += 1

    def read_pgn(self, fname):
        kept = 0
        skipped = 0
        #with open(fname, encoding="utf-8-sig", errors="surrogateescape") as f:
        with open(fname, 'rt') as f:
            while True:
                game = chess.pgn.read_game(f)
                if game is None:
                    break

                try:
                    h = parse_header(game.headers)
                except Exception as e:
                    print 'wrong headers', e
                    continue
                if not check_elo(h.WhiteElo) or not \
                        check_elo(h.BlackElo):
                    skipped += 1
                    continue

                kept += 1
                self.add_game(game, len(self.headers))

                self.headers.append(h)
                if len(self.headers) % 1000 == 0:
                    print len(self.headers)
        return kept, skipped

    def add_game(self, game, i, depth=0):
        if depth > MAX_GAME_DEPTH:
            return
        hfen = poshash(game.board())

        if game.variations:
            src, target, promo = make_move(game.variations[0])

            self.gdb.add_move(hfen, i, src, target, promo)
            self.add_game(game.variations[0], i, depth + 1)

    def board_stat(self, board):
        hfen = poshash(board)
        idxs = []
        moves = self.gdb.get_moves(hfen)
        if not moves:
            return {}

        for m in moves:
            idxs.append(m & ((1 << 24) - 1))

        return {
            'nrgames': len(idxs),
            'white_weighted': self.wweight.get_score(hfen),
            'black_weighted': self.bweight.get_score(hfen),
            'minimax': self.minmax.get_score(hfen),
            'draws': self.draws(idxs) * 100,
            'white_elo': self.average(idxs, 'WhiteElo'),
            'black_elo': self.average(idxs, 'BlackElo'),
            'score': (self.average(idxs, 'Result') + 1) * 50,
            'white_performance': self.performance_delta(idxs)
        }

    def full_board_stat(self, board):
        curboard = self.board_stat(board)

        hfen = poshash(board)
        moves = self.gdb.get_moves(hfen)
        c = Counter()
        if moves:
            for x in moves:
                x >>= 24
                if not x:
                    continue
                c.update([x])

        movestat = []
        for move, nr in c.most_common():
            mm = chess.Move(*dbcore.decompress(move << 24)[1:])
            board.push(mm)
            stat = self.board_stat(board)
            board.pop()
            stat['move'] = board.san(mm)
            movestat.append(stat)

        return {'board': curboard, 'moves': movestat}

    def print_bs(self, b):
        stats = self.full_board_stat(b)
        bs = stats['board']
        if not bs:
            print 'Not in DB'
        else:
            print '%d -> %.1f %.1f %.1f, %.2f %.2f, %d, %d, %d' % (
                bs['nrgames'], bs['white_weighted'], bs['black_weighted'],
                bs['minimax'], bs['score'], bs['draws'], bs['white_elo'],
                bs['black_elo'], bs['white_performance'])
        for bs in stats['moves']:
            if bs['minimax'] is not None:
                print '  %s: %d -> %.1f %.1f %.1f, %.2f %.2f, %d, %d, %d' % (
                    bs['move'], bs['nrgames'], bs['white_weighted'],
                    bs['black_weighted'], bs['minimax'], bs['score'],
                    bs['draws'], bs['white_elo'], bs['black_elo'],
                    bs['white_performance'])
            else:
                print '  %s: %d -> %.2f %.2f, %d, %d, %d' % (
                    bs['move'], bs['nrgames'], bs['score'], bs['draws'],
                    bs['white_elo'], bs['black_elo'], bs['white_performance'])

    def weighted(self, board, optimize_white=True, minsize=10, scorefun=None):
        if not scorefun:
            scorefun = self.performance_delta
        if optimize_white:
            self.wweight = dbcore.ScoreDB()
            self.wwrep = dbcore.ScoreDB()
        else:
            self.bweight = dbcore.ScoreDB()
            self.bwrep = dbcore.ScoreDB()
        self.seen = set()
        score = self._weighted(board, optimize_white, minsize, scorefun)
        self.seen = set()
        return score

    def _weighted(self, board, optimize_white, minsize, scorefun):
        hfen = poshash(board)
        if optimize_white:
            score = self.wweight.get_score(hfen)
        else:
            score = self.bweight.get_score(hfen)
        if score is not None:
            return score
        if hfen in self.seen or self.gdb.count_moves(hfen) < minsize:
            return None
        self.seen.add(hfen)

        scores = []
        wscores = []
        totnr = 0

        moves = self.gdb.get_moves(hfen)
        c = Counter()
        idxs = []
        if moves:
            for x in moves:
                idx, src, target, promo = dbcore.decompress(x)
                idxs.append(idx)
                if src == 0 and target == 0:
                    continue
                c.update([(src, target, promo)])

        for move, nr in c.most_common():
            board.push(chess.Move(*move))
            score = self._weighted(board, optimize_white, minsize, scorefun)
            if score is not None:
                scores.append(score)
                wscores.append(score * nr)
                totnr += nr
            board.pop()

        if not scores:
            score = scorefun(idxs)
            scores = [score]
            wscores = [score * totnr]

        if optimize_white:
            if board.turn:
                score = max(scores)
            else:
                score = sum(wscores) / totnr
            self.wweight.add_pos(hfen, score)
        else:
            if board.turn:
                score = sum(wscores) / totnr
            else:
                score = min(scores)
            self.bweight.add_pos(hfen, score)

        return score

    def minimax(self, board, minsize=10, scorefun=None):
        if not scorefun:
            scorefun = self.performance_delta
        self.score = dbcore.ScoreDB()
        self.seen = set()
        return self._minimax(board, minsize, scorefun)

    def _minimax(self, board, minsize, scorefun):
        hfen = poshash(board)
        score = self.minmax.get_score(hfen)
        if score is not None:
            return score
        if hfen in self.seen or self.gdb.count_moves(hfen) < minsize:
            return None
        self.seen.add(hfen)

        scores = []
        moves = self.gdb.get_moves(hfen)
        c = Counter()
        idxs = []
        if moves:
            for x in moves:
                idx, src, target, promo = dbcore.decompress(x)
                idxs.append(idx)
                if src == 0 and target == 0:
                    continue
                c.update([(src, target, promo)])

        for move, nr in c.most_common():
            board.push(chess.Move(*move))
            score = self._minimax(board, minsize, scorefun)
            if score is not None:
                scores.append(score)
            board.pop()

        if scores:
            if board.turn:  # white
                score = max(scores)
            else:
                score = min(scores)
        else:
            score = scorefun(idxs)

        self.minmax.add_pos(hfen, score)
        return score

    def traverse(self, board, minsize=10):
        self.seen = set()
        for x in self._traverse(board, minsize):
            yield x

    def _traverse(self, board, minsize):
        fen = board.fen()
        if fen in self.seen or len(self.metadata[fen]) < minsize:
            return
        self.seen.add(fen)
        yield board
        for san, nr in self.connections[fen].most_common():
            board.push_san(san)
            for x in self._traverse(board, minsize):
                yield x
            board.pop()
