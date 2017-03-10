var board;
var game = new Chess();

var moves;
var movenr = 0;

var cfg;

/*
--
deploy

--
klicka för att göra drag
Visa nuvarande ställning-stat
Formatera tabell bredvid bräde (Bootstrap?)
färglägg förslag/varningar
memcache?
*/

function takeback(){
    game.undo();
    onSnapEnd();
    getStats();
}

function getStats(){
    $.ajax({url: "/fenstats/" + game.fen(), success: function(stat){
        $("#move-table").tabulator("setData", stat['moves']);
    }, cache: true});
}

function reset(){
    board = ChessBoard('board', cfg);
    game = new Chess();
    movenr = 0;

    $('#message').html('&nbsp;');
    $('#status').html('&nbsp;');
    $('#pgn').text('');
}


var removeGreySquares = function() {
  $('#board .square-55d63').css('background', '');
};

var greySquare = function(square) {
  var squareEl = $('#board .square-' + square);

  var background = '#a9a9a9';
  if (squareEl.hasClass('black-3c85d') === true) {
    background = '#696969';
  }

  squareEl.css('background', background);
};

var onDragStart = function(source, piece) {
  // do not pick up pieces if the game is over
  // or if it's not that side's turn
  if (game.game_over() === true ||
      (game.turn() === 'w' && piece.search(/^b/) !== -1) ||
      (game.turn() === 'b' && piece.search(/^w/) !== -1)) {
    return false;
  }
};

var onDrop = function(source, target) {
    removeGreySquares();

    // see if the move is legal
    var move = game.move({
        from: source,
        to: target,
        promotion: 'q' // TODO: promotion choice
    });

    if (move === null) return 'snapback';

    movenr++;
    getStats();
};

var onMouseoverSquare = function(square, piece) {
  // get list of possible moves for this square
  var moves = game.moves({
    square: square,
    verbose: true
  });

  // exit if there are no moves available for this square
  if (moves.length === 0) return;

  // highlight the square they moused over
  greySquare(square);

  // highlight the possible squares for this piece
  for (var i = 0; i < moves.length; i++) {
    greySquare(moves[i].to);
  }
};

var onMouseoutSquare = function(square, piece) {
  removeGreySquares();
};

var onSnapEnd = function() {
    board.position(game.fen());
    $('#pgn').text(game.pgn());
};

var intformat = function(value, data, cell, row, options, formatterParams){
    return Math.round(value);
};

cfg = {
    draggable: true,
    position: 'start',
    onDragStart: onDragStart,
    onDrop: onDrop,
    onMouseoutSquare: onMouseoutSquare,
    onMouseoverSquare: onMouseoverSquare,
    onSnapEnd: onSnapEnd
};

$( document ).ready(function(){
    $('#takeback').click(takeback);
    reset();
    $("#move-table").tabulator({
        columns:[
            {title:"Move", field:"move", sortable: false},
            {title:"Nr", field:"nrgames", sortable:true, sorter:"number", align:"right", width:60},

            {title:"Ww", field:"white_weighted", sortable:true, sorter:"number", align:"right", width:60, formatter: intformat},
            {title:"Bw", field:"black_weighted", sortable:true, sorter:"number", align:"right", width:60, formatter: intformat},
            {title:"Mm", field:"minimax", sortable:true, sorter:"number", align:"right", width:60, formatter: intformat},

            {title:"Score%", field:"score", sortable:true, sorter:"number", align:"right", width: 85, formatter: intformat},
            {title:"Draw%", field:"draws", sortable:true, sorter:"number", align:"right", width: 85, formatter: intformat},

            {title:"W Perf", field:"white_performance", sortable:true, sorter:"number", align:"right", width: 80, formatter: intformat},
            {title:"W Elo", field:"white_elo", sortable:true, sorter:"number", align:"right", width: 80, formatter: intformat},
            {title:"B Elo", field:"black_elo", sortable:true, sorter:"number", align:"right", width: 80, formatter: intformat},
        ],
        sortBy:"nrgames"
    });

    getStats();
});

//Make adaptive with this
function adjustStyle(width) {
    width = parseInt(width);
    if (width < 701) {
        $("#size-stylesheet").attr("href", "css/narrow.css");
    } else if (width < 900) {
        $("#size-stylesheet").attr("href", "css/medium.css");
    } else {
        $("#size-stylesheet").attr("href", "css/wide.css");
    }
}
