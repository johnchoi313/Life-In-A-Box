#Citations:
#Built from simple fps controls and collision done by treeform:
    #http://www.panda3d.org/forums/viewtopic.php?t=4068
#lots of simple examples from panda3d forums and documentation
    #described in code where appropriate...

#import modules (built into Panda3d)
import direct.directbase.DirectStart
from direct.showbase.DirectObject import DirectObject
from direct.filter.CommonFilters import CommonFilters
from direct.interval.LerpInterval import *
from direct.interval.IntervalGlobal import *
from panda3d.core import WindowProperties

#materials
from pandac.PandaModules import *
from panda3d.core import Material
from panda3d.core import VBase4

#import other standard libraries
from math import *
from random import *
import copy
import os
from PIL import Image

#main class
class LifeInABox(object,DirectObject):
    def __init__(self):
        #set first pass to false:
        self.firstPass = True; self.creationReady = True; self.creationStart = 0; self.doorReady = False; self.doorOpen = False
        
        #initialize~!!
        self.maxResolution(resolution = None,fullscreen = True)
        self.initText()
        self.initLights(startColor = VBase4(0,0,0,1),
                        toColor = VBase4(.5,.5,.5,1),
                        colorUpdateSpeed = 0.10,
                        fogDensity = 0.015,
                        lightColor = VBase4(.65,.65,.65,1))
        self.initTextures()
        self.initCollision()
        self.initPlayer(playerSpeed=10,playerStartPos=(0,-7,.6))
        self.generateMaze(layers = 2,sep = 1.0,pieceSpeed = 4,pieceDelay=.23)
        self.loadLevel()
        self.initCamera(120,0.1,100000.0,3)
        self.initSounds()
        
        #pretty effects... (used panda 3d docs for sample)
        filters = CommonFilters(base.win, base.cam)
        filters.setBloom(blend = (0.3,0.4,0.3,0.0),
                         mintrigger = .4,
                         maxtrigger = 1.0,
                         desat = 0.6,
                         intensity = 1.0,
                         size = "large") #wow... that was easy
        filters.setAmbientOcclusion() #wow, sooo pretty...
        render.setAntialias(AntialiasAttrib.MAuto)
        
        #initialize timer
        self.oldTime = 0; self.deltaTime = 0
        
        #add tasks:
        taskMgr.add(self.showTextTask, "Show Text Task") #text task
        taskMgr.add(self.updateBackgroundColor,"Update Background Color")

        #player control
        taskMgr.add(self.move, 'move-task')
        taskMgr.add(self.shakeCamera, 'shake-task')
        
        #balloon game loop
        taskMgr.add(self.balloonGame, 'balloon task')
        
#---------------------------------------------------------------------------#
    
    #resolution changer from http://www.panda3d.org/forums/viewtopic.php?t=8828
    #and from http://www.panda3d.org/forums/viewtopic.php?p=63967
    def maxResolution(self,resolution = None,fullscreen = True):
        wp = WindowProperties()
        
        if resolution == None:
            w=base.pipe.getDisplayWidth()
            h=base.pipe.getDisplayHeight()
        else:
            w,h = resolution
            
        wp.setSize( w, h )
        #hide mouse from forums (http://www.panda3d.org/forums/viewtopic.php?t=7948)
        
        wp.setCursorHidden(True)
        wp.setFullscreen(fullscreen)
        
        base.win.requestProperties( wp ) 

#---------------------------------------------------------------------------#
    
    def initSounds(self):
        
        #load walk sounds (from the game creators, Dark BAsic Pro Media)
        self.walkSound = loader.loadSfx("sounds/Girly slow.ogg")
        self.walkSound.setLoop(True)
        self.walkSound.setVolume(.3)
        
        #load switch sound
        self.switchSound = loader.loadSfx("sounds/switch.ogg")
        self.switchSound.setVolume(.9) 
        
        #load door sound
        self.doorSound = loader.loadSfx("sounds/door.ogg")
        self.switchSound.setVolume(.2) 
        
        #load ambient noise...
        #http://www.freesound.org/people/benb1n/sounds/90873/
        self.ambientSound = loader.loadSfx("sounds/ambient.ogg")
        self.ambientSound.setLoop(True)
        self.ambientSound.setVolume(.015)
        self.ambientSound.play()
        
        #recursively load all music in our myMusic folder:
        self.myMusic = self.loadMusic('myMusic')
        for index in xrange(len(self.myMusic)):
            #0 = music, 1 = path
            self.myMusic[index][0] = loader.loadSfx(self.myMusic[index][1])
            self.myMusic[index][0].setLoop(True)
            self.myMusic[index][0].setVolume(.3)
        
        #set our first music to play:
        self.currentMusic = 0
        
    #recursive music loading! (based off of my own image loader (see below))
    def loadMusic(self,path):
        #create a list to return
        musicList = []
    
        #get a list of all the items in the current folder 
        for item in os.listdir(path):
            newPath = path + '/' + item
            #check if it is a file:
            if os.path.isdir(newPath) == False:
                #check if it is music:
                if (item[len(item)-4:].upper() == '.OGG' or item[len(item)-4:].upper() == '.WAV' or
                   item[len(item)-4:].upper() == '.MP3'):
                    #0 = music, 1 = path
                    musicList.append([0,newPath])
            #if it is a folder:
            else:
                musicList.extend(self.loadMusic(newPath))
    
        #return the resultant list
        return musicList
        
    
