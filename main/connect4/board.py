class board:
    def __init__(self,blankChar,P1,P2,numRows,numCols,content):
        self.blankChar=blankChar
        self.P1=P1
        self.P2=P2
        self.numRows=numRows
        self.numCols=numCols
        self.content=content
    def generate(self):
        self.content=list()
        for row in range(self.numRows):
            cRow=list()
            for col in range(self.numCols):
                cRow.append(self.blankChar)
            self.content.append(cRow)
    def pushMove(self,move,char):
        if char==self.P1:
            self.content[move[1]][move[0]]=self.P1
        elif char==self.P2:
            self.content[move[1]][move[0]]=self.P2
        else:
            self.content[move[1]][move[0]]=self.blankChar
    def validMoves(self):
        validCols=list()
        validMoves=list()
        for col in range(self.numCols):
            if self.content[self.numRows-1][col]==self.blankChar:
                validCols.append(col)
        for column in validCols:
            for row in range(self.numRows):
                if self.content[row][column]==self.blankChar:
                    validMoves.append([column,row])
                    break
        return validMoves,validCols
    def winCheck(self,char,consecNum):
        wins=0
        winner=None
        winText=''
        rowNum=-1
        fullness=True
        #LOOP THROUGH ALL ROWS ON BOARD
        for row in self.content:
            rowNum=rowNum+1
            #LOOP THROUGH ALL SPACES ON A ROW
            colNum=-1
            for space in row:
                colNum=colNum+1
                #ONLY CHECK SPACES FOR CORRECT CHARACTER
                if space==char:
                    counts=list()
                    #CHECK IN ALL DIRECTIONS FOR A SINGLE SPACE
                    for xMulti in range(-1,2):
                        for zMulti in range(-1,2):
                            #SKIP OVER CURRENT SPACE
                            if xMulti==0 and zMulti==0:
                                continue
                            counter=0
                            while True:
                                rowCheck=rowNum+zMulti*(counter+1)
                                colCheck=colNum+xMulti*(counter+1)
                                if rowCheck in range(self.numRows) and colCheck in range(self.numCols):
                                    #Check if there's another piece of the same type in this direction
                                    if self.content[rowNum+zMulti*(counter+1)][colNum+xMulti*(counter+1)]==char:
                                        counter=counter+1
                                    else:
                                        break
                                else:
                                    break
                            counts.append(counter)
                    for (x,y) in zip(range(0,4),reversed(range(4,8))):
                        if counts[x]+counts[y]+1>=consecNum:
                            #print('winner at '+str(rowNum)+' '+str(colNum))
                            wins=wins+1
                            winText='Game Over! '+char+' wins'
                            winner=char
                elif space==self.blankChar:
                    fullness=False
        if wins==0 and fullness==True:
            wins=1
            winText="Game Over! Its a tie"
            winner='tie'
        wins=wins/consecNum
        return wins,winText,winner
    def score(self,char,points):
        #THIS FUNCTION CALCULATES HOW GOOD THE BOARD IS FOR THE OPPOSING PLAYER (HIGHER SCORE IS BETTER FOR THE "CHAR" PLAYER WHO IS YOUR OPPONENT)
        [nonscoringCharacter,scoringCharacter]=self.findChars(char)
        score=0
        
        #Calculate board score
        rowNum=-1
        for row in self.content:
            rowNum=rowNum+1
            colNum=-1
            for space in row:
                colNum=colNum+1
                if space==char:
                    spaceScore=points['Row'+str(rowNum)+'Multiplier']*points['Column'+str(colNum)+'Score']
                    score=score+spaceScore
                    
        #Check to see if theres a winning move
        [wins,winText,winner]=self.winCheck(nonscoringCharacter,4)
        if wins>0:
            score=score+points['lossScore']*wins
        #Add score for wins
        [wins,winText,winner]=self.winCheck(scoringCharacter,4)
        if wins>0:
            score=score+points['winScore']*wins
            
        [P1wins,P1winLocations,P2wins,P2winLocations]=self.findWins()
        
        #Determine which opponent is which
        if scoringCharacter==self.P1:
            scoringPlayerWins=P1wins
            scoringPlayerWinLocations=P1winLocations
            nonscoringPlayerWins=P2wins
            nonscoringPlayerWinLocations=P2winLocations
        elif scoringCharacter==self.P2:
            scoringPlayerWins=P2wins
            scoringPlayerWinLocations=P2winLocations
            nonscoringPlayerWins=P1wins
            nonscoringPlayerWinLocations=P1winLocations
        
        [validMoves,validCols]=self.validMoves()    
        #Score for SCORING player win opportunities
        if scoringPlayerWins>0:
            #Add points for your wins
            score=score+points['scoringPlayerWins']*scoringPlayerWins
            #Check to see if move will be blocked instantly in next move
            winCount=0
            for move in scoringPlayerWinLocations:
                if move in validMoves:
                    #count how many places you can win next turn
                    winCount=winCount+1
            if winCount==1:
                score=score+points['scoringPlayerBlockPenalty']
            #find any stacked wins and add bonus for that
            checkedSpaces=list()
            for space in scoringPlayerWinLocations:
                for space2 in scoringPlayerWinLocations:
                    #CHECK TO SEE IF THE ROW NUMBERS ARE 1 APART AND IN THE SAME COLUMN
                    if abs(space[1]-space2[1])==1 and space[0]==space2[0] and space not in checkedSpaces and space2 not in checkedSpaces:
                        #MAKE SURE OPPONENT DOESN'T HAVE ALREADY WINNING MOVE BELOW US
                        check=True
                        for move in nonscoringPlayerWinLocations:
                            if move[0]==space[0] and move[1]<min(space[1],space2[1]):
                                check=False
                        if check==True:
                            score=score+points['scoringPlayerWinStackBonus']
                            checkedSpaces.append(space)
                            checkedSpaces.append(space2)

        #Score for NONSCORING player win opportunities
        if nonscoringPlayerWins>0:
            #Add points for your wins
            score=score+points['nonscoringPlayerWins']*nonscoringPlayerWins
            #Check to see if move will be blocked instantly in next move
            winCount=0
            for move in nonscoringPlayerWinLocations:
                if move in validMoves:
                    winCount=winCount+1
            if winCount==1:
                score=score+points['nonscoringPlayerBlockPenalty']
            #find any stacked wins and add bonus for that
            checkedSpaces=list()
            for space in nonscoringPlayerWinLocations:
                for space2 in nonscoringPlayerWinLocations:
                    #CHECK TO SEE IF THE ROW NUMBERS ARE 1 APART AND IN THE SAME COLUMN
                    if abs(space[1]-space2[1])==1 and space[0]==space2[0] and space not in checkedSpaces and space2 not in checkedSpaces:
                        #MAKE SURE OPPONENT DOESN'T HAVE ALREADY WINNING MOVE BELOW US
                        check=True
                        for move in scoringPlayerWinLocations:
                            if move[0]==space[0] and move[1]<min(space[1],space2[1]):
                                check=False
                        if check==True:
                            score=score+points['nonscoringPlayerWinStackBonus']
                            checkedSpaces.append(space)
                            checkedSpaces.append(space2)
        return score
    
        #add bonus if two wins are stacked
        
    
    def findChars(self,char):
        if char==self.P1:
            OPCharacter=self.P2
            myCharacter=self.P1
        else:
            OPCharacter=self.P1
            myCharacter=self.P2
        return OPCharacter,myCharacter
    
    def findWins(self):
        #This function goes through all of the blank spaces and see if it has 3 or more of either character in a row for each direction.
        #The function returns the number of wins for each player, and the position of each win [P1wins,P1winLocations,P2wins,P2winLocations]
        rowNum=-1
        P1wins=0
        P2wins=0
        P1winLocations=list()
        P2winLocations=list()
        #LOOP THROUGH ALL ROWS ON BOARD
        for row in self.content:
            rowNum=rowNum+1
            #LOOP THROUGH ALL SPACES ON A ROW
            colNum=-1
            for space in row:
                colNum=colNum+1
                #ONLY CHECK SPACES FOR CORRECT CHARACTER
                if space==self.blankChar:
                    for character in [self.P1,self.P2]:
                        counts=list()
                        #CHECK IN ALL DIRECTIONS FOR A SINGLE SPACE
                        for xMulti in range(-1,2):
                            for zMulti in range(-1,2):
                                counter=0
                                #SKIP OVER CURRENT SPACE
                                if xMulti==0 and zMulti==0:
                                    continue
                                while True:
                                    rowCheck=rowNum+zMulti*(counter+1)
                                    colCheck=colNum+xMulti*(counter+1)
                                    #Make sure not to check spaces that are outside the board
                                    if rowCheck in range(self.numRows) and colCheck in range(self.numCols):
                                        #Check if there's another piece of the same type in this direction
                                        if self.content[rowNum+zMulti*(counter+1)][colNum+xMulti*(counter+1)]==character:
                                            counter=counter+1
                                        else:
                                            break
                                    else:
                                        break
                                counts.append(counter)
                        for (x,y) in zip(range(0,4),reversed(range(4,8))):
                            if counts[x]+counts[y]>=3:
                                #print('winner at '+str(rowNum)+' '+str(colNum))
                                if character==self.P1:
                                    P1winLocations.append([colNum,rowNum])
                                    P1wins=P1wins+1
                                elif character==self.P2:
                                    P2winLocations.append([colNum,rowNum])
                                    P2wins=P2wins+1
                                break
        return P1wins,P1winLocations,P2wins,P2winLocations
        