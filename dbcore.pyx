from cython.operator cimport dereference as deref

from libcpp.unordered_map cimport unordered_map
from libcpp.vector cimport vector

# from SO, to use streams
cdef extern from "<iostream>" namespace "std":
    cdef cppclass ostream:
        ostream& write(const char*, int) except +
    cdef cppclass istream:
        istream& read(char*, int) except +

# obviously std::ios_base isn't a namespace, but this lets
# Cython generate the correct C++ code
cdef extern from "<iostream>" namespace "std::ios_base":
    cdef cppclass open_mode:
        pass
    cdef open_mode binary
    # you can define other constants as needed

cdef extern from "<fstream>" namespace "std":
    cdef cppclass ofstream(ostream):
        # constructors
        ofstream(const char*) except +
        ofstream(const char*, open_mode) except+

    cdef cppclass ifstream(istream):
            # constructors
        ifstream(const char*) except +
        ifstream(const char*, open_mode) except+
# end streams


cdef unsigned long compress_move(unsigned long idx, unsigned long src,
                                 unsigned long target, unsigned long piece):
    return idx | (src << 32) | (target << 40) | (piece << 48)

def decompress(move):
    return move & ((1L << 32) - 1), (move >> 32) & ((1L << 8) - 1),\
           (move >> 40) & ((1L << 8) - 1), (move >> 48) & ((1L << 3) - 1)

ctypedef vector[unsigned long] movelist
cdef class GraphDB:
    cdef unordered_map[unsigned long, movelist] db

    def save(self, fname):
        outf = new ofstream(fname, binary)
        try:
            self._save(outf)
        finally:
            del outf

    cdef void _save(self, ostream *outf):
        cdef unsigned int l = self.db.size()
        cdef unsigned long hash
        outf.write(<const char *>&l, sizeof(unsigned int))

        for t in self.db:
            hash = t.first
            outf.write(<const char *>&hash, sizeof(unsigned long))

            l = t.second.size()
            outf.write(<const char *>&l, sizeof(unsigned int))
            outf.write(<const char *>t.second.data(), t.second.size() * sizeof(unsigned long))

    def load(self, fname):
        inf = new ifstream(fname, binary)
        try:
            self._load(inf)
        finally:
            del inf

    cdef void _load(self, ifstream *inf):
        cdef unsigned int l, lv
        cdef unsigned long hash
        cdef movelist *vec
        inf.read(<char *>&l, sizeof(unsigned int))

        for i in xrange(l):
            inf.read(<char *>&hash, sizeof(unsigned long))

            inf.read(<char *>&lv, sizeof(unsigned int))

            vec = new movelist()
            vec.resize(lv)
            inf.read(<char *>vec.data(), lv * sizeof(unsigned long))

            self.db[hash] = deref(vec)
            del vec

    def add_move(self, poshash, idx, src, target, piece):
        move = compress_move(idx, src, target, piece)
        self.db[poshash].push_back(move)
        return move

    def cam(self):
        return self.count_all_moves()

    cdef unsigned long count_all_moves(self):
        cdef unsigned long s = 0
        for t in self.db:
            s += t.second.size()
        return s

    def count_moves(self, poshash):
        nr = self.db.count(poshash)
        if nr == 0:
            return 0
        return self.db[poshash].size()

    cpdef get_move_tuples(self, poshash):
        cdef unordered_map[unsigned long, unsigned int] counter
        for m in self.db[poshash]:
            counter[m >> 24] += 1
        return counter

    def get_moves(self, poshash):
        nr = self.db.count(poshash)
        if nr == 0:
             return None
        return self.db[poshash]

    def get_positions(self):
        for t in self.db:
            yield t.first

    def set_moves(self, poshash, moves):
        self.db[poshash] = moves

    def __len__(self):
        return self.db.size()

cdef class ScoreDB:
    cdef unordered_map[unsigned long, float] db

    def add_pos(self, poshash, score):
        self.db[poshash] = score

    def get_score(self, poshash):
        nr = self.db.count(poshash)
        if nr == 0:
            return None
        return self.db[poshash]

    def get_posscores(self):
        for t in self.db:
            yield t

    def save(self, fname):
        outf = new ofstream(fname, binary)
        try:
            self._save(outf)
        finally:
            del outf

    cdef void _save(self, ostream *outf):
        cdef unsigned int l = self.db.size()
        cdef unsigned long hash
        cdef float score
        outf.write(<const char *>&l, sizeof(unsigned int))

        for t in self.db:
            hash = t.first
            outf.write(<const char *>&hash, sizeof(unsigned long))

            score = t.second
            outf.write(<const char *>&score, sizeof(float))

    def load(self, fname):
        inf = new ifstream(fname, binary)
        try:
            self._load(inf)
        finally:
            del inf

    cdef void _load(self, ifstream *inf):
        cdef unsigned int l
        cdef float score
        cdef unsigned long hash

        inf.read(<char *>&l, sizeof(unsigned int))

        for i in xrange(l):
            inf.read(<char *>&hash, sizeof(unsigned long))

            inf.read(<char *>&score, sizeof(float))

            self.db[hash] = score


    def __len__(self):
        return self.db.size()