#---------------------------------------------------------------------------#    
    
    #text node tutorial from panda 3d documentation (heavily modified by me)
    #http://www.panda3d.org/playerual/index.php/Text_Node
    def initText(self):
    
        #load fonts
        self.cour = loader.loadFont('fonts/cour.ttf');
        
        #create title
        self.title = TextNode('info') #create the title!
        self.titleNodePath = aspect2d.attachNewNode(self.title)
        #first propertization
        message = "Life In A Box"
        self.propertizeText(self.title,self.titleNodePath,message,self.cour,
                            (0,0),.075,TextNode.ACenter,(.2,.2,.2,1))
        
        #create balloon text
        self.balloonText = TextNode('info') #create the balloon text
        self.balloonTextPath = aspect2d.attachNewNode(self.balloonText)
        self.showBalloonText = 0
        #first propertization
        message = "Press [Left Mouse] to activate."
        self.propertizeText(self.balloonText,self.balloonTextPath,message,self.cour,
                            (0,0),.075,TextNode.ACenter,(.2,.2,.2,1))
        
        #create door text
        self.doorText = TextNode('info') #create the balloon text
        self.doorTextPath = aspect2d.attachNewNode(self.doorText)
        self.showDoorText = 0
        #first propertization
        message = "Press [Left Mouse] to exit."
        self.propertizeText(self.balloonText,self.balloonTextPath,message,self.cour,
                            (0,0),.075,TextNode.ACenter,(.2,.2,.2,1))
        
        
    def showTextTask(self,task):
        
        #set title properties
        message = "Life In A Box"
        self.propertizeText(self.title,self.titleNodePath,message,self.cour,
                            (randint(-10,10)*.001,randint(-10,10)*.001),.075,
                            TextNode.ACenter,
                            (.1,.1,.1,0) ) #hidden for now
        
        #set balloonText properties
        message = "Press [Left Mouse] to activate."
        self.propertizeText(self.balloonText,self.balloonTextPath,message,self.cour,
                            (0,0),.075,TextNode.ACenter,(.2,.2,.2,self.showBalloonText))
        
        #set balloonText properties
        message = "Press [Left Mouse] to exit."
        self.propertizeText(self.doorText,self.doorTextPath,message,self.cour,
                            (0,0),.075,TextNode.ACenter,(.2,.2,.2,self.showDoorText))
        
        return task.cont
    
    #quick function to apply properties of a function
    def propertizeText(self,text,textNodePath,message = '',font=None,
                       pos=(0,0),scale = .075,align = TextNode.ALeft,
                       color = (1,1,1,1)):
        if font != None: text.setFont(font)
        text.setText(message)
        posx,posy = pos
        textNodePath.setPos(posx,0,posy)
        textNodePath.setScale(scale)
        text.setAlign(align)
        text.setTextColor(color)

#---------------------------------------------------------------------------#

    def initLights(self,startColor=(0,0,0,1),toColor=(1,1,1,1),
                   colorUpdateSpeed=.01,fogDensity =.05,lightColor=(.5,.5,.5,1)):
        
        #let there be light...!!!! (from panda3d standard documentation)
        #from http://www.panda3d.org/playerual/index.php/Lighting
        dlight = DirectionalLight('dlight') #make directional
        dlnp = render.attachNewNode(dlight) #attach to the renderer
        dlnp.setHpr(0, -80, 45) #set the light angle
        dlnp.setColor(lightColor)
        render.setLight(dlnp) #prepare the light
        
        # Add an ambient light(from bump maps demo)
        self.alight = AmbientLight('alight')
        alnp = render.attachNewNode(self.alight)
        self.alight.setColor(lightColor)
        render.setLight(alnp) #prepare the light
        
        #create a point light that follows player
        plight = PointLight('plight')
        plight.setColor(VBase4(1.95, 1.95, 1.95, 1))
        plight.setAttenuation(Point3(0, 0, 1.0))
        self.plnp = render.attachNewNode(plight)
        render.setLight(self.plnp)
        
        #define background color variables...
        self.backgroundColor = startColor
        self.newBackgroundColor = toColor
        self.backgroundUpdateSpeed = colorUpdateSpeed
        
        #cool fog... (from panda 3d docs)
        self.fog = Fog("fog"); self.fog.setExpDensity(fogDensity)
        #load level cylinder and floor pieces
        self.background = loader.loadModel('meshes/background')
        self.propertizeObject(self.background,scale=1000, useLight = False)
        
        #apply initial background colors
        self.background.setColor(self.backgroundColor) #sky object
        self.fog.setColor(self.backgroundColor) #fog
        
    #and my own update background function!
    def updateBackgroundColor(self,task):
        #apply new colors    
        self.background.setColor(self.backgroundColor) #sky object
        self.fog.setColor(self.backgroundColor) #fog
        #self.alight.setColor(self.backgroundColor)
        #define vars
        speed = self.backgroundUpdateSpeed
        fr,fg,fb,fa = self.backgroundColor
        tr,tg,tb,ta = self.newBackgroundColor
        #check where lerp is
        if (fr-tr)>0: fr-=speed*self.deltaTime
        else : fr+=speed*self.deltaTime
        if (fg-tg)>0: fg-=speed*self.deltaTime
        else : fg+=speed*self.deltaTime
        if (fb-tb)>0: fb-=speed*self.deltaTime
        else : fb+=speed*self.deltaTime
        if (fa-ta)>0: fa-=speed*self.deltaTime
        else : fa+=speed*self.deltaTime
        #set new color
        self.backgroundColor = VBase4(fr,fg,fb,fa)
        return task.cont

#---------------------------------------------------------------------------#
   
   #beautiful....
    def initTextures(self):
        #load level textures (standard)
        self.grey = loader.loadTexture('textures/grey.png')
        self.balloontx = loader.loadTexture('textures/balloon.png')
        self.door_tex = loader.loadTexture('textures/door_bake.png')
        
        #get all possible maze textures
        self.maze_tex = self.loadImages('mazeTex',mazeTex=True)
        for index in xrange(len(self.maze_tex)):
            #0 = texture, 1 = path, 2 = image size, 3 = frame object, 4 = picture object
            self.maze_tex[index][0] = loader.loadTexture(self.maze_tex[index][1])
        
        #get frame tex
        self.frame_tex = loader.loadTexture('textures/frame.png')
        
        #recursively load all images in our myPictures folder:
        self.myPictures = self.loadImages('myPictures')
        for index in xrange(len(self.myPictures)):
            #0 = texture, 1 = path, 2 = image size, 3 = frame object, 4 = picture object
            self.myPictures[index][0] = loader.loadTexture(self.myPictures[index][1])
        
    #quick shortcut to apply lots of Panda features at once!
    def propertizeTexture(self,tex,wrapMode = Texture.WMRepeat,
                          filterMode = Texture.FTLinear):
        tex.setWrapU(wrapMode)
        tex.setWrapV(wrapMode)
        tex.setMagfilter(filterMode)
        tex.setMinfilter(filterMode)     

    #recursive picture loading function! (made by myself, based off of class notes)
    def loadImages(self,path,mazeTex = False):
        #create a list to return
        imageList = []
    
        #get a list of all the items in the current folder 
        for item in os.listdir(path):
            newPath = path + '/' + item
            #check if it is a file:
            if os.path.isdir(newPath) == False:
                #check if it is an image:
                if item[len(item)-4:].upper() == '.JPG' or item[len(item)-4:].upper() == '.PNG':
                    #add this item to our list
                    image = Image.open(newPath)
                    #0 = texture, 1 = path, 2 = image size, 3 = frame object, 4 = picture object, 5 = pos, 6 = angleH
                    if mazeTex == False: imageList.append([0,newPath,image.size,0,0,(0,0,0),(0,0,0)])
                    else: imageList.append([0,newPath])
            #if it is a folder:
            else:
                imageList.extend(self.loadImages(newPath))
    
        #return the resultant list
        return imageList

