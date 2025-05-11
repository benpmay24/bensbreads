def evalMoves(board,char,points):
    [OPCharacter,myCharacter]=board.findChars(char)
    minScore=1000000
    for move in board.validMoves()[0]:
        board.pushMove(move,char)
        OPscores=list()
        maxOPScore=-1000000
        for OPmove in board.validMoves()[0]:
            board.pushMove(OPmove,OPCharacter)
            #printBoard(board)
            OPscore=board.score(OPCharacter,points)
            #print(OPscore)
            #print('Score for '+OPCharacter+' :')
            #print(OPscore)
            if OPscore>maxOPScore:
                maxOPScore=OPscore
            board.pushMove(OPmove,board.blankChar)
        if maxOPScore<minScore:
            minScore=maxOPScore
            bestMove=move
        board.pushMove(move,board.blankChar)
    #print(minScore)
    return bestMove