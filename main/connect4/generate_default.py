def generateDefault():
    numRows=6
    numCols=7
    points=dict()
    scores=dict()
    points['winScore']=10000
    points['lossScore']=-100000
    points['scoringPlayerWins']=75
    points['scoringPlayerWinStackBonus']=300
    points['nonscoringPlayerWins']=-50
    points['nonscoringPlayerWinStackBonus']=-200
    points['scoringPlayerBlockPenalty']=-100
    points['nonscoringPlayerBlockPenalty']=75
    rowMultiplier=[1.5,1.4,1.3,1.2,1.1,1]
    columnScore=[5,6,7,8,7,6,5]
    rowCounter=-1
    for number in rowMultiplier:
        rowCounter=rowCounter+1
        parameter='Row'+str(rowCounter)+'Multiplier'
        points[parameter]=number
    colCounter=-1
    for number in columnScore:
        colCounter=colCounter+1
        parameter='Column'+str(colCounter)+'Score'
        points[parameter]=number
    for parameter in points.keys():
        scores[parameter]=0.33
    return points,scores