#---------------------------------------------------------------------------#

    #my own maze generation algorithm implementation, using depth first search
    #conceptual help from: http://www.mazeworks.com/mazegen/mazetut/
    def generateMaze(self,layers=2,sep = 1,pieceSpeed = 4,pieceDelay=.25,pieceSpread = 10.0,firstMaze = True):
                
        #set the amount of layers we wish to create 
        self.layers = layers ; self.sep = sep
        
        #set the speed of maze generation
        self.pieceDelay = pieceDelay
        self.pieceSpeed = pieceSpeed
        self.spread = pieceSpread
        
        #[True,1,2]:# first value = true or false (1 or 0),
                    # second value = object
                    # third value = collider 
        
        #if we were creating our first maze:
        if firstMaze == True:
        
            #-------------------------------#
    
            #create a list of floor pieces
            self.floorPiece = []
            for row in xrange(layers*2+1):
                colList = []
                for col in xrange(layers*2+1):
                    colList.append([0])
                self.floorPiece.append(colList)
    
            #-------------------------------#
            
            #create a list of wall rows
            self.wallRow = []
            for row in xrange(layers*2+1):
                colList = []
                for col in xrange(layers*2+2):
                    colList.append([1,1,2])
                self.wallRow.append(colList)
            
            #create a list of wall cols
            self.wallCol = []
            for row in xrange(layers*2+2):
                colList = []
                for col in xrange(layers*2+1):
                    colList.append([1,1,2]) 
                self.wallCol.append(colList)
    
            #-------------------------------#

        #we are not creating our first maze:
        else:
        
            #-------------------------------#
            
            #create a list of wall rows
            for row in xrange(layers*2+1):
                for col in xrange(layers*2+2):
                    self.wallRow[row][col][0]=1
            
            #create a list of wall cols
            for row in xrange(layers*2+2):
                for col in xrange(layers*2+1):
                    self.wallCol[row][col][0]=1
    
            #-------------------------------#
      
        #create a master board
        self.masterBoard = []
        for row in xrange(layers*2+1):
            colList = []
            for col in xrange(layers*2+1):
                colList.append(0) 
            self.masterBoard.append(colList)
        
        #create solved board
        self.solvedBoard = []
        for row in xrange(layers*2+1):
            colList = []
            for col in xrange(layers*2+1):
                colList.append(1) 
            self.solvedBoard.append(colList)

        #-------------------------------#
        
        self.solveMaze()
        self.getPossiblePicturePositions()
        
    #recursively go through this board
    def solveMaze(self, pos = (0,0)):
    
        #set starting point
        posx,posy  = pos
    
        #set the current position to True (meaning we already been there)
        self.masterBoard[posx][posy] = 1
    
        #recursive go thorugh all directions randomly and set values to true
        directions = ['up','down','left','right']
        while directions != [] and self.masterBoard != self.solvedBoard:
    
            #get direction to check
            direction = choice(directions)
            
            #check direction
            if direction == 'right':
                if posy+1 < len(self.masterBoard[0]):
                    if self.masterBoard[posx][posy+1] == 0:
                        #break a wall
                        self.wallRow[posx][posy+1][0] = 0
                        #and continue
                        self.solveMaze((posx,posy+1))
            if direction == 'left':
                if posy-1 > 0:
                    if self.masterBoard[posx][posy-1] == 0:
                        #break a wall
                        self.wallRow[posx][posy-1][0] = 0
                        #and continue
                        self.solveMaze((posx,posy-1))
            if direction == 'down':
                if posx+1 < len(self.masterBoard):
                    if self.masterBoard[posx+1][posy] == 0:
                        #break a wall
                        self.wallCol[posx+1][posy][0] = 0
                        #and continue
                        self.solveMaze((posx+1,posy))
            if direction == 'up':
                if posx-1 > 0:
                    if self.masterBoard[posx-1][posy] == 0:
                        #break a wall
                        self.wallCol[posx-1][posy][0] = 0
                        #and continue
                        self.solveMaze((posx-1,posy))
    
            #remove this choice from this list
            directions.pop(directions.index(direction))

    def getPossiblePicturePositions(self):
        #universal maze variables
        layers = self.layers ; sep = self.sep    
        
        #possible positions for wall cols
        self.colPositions = [] #create a list of possible positions
        wallCol = self.wallCol
        for row in xrange(-layers,layers+2):
            for col in xrange(-layers,layers+1,1):
                if wallCol[row+layers][col+layers][0] == 1:
                    #add to our list of possible positions (if not outer edge!)
                    if row != -layers:
                        self.colPositions.append([(row,col),0]) #row, col orientation 0 is available
                    if row != layers+1:
                        self.colPositions.append([(row,col),1]) #row, col orientation 1 is available
                
        #possible positions for wall rows
        self.rowPositions = [] #create a list of possible positions
        wallRow = self.wallRow
        for col in xrange(-layers,layers+2):
            for row in xrange(-layers,layers+1,1):
                if wallRow[row+layers][col+layers][0] == 1 and (row != 0 or col != -layers):
                    #add to list of possible positions (if not outer edge!)
                    if col != layers+1:
                        self.rowPositions.append([(row,col),0]) #row, col orientation 0 is available
                    if col != -layers: 
                        self.rowPositions.append([(row,col),1]) #row, col orientation 1 is available
        
    

#---------------------------------------------------------------------------#
    
    #a lot of very cool maze generation sequences!
    #ALL HARDCODED BY -- YOU GUESSED IT -- ME!!!!!!!!!
    def startSequence(self, objects, objIndex, seq = 0, delay = 0):
    
        #universal maze variables
        layers = self.layers ; sep = self.sep    
        floorPiece = self.floorPiece
        wallRow = self.wallRow; wallCol = self.wallCol
        
        #col add and row add (for those extra edge walls)
        colAdd = 0
        if objects == self.wallRow: colAdd += 1
        rowAdd = 0
        if objects == self.wallCol: rowAdd += 1
        
        #creation sequence 1:
        if seq == 0:
    
            #set sequence variables for all floor pieces!
            count = 0
            for col in xrange(-layers,layers+1+colAdd):
                for row in xrange(-layers,layers+1+rowAdd,1):
                    #get the type of object list and get the requirements of each respectively:
                    if( ((row != 0 or col != 0) and objects == self.floorPiece) or 
                        ((wallCol[row+layers][col+layers-colAdd][0] == 1) and objects == self.wallCol) or
                        ((wallRow[row+layers-rowAdd][col+layers][0] == 1) and objects == self.wallRow) ):
                        #get to and from places: (based on objects)
                        mazePoint,awayPoint = self.getPositions(objects,row,col)
                        #define the floor object we want
                        obj = objects[row+layers][col+layers][objIndex]
                        #create the intervals
                        interval = obj.posInterval(self.pieceSpeed,mazePoint,startPos=awayPoint)
                        roterval = obj.hprInterval(self.pieceSpeed*1.05,Point3(0,0,0),startHpr=Point3(randint(0,360),randint(0,360),randint(0,360)))
                        #create the sequence
                        pieceSequence = Sequence(Wait(self.pieceDelay*count+delay),Parallel(interval,roterval))            
                        #play this sequence
                        pieceSequence.start()
                        count+=1
        
        #destruction sequence 1:
        if seq == 1:
    
            #set sequence variables for all floor pieces!
            count = 0
            for col in xrange(-layers,layers+1+colAdd):
                for row in xrange(-layers,layers+1+rowAdd,1):
                    #get the type of object list and get the requirements of each respectively:
                    if( ((row != 0 or col != 0) and objects == self.floorPiece) or 
                        ((wallCol[row+layers][col+layers-colAdd][0] == 1) and objects == self.wallCol) or
                        ((wallRow[row+layers-rowAdd][col+layers][0] == 1) and objects == self.wallRow) ):
                        #get to and from places: (based on objects)
                        mazePoint,awayPoint = self.getPositions(objects,row,col)
                        #define the floor object we want
                        obj = objects[row+layers][col+layers][objIndex]
                        #create the intervals
                        interval = obj.posInterval(self.pieceSpeed,awayPoint,startPos=mazePoint)
                        roterval = obj.hprInterval(self.pieceSpeed,Point3(0,0,0),startHpr=Point3(randint(0,360),randint(0,360),randint(0,360)))
                        #create the sequence
                        pieceSequence = Sequence(Wait(self.pieceDelay*count+delay),Parallel(interval,roterval))            
                        #play this sequence
                        pieceSequence.start()
                        count+=1

        #floor creation sequence (2):
        if seq == 2:
    
            #set sequence variables for all floor pieces!
            count = 0
            for col in xrange(-layers,layers+1+colAdd):
                for row in xrange(-layers,layers+1+rowAdd,1):
                    #get the type of object list and get the requirements of each respectively:
                    if( ((row != 0 or col != 0) and objects == self.floorPiece) or 
                        ((wallCol[row+layers][col+layers-colAdd][0] == 1) and objects == self.wallCol) or
                        ((wallRow[row+layers-rowAdd][col+layers][0] == 1) and objects == self.wallRow) ):
                        #get to and from places: (based on objects)
                        mazePoint,awayPoint = self.getPositions(objects,row,col)
                        #define the floor object we want
                        obj = objects[row+layers][col+layers][objIndex]
                        
                        #create the intervals
                        pos1 = obj.posInterval(self.pieceSpeed*.2,Point3(-30,15,-10),startPos=Point3(-50,5,-2.5)) #final in place
                        pos2 = obj.posInterval(self.pieceSpeed*.2,Point3(-10,20,-5),startPos=Point3(-30,15,-10)) #final in place
                        pos3 = obj.posInterval(self.pieceSpeed*.2,mazePoint,startPos=Point3(-10,20,-5)) #final in place
                        roterval = obj.hprInterval(self.pieceSpeed*.8,Point3(0,0,0),startHpr=Point3(randint(0,360),randint(0,360),randint(0,360)))
                        #create the sequence
                        pieceSequence = Sequence(Wait(self.pieceDelay*count+delay),Parallel(Sequence(pos1,pos2,pos3),roterval))            
                        #play this sequence
                        pieceSequence.start()
                        count+=1
                        
        #wallcol creation sequence!
        if seq == 3:
    
            #set sequence variables for all floor pieces!
            count = 0
            for col in xrange(-layers,layers+1+colAdd):
                for row in xrange(-layers,layers+1+rowAdd,1):
                    #get the type of object list and get the requirements of each respectively:
                    if( ((row != 0 or col != 0) and objects == self.floorPiece) or 
                        ((wallCol[row+layers][col+layers-colAdd][0] == 1) and objects == self.wallCol) or
                        ((wallRow[row+layers-rowAdd][col+layers][0] == 1) and objects == self.wallRow) ):
                        #get to and from places: (based on objects)
                        mazePoint,awayPoint = self.getPositions(objects,row,col)
                        #define the floor object we want
                        obj = objects[row+layers][col+layers][objIndex]
                        
                        #create the intervals
                        pos1 = obj.posInterval(self.pieceSpeed*.25,Point3(-8.7,7.4,5.5),startPos=Point3(-12.7,8.8,.4)) #final in place
                        rot1 = obj.hprInterval(self.pieceSpeed*.25,Point3(3.6,-45.3,-15.1),startHpr=Point3(19.3,-53.2,-33.4)) #final in place
                        
                        pos2 = obj.posInterval(self.pieceSpeed*.25,Point3(-4.8,4.8,8.1),startPos=Point3(-8.7,7.4,5.5)) #final in place
                        rot2 = obj.hprInterval(self.pieceSpeed*.25,Point3(-2.1,-22.5,-11.3),startHpr=Point3(3.6,-45.3,-15.1)) #final in place
                        
                        pos3 = obj.posInterval(self.pieceSpeed*.25,Point3(-.8,2.6,7.6),startPos=Point3(-4.8,4.8,8.1)) #final in place
                        rot3 = obj.hprInterval(self.pieceSpeed*.25,Point3(29.4,-29.3,-22.7),startHpr=Point3(-2.1,-22.5,-11.3)) #final in place
                        
                        pos4 = obj.posInterval(self.pieceSpeed*.25,mazePoint,startPos=Point3(-.8,2.6,7.6)) #final in place
                        rot4 = obj.hprInterval(self.pieceSpeed*.3,Point3(0,0,0),startHpr=Point3(29.4,-29.3,-22.7)) #final in place
                
                        #create the sequence
                        pieceSequence = Sequence(Wait(self.pieceDelay*count+delay),Parallel(pos1,rot1),Parallel(pos2,rot2),Parallel(pos3,rot3),Parallel(pos4,rot4))            
                        #play this sequence
                        pieceSequence.start()
                        count+=1

        #wallrow creation sequence!
        if seq == 4:
    
            #set sequence variables for all floor pieces!
            count = 0
            for col in xrange(-layers,layers+1+colAdd):
                for row in xrange(-layers,layers+1+rowAdd,1):
                    #get the type of object list and get the requirements of each respectively:
                    if( ((row != 0 or col != 0) and objects == self.floorPiece) or 
                        ((wallCol[row+layers][col+layers-colAdd][0] == 1) and objects == self.wallCol) or
                        ((wallRow[row+layers-rowAdd][col+layers][0] == 1) and objects == self.wallRow) ):
                        #get to and from places: (based on objects)
                        mazePoint,awayPoint = self.getPositions(objects,row,col)
                        #define the floor object we want
                        obj = objects[row+layers][col+layers][objIndex]
                        
                        #create the intervals
                        pos1 = obj.posInterval(self.pieceSpeed*.25,Point3(12.3,-4.2,4.8),startPos=Point3(16.1,-.9,0)) #final in place
                        rot1 = obj.hprInterval(self.pieceSpeed*.25,Point3(70.9,23,23.5),startHpr=Point3(107.3,29.7,30.3)) #final in place
                        
                        pos2 = obj.posInterval(self.pieceSpeed*.25,Point3(6.6,-5.9,7.4),startPos=Point3(12.3,-4.2,4.8)) #final in place
                        rot2 = obj.hprInterval(self.pieceSpeed*.25,Point3(-50.7,-4.2,-19.2),startHpr=Point3(70.9,23,23.5)) #final in place
                        
                        pos3 = obj.posInterval(self.pieceSpeed*.25,Point3(2.3,-2.6,6.4),startPos=Point3(6.6,-5.9,7.4)) #final in place
                        rot3 = obj.hprInterval(self.pieceSpeed*.25,Point3(14,-22.7,-34),startHpr=Point3(-50.7,-4.2,-19.2)) #final in place
                        
                        pos4 = obj.posInterval(self.pieceSpeed*.25,mazePoint,startPos=Point3(2.3,-2.6,6.4)) #final in place
                        rot4 = obj.hprInterval(self.pieceSpeed*.3,Point3(0,0,0),startHpr=Point3(14,-22.7,-34)) #final in place
                
                        #create the sequence
                        pieceSequence = Sequence(Wait(self.pieceDelay*count+delay),Parallel(pos1,rot1),Parallel(pos2,rot2),Parallel(pos3,rot3),Parallel(pos4,rot4))            
                        #play this sequence
                        pieceSequence.start()
                        count+=1

        ######################################

        #move everything that is not part of maze away from maze
        count = 0
        for col in xrange(-layers,layers+1+colAdd):
            for row in xrange(-layers,layers+1+rowAdd,1):
                if ( ((wallCol[row+layers][col+layers-colAdd][0] == 0) and objects == self.wallCol) or
                     ((wallRow[row+layers-rowAdd][col+layers][0] == 0) and objects == self.wallRow) ):
                    #get to and from places: (based on objects)
                    mazePoint,awayPoint = self.getPositions(objects,row,col)
                    #define the floor object we want
                    obj = objects[row+layers][col+layers][objIndex]
                    #create the intervals
                    interval = obj.posInterval(self.pieceSpeed,awayPoint,startPos=awayPoint)
                    #create the sequence
                    pieceSequence = Sequence(Wait(self.pieceDelay*count+delay),interval)            
                    #play this sequence
                    pieceSequence.start()
                    count+=1
        
                        

    #a nice little helper function to get to and away points (for maze objects)
    def getPositions(self,objects,row,col):
        #universal maze variables
        layers = self.layers ; sep = self.sep    
        
        #random x; random y
        randx = random()*self.spread-self.spread*.5
        randy = random()*self.spread-self.spread*.5
                
        #get to and from places: (based on objects)
        if objects == self.floorPiece:
            mazePoint = Point3(row*sep,col*sep,0)
            awayPoint = Point3(randx, randy, -50)
        if objects == self.wallRow:
            mazePoint = Point3(row*sep,col*sep-sep*.5,0)
            awayPoint = Point3(randx, randy, 50)
        if objects == self.wallCol:
            mazePoint = Point3(row*sep-sep*.5,col*sep,0)
            awayPoint = Point3(randx, randy, 50)            
        return (mazePoint,awayPoint)
    
    

    #now do the thing that moves pictures in place
    def startImageSequence(self,seq=0,delay=0):
        #universal maze variables
        layers = self.layers ; sep = self.sep    
        
        #frame creation sequence
        if seq == 0 : 
            
            #first half go on col walls...
            count = 0
            for index in xrange(len(self.myPictures)):
                
                #define the pictures that we want
                picture = self.myPictures[index][3]
                
                #get the final position and orientation!!1!
                if index < len(self.myPictures)/2: #col pictures 
                    if len(self.colPositions)>0: #if there is space available, then place picture
                        #get positions
                        position = choice(self.colPositions)
                        row,col = position[0]; orientation = position[1]            
                        self.myPictures[index][5] = (row*sep-sep*.5,col*sep,self.wallHeight*.5)
                        self.myPictures[index][6] = (180*orientation+90,0,0)
                        self.colPositions.remove(position)
                    else:
                        self.myPictures[index][5] = (0,0,50)
                        self.myPictures[index][6] = (0,0,0)
                        
                #these are row pictures 
                else: 
                    if len(self.rowPositions)>0: #if there is space available, then place picture
                        position = choice(self.rowPositions)
                        row,col = position[0]; orientation = position[1]
                        self.myPictures[index][5] = (row*sep,col*sep-sep*.5,self.wallHeight*.5)
                        self.myPictures[index][6] = (180*orientation,0,0)
                        self.rowPositions.remove(position)
                    else:
                        self.myPictures[index][5] = (0,0,50)
                        self.myPictures[index][6] = (0,0,0)
                        
                #create the intervals
                randx = random()*self.spread-self.spread*.5
                randy = random()*self.spread-self.spread*.5
                intervalPos = picture.posInterval(self.pieceSpeed,self.myPictures[index][5], startPos = Point3(randx,randy,50))
                intervalRot = picture.hprInterval(self.pieceSpeed*1.05,self.myPictures[index][6], startHpr = Point3(randint(0,360),randint(0,360),randint(0,360)))
                
                #create the sequence
                pieceSequence = Sequence(Wait(.5*self.pieceDelay*count+delay),Parallel(intervalPos,intervalRot))       
                #play this sequence
                pieceSequence.start()
                count+=1
        
        #frame destruction sequence
        if seq == 1 : 
            
            #first half go on col walls...
            count = 0
            for index in xrange(len(self.myPictures)):
                
                #define the pictures that we want
                picture = self.myPictures[index][3]
                
                #get initial rotation and position
                fromPos = self.myPictures[index][5]
                fromRot = self.myPictures[index][6]
                
                #create the intervals
                intervalPos = picture.posInterval(self.pieceSpeed,Point3(0,0,50),startPos=fromPos)
                intervalRot = picture.hprInterval(self.pieceSpeed,Point3(randint(0,360),randint(0,360),randint(0,360)),startHpr=fromRot)
                
                #create the sequence
                pieceSequence = Sequence(Wait(.3*self.pieceDelay*count+delay),Parallel(intervalPos,intervalRot))       
                #play this sequence
                pieceSequence.start()
                count+=1
        
    
        
#---------------------------------------------------------------------------#
                
    #based off of treeform's level loading script - heavily modified by me
    def loadLevel(self):
        
        #load level cylinder and floor pieces
        cylinder = loader.loadModel('meshes/cylinder')
        self.propertizeObject(cylinder)#, tex = self.grey)
        
        #load main balloon
        balloon = loader.loadModel('meshes/balloon')
        self.propertizeObject(balloon, pos = (0,0,0.2),scale = 2,
                              tex = self.balloontx)
 
        #universal maze variables
        layers = self.layers ; sep = self.sep
        #create the colliders! (more like load, rather...)
        self.createWallColliders()
        
        #create all floor_pieces
        floorPiece = self.floorPiece
        for col in xrange(-layers,layers+1):
            for row in xrange(-layers,layers+1,1):
                if(row != 0 or col != 0):
                    #add object
                    floorPiece[row+layers][col+layers][0] = loader.loadModel('meshes/floor_piece')
                    self.propertizeObject(floorPiece[row+layers][col+layers][0],
                                          pos=(0,0,-50),#pos = (row*sep,col*sep,0),
                                          useLight = True) 
        
        #create wall rows 
        wallRow = self.wallRow
        for col in xrange(-layers,layers+2):
            for row in xrange(-layers,layers+1,1):            
                
                #if standard piece:
                if (row != 0 or col != -layers):
                    
                    #add object (regardless of maze)
                    wallRow[row+layers][col+layers][1] = loader.loadModel('meshes/wall_row')
                    self.propertizeObject(wallRow[row+layers][col+layers][1],
                                          pos = (0,0,100),#pos=(row*sep,col*sep-sep*.5,0),
                                          useLight = True)
                    #add collider
                    wallRow[row+layers][col+layers][2] = wallRow[row+layers][col+layers][1].attachNewNode(self.wallRowCollider)
                #if door_piece:
                else:
                    #add door_wall object
                    wallRow[row+layers][col+layers][1] = loader.loadModel('meshes/door_wall')
                    self.propertizeObject(wallRow[row+layers][col+layers][1],
                                          useLight = True)
                    #add door wall object
                    door_frame = loader.loadModel('meshes/door_frame')
                    self.propertizeObject(door_frame,
                                          tex = self.door_tex,
                                          useLight = True)
                    door_frame.reparentTo(wallRow[row+layers][col+layers][1])
                    #add door object
                    self.door = loader.loadModel('meshes/door')
                    self.propertizeObject(self.door,
                                          tex = self.door_tex,
                                          pos = (.23,0,0),
                                          useLight = True)
                    self.door.reparentTo(door_frame)
                    #position wall
                    wallRow[row+layers][col+layers][1].setPos(0,0,100)      
                    
                    #add collider
                    #wallRow[row+layers][col+layers][2] = wallRow[row+layers][col+layers][1].attachNewNode(self.wallRowCollider)
                
        #create wall cols
        wallCol = self.wallCol
        for row in xrange(-layers,layers+2):
            for col in xrange(-layers,layers+1,1):    
                #add object
                wallCol[row+layers][col+layers][1] = loader.loadModel('meshes/wall_col')
                self.propertizeObject(wallCol[row+layers][col+layers][1],
                                      pos = (0,0,100),#pos=(row*sep-sep*.5,col*sep,0),
                                      useLight = True)
                #add collider
                wallCol[row+layers][col+layers][2] = wallCol[row+layers][col+layers][1].attachNewNode(self.wallColCollider)
        
        #apply random maze textures to wall cols and rows
        self.applyRandomMazeTexture()
        
        #create a frame and picture for every item in myPictures
        #ref: 0 = texture, 1 = path, 2 = image size, 3 = frame object, 4 = picture object
        for index in xrange(len(self.myPictures)):
            #load frame object
            self.myPictures[index][3] = loader.loadModel('meshes/frame') 
            self.propertizeObject(self.myPictures[index][3],tex = self.frame_tex,pos=(0,0,50))
            #load picture object
            self.myPictures[index][4] = loader.loadModel('meshes/picture')
            self.propertizeObject(self.myPictures[index][4],tex = self.myPictures[index][0])
            #attach picture to frame
            self.myPictures[index][4].reparentTo(self.myPictures[index][3])
            #scale frame and picture accordingly
            scale = 1.3
            sx,sy = self.myPictures[index][2]    
            self.myPictures[index][3].setSz(scale*sy/sx)
            self.myPictures[index][3].setSx(scale)        
     
     
    #function to create wall collider pieces
    def createWallColliders(self):
        #create all wall colliders
        wallWidth = 0.2 ; wallHeight = 1.2 ; wallLength = 1.2
        self.wallHeight = wallHeight
        
        #create wall row collider
        self.wallRowCollider = CollisionNode('wallColCollider')
        #front collider
        self.wallRowCollider.addSolid( CollisionPolygon(Point3(wallLength*.5,-wallWidth*.5, 0),
                                                   Point3(wallLength*.5,-wallWidth*.5, wallHeight),
                                                   Point3(-wallLength*.5,-wallWidth*.5, wallHeight),
                                                   Point3(-wallLength*.5,-wallWidth*.5, 0)))
        #back collider
        self.wallRowCollider.addSolid( CollisionPolygon(Point3(-wallLength*.5, wallWidth*.5, 0),
                                                   Point3(-wallLength*.5, wallWidth*.5, wallHeight),
                                                   Point3(wallLength*.5, wallWidth*.5, wallHeight),
                                                   Point3(wallLength*.5, wallWidth*.5, 0)))
        #left collider
        self.wallRowCollider.addSolid( CollisionPolygon(Point3(-wallLength*.5, -wallWidth*.5, 0),
                                                   Point3(-wallLength*.5, -wallWidth*.5, wallHeight),
                                                   Point3(-wallLength*.5, wallWidth*.5, wallHeight),
                                                   Point3(-wallLength*.5, wallWidth*.5, 0)))
        #right collider
        self.wallRowCollider.addSolid( CollisionPolygon(Point3(wallLength*.5, wallWidth*.5, 0),
                                                   Point3(wallLength*.5, wallWidth*.5, wallHeight),
                                                   Point3(wallLength*.5, -wallWidth*.5, wallHeight),
                                                   Point3(wallLength*.5, -wallWidth*.5, 0)))
        
        #create wall col collider
        self.wallColCollider = CollisionNode('wallColCollider')
        #front collider
        self.wallColCollider.addSolid( CollisionPolygon(Point3(-wallWidth*.5, -wallLength*.5, 0),
                                                   Point3(-wallWidth*.5, -wallLength*.5, wallHeight),
                                                   Point3(-wallWidth*.5, wallLength*.5, wallHeight),
                                                   Point3(-wallWidth*.5, wallLength*.5, 0)))
        #back collider
        self.wallColCollider.addSolid( CollisionPolygon(Point3(wallWidth*.5, wallLength*.5, 0),
                                                   Point3(wallWidth*.5, wallLength*.5, wallHeight),
                                                   Point3(wallWidth*.5, -wallLength*.5, wallHeight),
                                                   Point3(wallWidth*.5, -wallLength*.5, 0)))
        #right collider
        self.wallColCollider.addSolid( CollisionPolygon(Point3(-wallWidth*.5, wallLength*.5, 0),
                                                   Point3(-wallWidth*.5, wallLength*.5, wallHeight),
                                                   Point3(wallWidth*.5, wallLength*.5, wallHeight),
                                                   Point3(wallWidth*.5, wallLength*.5, 0)))
        #left collider
        self.wallColCollider.addSolid( CollisionPolygon(Point3(wallWidth*.5, -wallLength*.5, 0),
                                                   Point3(wallWidth*.5, -wallLength*.5, wallHeight),
                                                   Point3(-wallWidth*.5, -wallLength*.5, wallHeight),
                                                   Point3(-wallWidth*.5, -wallLength*.5, 0)))

    #quick shortcut to apply maze tex to every wall!
    def applyRandomMazeTexture(self):
        
        #make sure that we habve at least one texture for our maze:
        if len(self.maze_tex) > 0:
        
            #pick some random textures
            walltex = choice(self.maze_tex)
            floortex = choice(self.maze_tex)
            
            #universal maze variables
            layers = self.layers ; sep = self.sep    
            
            #create all floor_pieces
            floorPiece = self.floorPiece
            for col in xrange(-layers,layers+1):
                for row in xrange(-layers,layers+1,1):
                    if(row != 0 or col != 0):
                        floorPiece[row+layers][col+layers][0].setTexture(floortex[0])
                        
            #create wall rows 
            wallRow = self.wallRow
            for col in xrange(-layers,layers+2):
                for row in xrange(-layers,layers+1,1):            
                    wallRow[row+layers][col+layers][1].setTexture(walltex[0])
                    
            #create wall cols
            wallCol = self.wallCol
            for row in xrange(-layers,layers+2):
                for col in xrange(-layers,layers+1,1):    
                    wallCol[row+layers][col+layers][1].setTexture(walltex[0])
                    
    
    #quick shortcut to apply lots of panda features at once
    def propertizeObject(self,obj,pos=(0,0,0),rot=(0,0,0),scale=1.0,
                   mat=None,tex=None,useLight = True,useFog=True):
        #attach object to renderer
        obj.reparentTo(render)
        #set transform attributes
        posx,posy,posz = pos;
        rotx,roty,rotz = rot;
        obj.setPos(posx,posy,posz)
        obj.setHpr(rotx,roty,rotz)
        obj.setScale(scale)
        #set appearance
        if mat != None: obj.setMaterial(mat)
        if tex != None: obj.setTexture(tex)
        if useLight == False:
            obj.setLightOff()
        if useFog == True:
            obj.setFog(self.fog)
        
#---------------------------------------------------------------------------#
    
    #treeform's collision preparer:
    def initCollision(self):
        base.cTrav = CollisionTraverser() #initialize traverser
        self.pusher = CollisionHandlerPusher() #initialize pusher
    
    #used treeform's code here:
    def initPlayer(self,playerSpeed=1.0,playerStartPos=(0,0,0)):
        #load player (sphere)
        self.player = loader.loadModel('meshes/sphere')
        self.player.hide()
        self.propertizeObject(self.player, pos = playerStartPos,scale = .05)
        self.playerZ = playerStartPos[2]
        
        #create a collision solid for the player
        cNode = CollisionNode('player')
        cNode.addSolid(CollisionSphere(0,0,0,1.0))
        playerC = self.player.attachNewNode(cNode)
        playerC.show()
        base.cTrav.addCollider(playerC,self.pusher)
        self.pusher.addCollider(playerC,self.player, base.drive.node())
        #set controls
        walkSpeed = playerSpeed
        strifeSpeed = playerSpeed*2.0
        Forward = Vec3(0,walkSpeed*2,0)
        Back = Vec3(0,-walkSpeed,0)
        Left = Vec3(-strifeSpeed,0,0)
        Right = Vec3(strifeSpeed,0,0)
        Stop = Vec3(0)
        #set WSAD controls:
        self.walk = Stop; self.strife = Stop
        self.accept( "s" , self.__setattr__,["walk",Back] )
        self.accept( "w" , self.__setattr__,["walk",Forward])
        self.accept( "s-up" , self.__setattr__,["walk",Stop] )
        self.accept( "w-up" , self.__setattr__,["walk",Stop] )
        self.accept( "a" , self.__setattr__,["strife",Left])
        self.accept( "d" , self.__setattr__,["strife",Right] )
        self.accept( "a-up" , self.__setattr__,["strife",Stop] )
        self.accept( "d-up" , self.__setattr__,["strife",Stop] )
        #add escape key so user exits upon escape press
        self.accept('escape', lambda: sys.exit())
        #add key to access topview
        self.view=0
        self.accept('tab', self.__setattr__,["view",1])
        self.accept('tab-up', self.__setattr__,["view",0])
        #right mouseclick FOV zoom
        self.zoom=120
        self.accept( "mouse3", self.__setattr__,["zoom",60] )
        self.accept( "mouse3-up", self.__setattr__,["zoom",120] )
        #left mouse click maze activation!
        self.activate=0
        self.accept( "mouse1", self.__setattr__,["activate",1])
        self.accept( "mouse1-up", self.__setattr__,["activate",0])
        
    def move(self,task):
        #get time update speed
        self.deltaTime = task.time - self.oldTime
        
        # mouse
        md = base.win.getPointer(0)
        x = md.getX(); y = md.getY()
        maxAngle = 90.0
        if base.win.movePointer(0, base.win.getXSize()/2, base.win.getYSize()/2):
            #rotate!
            #using clamp code from http://stackoverflow.com/questions/9775731/clamping-floating-numbers-in-python)
            if self.view == 0:
                self.player.setH(self.player.getH() -  (x - base.win.getXSize()/2)*0.1)
                base.camera.setP(max(min(base.camera.getP() - (y - base.win.getYSize()/2)*0.1, maxAngle),-maxAngle))
            else: 
                self.topView.setH(self.topView.getH() -  (x - base.win.getXSize()/2)*0.1)
                self.topView.setP(max(min(self.topView.getP() - (y - base.win.getYSize()/2)*0.1, maxAngle),-maxAngle))    
                base.camera.setP(0)
                
        #lock player z position
        self.player.setZ(self.playerZ)
        
        #attach light to player
        self.plnp.setPos(self.player.getPos())

        #clamp player's position to bounds within maze after first pass
        layers = self.layers ; sep = self.sep
        if(self.firstPass == False and self.doorOpen == False):
            self.player.setX(max(min(self.player.getX(),layers*sep+sep*.5-.25),-layers*sep-sep*.5+.25))
            self.player.setY(max(min(self.player.getY(),layers*sep+sep*.5-.25),-layers*sep-sep*.5+.25))

        #change view
        if self.view == 0:
            #assign camera to player
            base.camera.reparentTo(self.player)
            # move where the keys set it if player view
            self.player.setPos(self.player,self.walk*globalClock.getDt())
            self.player.setPos(self.player,self.strife*globalClock.getDt())    
            self.player.hide()
        else:
            #assign camera to top view
            base.camera.reparentTo(self.topView)
            self.player.show()
            
        #set smooth mouse zoom
        if self.currentFocus - self.zoom > .1:
            self.currentFocus -= 200.0*self.deltaTime
        if self.currentFocus - self.zoom < -.1:
            self.currentFocus += 200.0*self.deltaTime
        base.camLens.setFov(self.currentFocus)
        
        #update the time
        self.oldTime = task.time
        
        return task.cont

#---------------------------------------------------------------------------#
        
    def  initCamera(self,fov,near,far,topHeight):
        #create top view
        self.topView = loader.loadModel('meshes/sphere')
        self.topView.hide()
        self.propertizeObject(self.topView, pos = (0,0,topHeight),scale = .05)
        self.topView.setHpr(0,0,0)
        
        #initialize camera
        base.camera.reparentTo(self.topView)
        base.camera.reparentTo(self.player)    
        base.camera.setPos(0,0,0)
        self.currentFocus = fov
        base.camLens.setNear(near)
        base.camLens.setFar(far)        
        base.disableMouse()
        
        
    def shakeCamera(self,task):
        #if camera is attached to player
        if self.view == 0:
            #turn walk sounds on and off
            if self.walk!=Vec3(0) or self.strife!=Vec3(0):
                #play walk sound
                if self.walkSound.status() == self.walkSound.READY:
                    self.walkSound.play()
            else:
                #stop walk sound
                self.walkSound.stop()
            #universal camera shake
            base.camera.setPos( .3*cos(1*task.time),0,.15*cos(.15*task.time))
        else:
            self.walkSound.stop()
        
        return task.cont

#---------------------------------------------------------------------------#

    #maze creation!
    def createMazeMuseum(self):
        
        #universal maze variables
        layers = self.layers ; sep = self.sep    
        floorPiece = self.floorPiece
        wallRow = self.wallRow; wallCol = self.wallCol
        
        #create a new maze!
        self.generateMaze(layers = self.layers,sep = self.sep,
                          pieceSpeed = self.pieceSpeed,
                          pieceDelay=self.pieceDelay,
                          pieceSpread = self.spread,
                          firstMaze = False)
        
        #close door (if open)
        if self.doorOpen == True:
            
            self.doorOpen = False
            interval = self.door.hprInterval(1,Point3(0,0,0),startHpr=(90,0,0))
            Sequence(interval).start()
                    
        #----DESTRUCTION!!!----#
        
        #if not the first pass:
        if(self.firstPass==False):
        
            #1) destroy floor pieces!
            self.startSequence(objects = self.floorPiece,objIndex = 0,seq = 1,delay = 0)
            
            #2) destroy wall pieces! (in parallel)
            self.startSequence(objects = wallRow,objIndex = 1,seq = 1,delay = 0)
            self.startSequence(objects = wallCol,objIndex = 1,seq = 1,delay = 0)
            
            #3) destroy pictures!
            self.startImageSequence(seq=1,delay=0)

        #----CREATION!!!----#
        
        #1) create floor pieces!
        self.startSequence(objects = self.floorPiece,objIndex = 0,seq = 2,delay = 5-int(self.firstPass)*5)
        
        #2) create wall pieces! (in parallel)
        self.startSequence(objects = wallRow,objIndex = 1,seq = 3,delay = 5-int(self.firstPass)*5)
        self.startSequence(objects = wallCol,objIndex = 1,seq = 4,delay = 5-int(self.firstPass)*5)
               
        #3) create pictures!
        self.startImageSequence(seq=0,delay=5-int(self.firstPass)*5)

        #we have now done at least the first pass
        self.firstPass = False
        
#---------------------------------------------------------------------------#
    #game loop to allow player to click balloon
    def balloonGame(self, task):

        #get distance:
        distance = (self.player.getX()**2.0 + self.player.getY()**2.0 )**0.5

        #if player is close enough to balloon
        if distance < 0.5:
            
            #make sure we are ready to begin the creation process
            if self.creationReady==True:
                
                #show user ballooon manual
                self.showBalloonText = 1
                
                #get click:
                if self.activate == 1:
                    
                    #begin process for building museum
                    self.creationReady = False
                    self.creationStart = task.time
                    self.createMazeMuseum()
                    
                    #randomize background color
                    self.newBackgroundColor = VBase4(random(),random(),random(),1)
                    #play switch sound
                    self.switchSound.play()
                    #play next music
                    if len(self.myMusic)>0:
                        #begin next music
                        self.myMusic[self.currentMusic][0].play()
                        #stop all other music
                        for music in xrange(len(self.myMusic)):
                            if music != self.currentMusic:
                                self.myMusic[music][0].stop()
                        #set next music
                        self.currentMusic += 1
                        if self.currentMusic >= len(self.myMusic): self.currentMusic = 0 #wrap around
        
            #we are in the midst of the creation stage:
            else:
                self.showBalloonText = 0
                        
        #if player is not close enough to balloon
        else:
            self.showBalloonText = 0
            
        #creation completed:
        if task.time - self.creationStart > 10.0: self.creationReady = True

        
        #switch maze texture during middle
        if task.time - self.creationStart > 6.0 and task.time - self.creationStart < 6.1 and self.firstPass == False: self.applyRandomMazeTexture()
        
        
        
        #get door distance:
        layers = self.layers ; sep = self.sep
        doorDistance = (self.player.getX()**2.0 + (self.player.getY()-(-layers*sep-sep*.5+.25))**2.0 )**0.5
        
        #also use the door to exit!
        if doorDistance < 0.5 and self.firstPass == False:
            
            #make sure the door exists
            if self.doorOpen==False:
                
                #show user ballooon manual
                self.showDoorText = 1
                
                #get click:
                if self.activate == 1:
                    
                    #change the background color
                    self.newBackgroundColor = VBase4(.9,.9,.9,1)
                    
                    #open door
                    self.doorOpen = True
                    interval = self.door.hprInterval(1,Point3(90,0,0),startHpr=(0,0,0))
                    Sequence(interval).start()
                    
                    #play door sound
                    self.doorSound.play()
                    
            else:
                self.showDoorText = 0
                
        else:
            self.showDoorText = 0
                
        
        #continue the loop
        return task.cont
        
#run the game
LifeInABox()
render.setShaderAuto()
run() 
