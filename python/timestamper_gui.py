import os,sys

import basis
import config

import wx			#THE wxPython WINDOW LIBRARY !
import wx.grid			#the excel-like GRID is a submodule

MainWin = None                  #MAIN WINDOW (toplevel)
PathLine = None                 #the TOP LINE showing the current PATH
FatLabel = None                 #close to the path: is it FAT or NTFS ?
TableGrid = None                #THE CORE: the GRID for 1 directory
MainopText = None               #MAIN OPERATION preview left of the OP Buttons

#----------------------------------------------------------------------
#Simple ERROR-DIALOGS, ubiquitous in my code...

MSG_INFO  = 0
MSG_WARNG = 1
MSG_ERROR = 2
MSG_FATAL = 3

MSG_Levelnames  = [ "OKAY", "WARNING", "ERROR", "FATAL" ]					#the TEXT Label
MSG_Levelicons  = [ wx.ICON_INFORMATION, wx.ICON_EXCLAMATION, wx.ICON_ERROR, wx.ICON_ERROR ]	#the Icon for wx.MessageDialog

def LogMessageDialog(level, message):
  "simple OK-MESSAGE with Error levels"
  dlg = wx.MessageDialog(MainWin, message,
                         MSG_Levelnames[level],
                         wx.OK | MSG_Levelicons[level])
  dlg.ShowModal()
  dlg.Destroy()

def QuestionDialog(level, message, yesdefault):
  "YES/NO Question with Error levels"
  dlg = wx.MessageDialog(MainWin, message,
                         MSG_Levelnames[level],
                         wx.YES_NO
                         | ifop(yesdefault,wx.YES_DEFAULT,wx.NO_DEFAULT)
                         | MSG_Levelicons[level])
  ret = (dlg.ShowModal() == wx.ID_YES)
  dlg.Destroy()
  return ret

#----------------------------------------------------------------------
#important: THE MAIN COLUMN DESCRIPTION FOR THE GUI TABLE

  ##FUTURE: Columns might be picked and sorted in a GUI dialog

def colourMaker(coltuple):
  """little factory function to give to basis.py
    which knows nothing about wxPython but wants to fully prepare Colour values"""
  return wx.Colour(*coltuple)

basis.CellObject.colourMaker = colourMaker

class ColumnDescription:
  """convenience class for better readability of Column Descriptions;
    just a collection of data with no functionality"""
  
  def __init__(self, name,heading,width,align,colour, active,  isstamp,  proxyobj, posttransfer=False):
    
      #the name of this column, used as a key when asking FileData for its col_... members
    self.name = name
      #most columns will just capitalize their name bytes -> Bytes for GUI Headings
    self.heading = heading or name.capitalize()

      #desired width (SetColSize)
    self.width = width
    
      #alignment of contents: L<- (C) ->R
    self.align = align
    
      #column colour (used to set debug columns GREY240)
    self.colour = colour
    
      #switching columns on and off is better than commenting their lines
    self.active = active
    
      #--------------------
      #for TIMESTAMPS 1.is this a timestamp ?
      #  2.if it is, does it accept transfer input ?
    self.isstamp =      isstamp
    self.posttransfer = posttransfer
      #can be a flag:
      #  FALSE: not allowed as transfer target
      #  TRUE:  allowed, no special handling
      #or a function:
      #  function <- transfer allowed, call this when done
    
      #--------------------
      #Column Descriptions must supply a PROXY OBJECT that will be used for sorting and formatting
      #if the file value here is not a full CellObject but a simple data type
      #(mandatory because subdirs will do so)
    assert proxyobj, "all COLUMNS must supply a CellObjectProxy for their properties"
    assert isinstance(proxyobj,basis.CellObjectProxy), "the proxy object must be a CellObjectProxy descendant"
    
    self.proxyobj = proxyobj

  #a small optimisation, some proxies are used many times...
cobjProxyString = basis.CellObjectProxyString()
cobjProxyStamp  = basis.CellObjectProxyStamp()

def DirWriteMyFile():
  TableGrid.WriteMyFile()

#ALL descriptions, .active and inactive, will only be used filtered to ColumnDescriptions
stampwidthbig  = 125
stampwidthsmall = 65

GREY240 = wx.Colour(240,240,240)

ColumnDescriptions_ALL = [
    #SPECIAL COLUMN: mark files for operations
  ColumnDescription("mark",  "",         40,"C",None, True,  False, basis.CellObjectProxyMarker()),
  
    #simple columns, not timestamps
  ColumnDescription("ftype", "Typ",      40,"C",None, True,  False, cobjProxyString),
  ColumnDescription("name",  None,      250,"L",None, True,  False, cobjProxyString),
  ColumnDescription("extn", "Extension", 60,"L",None, True,  False, cobjProxyString),
  ColumnDescription("bytes", None,       80,"R",None, True,  False, basis.CellObjectProxyBytes()),
  
    #VERY SPECIAL COLUMN, starts empty, used for Operation Output (currently Operation ANALYSE)
  ColumnDescription("out",  "***",       20,"R",None, True,  False, basis.CellObjectProxyOutput()),
  
  #===== LOW LEVEL STAMPS =====
    #1.THE FIRST TIMESTAMP starts off with 4 possible columns
    #  1.SOURCE: mtime or ctime (for test purposes)
    #  2.TIMEZONE: Local or GMT (for test purposes)
    #=>SINGLE CHOICE: Linux Display (ls, nautilus...) ist mtime in local time
  ColumnDescription("ts1_modloc", "PY local", stampwidthsmall,"R",GREY240, True,  True, cobjProxyStamp, True),
  ColumnDescription("ts1_modgmt", "PY gmt",   stampwidthsmall,"R",GREY240, True,  True, cobjProxyStamp, True),
  
    ##for DEBUG: <hours> value raw from st_mtime without any conversion
  ColumnDescription("rawhours", None,  40,"R",GREY240, False, False, basis.CellObjectProxyInt()),
    ##for DEBUG: <dst> value from time.localtime
  ColumnDescription("isdst",    "DST", 40,"R",None,    True,  False, basis.CellObjectProxyInt()),
  
    ##ctime is pointless, was for Debugging, inactive
  ColumnDescription("ts1_crtloc", None,        stampwidthsmall,"R",GREY240, False, True, cobjProxyStamp, False),
  ColumnDescription("ts1_crtgmt", None,        stampwidthsmall,"R",GREY240, False, True, cobjProxyStamp, False),
  
  #===== LINUX & WINDOWS STAMPS =====
    #2.LINUX would not need extra columns while running on linux
    #  as PYTHON ts1 == LINUX ts2 but running on Windows it does
  ColumnDescription("ts2_linux",  "Linux",     stampwidthbig,  "R",None, True,  True, cobjProxyStamp, True),
  
    #3.WINDOWS is worse than anticipated,
    #* old Windows will always apply the dst offset depending on the current time (eg. WINTER)
    #  even to files that where in another part of the year (eg. SUMMER)
    #
    #* new Windows follows Linux and Mac in that DST is only applied to files where
    #  DST was actually on, which is much better, BUT...
    #  1.BUT: only in Windows Explorer, the DIR command now shows different times (!)
    #  2.BUT: that means there is now a third way to store stamps in the FILESYSTEM
    #    it used to be a)UTC and b)LOCAL TIME including Timezone and DST (for Windows on FAT)
    #    now there is also c)LOCAL TIME with only Timezone but no DST offset
  ColumnDescription("ts3_winnew", "Win new",   stampwidthbig,  "R",None, True,  True, cobjProxyStamp, True),
  ColumnDescription("ts3_winold", "Win old",   stampwidthbig,  "R",None, True,  True, cobjProxyStamp, True),
  
  #===== SPECIAL STAMPS =====
    #4.FROM FILENAME: source only, not destination
  ColumnDescription("ts4_fname","From Fname",    stampwidthbig,  "R",None, True,  True, cobjProxyStamp, False),
  
    #5.IN PRIVATE DATA FILE, read and written by the directory Object
  ColumnDescription("ts5_datafile","My Datafile",stampwidthbig,  "R",None, True,  True, cobjProxyStamp, DirWriteMyFile),
]

#COLUMN DESCRIPTIONS filtered to active ones, this is THE MAIN GUI DESCRIPTION !
ColumnDescriptions = [cd for cd in ColumnDescriptions_ALL if cd.active]

#FileData need to assert they supply all of columns
AllColumnNames = [cd.name for cd in ColumnDescriptions]
  ##LATER: FileData do not need to assert for inactive columns,
  ##  but a warning might be nice instead
  ##  (would have to iterate _ALL and supply both .name and .active)

#Additional Structure: indexed by name => IDX and full COLDESC Object
ColDescDict = {cd.name:(cdidx,cd) for cdidx,cd in enumerate(ColumnDescriptions)}


#----------------------------------------------------------------------
#The CENTRAL Widget: the GRID displaying the current directory

class StamperDirTable (wx.grid.Grid):
  #my main (and only) basis.DirectoryData object
  dirdata = None
  
  def __init__(self, parent):
    #my parent the GRID object
    wx.grid.Grid.__init__(self, parent,-1)
    
    #COLUMNS are fix in basis, ROWS will change right away
    self.CreateGrid(1, len(ColumnDescriptions))
    
    for colnum,coldesc in enumerate(ColumnDescriptions):
      self.SetColLabelValue(colnum, coldesc.heading)
    
    self.dirpath        = None  #must be set, will be asserted
    
    #find the NAME Column for standard sort
    self.sortcolIdx     = ColDescDict["name"][0]
    self.sortReverse    = False
    
    #===== GRID-EVENTS =====
      #Double Click is relevant on Directories
      #and for the Marker Column
    self.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.OnDoubleClick)
    
      #Label/Headline Click can still be sorting,
      #but must be on right click for column selection to work !
    self.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK, self.OnLabelSortClick)
    
    #===== FILL WITH DATA =====
    
    #my DirectoryData: create empty and then my goto
    self.dirdata = basis.DirectoryData(AllColumnNames)
      #the data object does not call goto from init, that is my job

  def GotoDirGrid(self, dirpath, sortIdxAndRev):
    #remember what I am displaying (or use what was remembered)
    if dirpath: self.dirpath = dirpath
    else:       assert self.dirpath, "GotoDirGrid without a path is not possible the first time"
    
    if not os.path.isdir(self.dirpath):
      LogMessageDialog(MSG_ERROR, "Path '%s' is not a directory" % self.dirpath)
      return    #no Update, do not destroy the current list with nonsense
    
    #Update my data object =>
    self.dirdata.GotoDir(self.dirpath)
    
    for col,cd in enumerate(ColumnDescriptions):
      self.SetColSize(col,cd.width)
    
    #=> Refresh Display
    self.SortRefresh(sortIdxAndRev)
    
    #plus UTC is displayed outside the grid
    FatLabel.SetLabel("win=%d utc=%d" % (int(basis.RUNNING_WIN), int(self.dirdata.fsutc)))

  def SortRefresh(self, sortIdxAndRev):
    #===== Set Sorting and Apply to DIR =====
    if sortIdxAndRev:
      self.sortcolIdx,self.sortReverse = sortIdxAndRev
    self.sortcolDesc = ColumnDescriptions[self.sortcolIdx]
    MainWin.SetStatusText("Sort: %s (%s)" % (self.sortcolDesc.heading, "Z..A" if self.sortReverse else "A..Z"))
    
    self.dirdata.ApplySort(self.sortcolDesc.name,self.sortcolDesc.proxyobj,self.sortReverse)
    
    #===== now Update the GRID contents from DIR =====
    numrows = self.dirdata.get_EntriesLen()
    
    ##FAIL: this is the intention, but Create works only once
    ##  self.CreateGrid(numrows, basis.COLNUM)
    
    #the COLUMNS will never change, but all ROWS are renewed
    if self.GetNumberRows():    #no need for empty dirs
      self.DeleteRows(0,-1)     #delete ALL rows
    
    if numrows:
      self.AppendRows(numrows)  #create the new number
    
    #the DIR provides an iter, the COLUMNS provide the sequence, then the FILE is asked
    for rownum,entry in enumerate(self.dirdata.get_EntriesIterAll()):
      entry_name = entry.getName()
      entry_type = entry.getType()
      
      for colnum,coldesc in enumerate(ColumnDescriptions):
        #1.get a single cell value for the file
        cellvalue = entry.getCellValue(coldesc.name)
        
        #2.format as string
        if isinstance(cellvalue,basis.CellObject):      #a)ask the CellObject
          cellstringex = cellvalue.getDisplay()
        
        else:                                           #b)give the value to the column's proxyobj
          ##all columns have a proxyobj, as asserted on init
          cellstringex = coldesc.proxyobj.getDisplay(cellvalue)
        
        if type(cellstringex)==type(()):                #CellObject may supply a colour
          cellstringex,cell_colour = cellstringex
        else:
          cell_colour = None

        self.SetCellValue(rownum,colnum, cellstringex)
        self.SetReadOnly (rownum,colnum, True)
        
        alignmap = { 'L':wx.ALIGN_LEFT, 'C':wx.ALIGN_CENTRE, 'R':wx.ALIGN_RIGHT }
        self.SetCellAlignment(rownum,colnum, alignmap[coldesc.align], wx.ALIGN_CENTRE)
        
        #SET COLOUR by Priority ...
          #PRIO 1: colour coming from this cell
        if cell_colour:
          self.SetCellBackgroundColour(rownum,colnum, cell_colour)
        
          #PRIO 2: line colour (Dirs,Special), if we are in the right columns
        elif colnum in [1,2] and entry.line_colour:
          self.SetCellBackgroundColour(rownum,colnum, entry.line_colour)
        
          #PRIO 3: column colour, used for debug columns
        elif coldesc.colour:
          self.SetCellBackgroundColour(rownum,colnum, coldesc.colour)
        
  
  #-------------------------------------------------
  #EVENTS...
  
  def OnDoubleClick(self, event):
    "Double Click is relevant on Directories and for the marker column"
    
    self.ClearSelection()
    
    col = event.GetCol()
    row = event.GetRow()
    
    #DCLICK in the marker column -> Toggle
    if col==0:
      self.MarkSelectedRows(-1,[row])     #Toggle, but choose the row
    
    #DCLICK anywhere in a subdirectory line -> Goto
    fileobj = self.dirdata.get_Entry(row)
    
    if fileobj.getType()=="D":
      MainWin.GotoDirMain(fileobj.getName())
    ##else:
    ##  ignore for F=File and x=Other...
  
  def SortItems(self, col,reverse):
    "from main window Buttons or from local Event OnLabelSortClick"
    
    self.ClearSelection()
    sortIdxAndRev = (col, reverse)
    self.SortRefresh(sortIdxAndRev)
      ##without reloading self.dirdata, the MARKER column
      ##must not be destroyed

  def OnLabelSortClick(self, event):
    "Label/Headline Click should be sorting like in Explorer"
    
    #this will come for all headers, rows and cols
    #row must be -1 (top line) and col must not (upper left box)
    row = event.GetRow()
    col = event.GetCol()
    ##DEBUG print (row,col)
    
    if row>-1 or col<=-1:
      event.Skip(True)
      return
    
    #new Column:  sort by this column A..Z       => col!=self.sortcolIdx
    #same Column: toggle A..Z and Z..A
    #  translates to: if col!=self.sortcolIdx then False else not self.sortReverse
    reverse = col==self.sortcolIdx and not self.sortReverse
    self.SortItems(col,reverse)

  def MarkSelectedRows(self, markmode, pickrows=None):
    if not pickrows:
      pickrows = self.GetSelectedRows()
    entries = self.dirdata.get_EntriesIterPick(pickrows)
    
    for entry in entries:
      entry.ChangeMark(markmode)
    
    #Update without file refresh like for sorting
    self.SortRefresh(None)
    
    #marks are counted, so update the display for the main ops
    ##NOT MainDataReset !!
    MainWin.UpdateMainopText()
  
  #-------------------------------------------------
  #ACTIONS for THE MAIN FUNCTIONS
  
  def hasMarkers(self):
    return self.dirdata.hasMarkedEntries()
  
  def pickMarkIterator(self):
    """pick one of 2 iterators to step over the [marked] files"""
    
    if self.dirdata.hasMarkedEntries():             #if there are Markers we iterate only those files
      return self.dirdata.get_EntriesIterMarked()
    
    else:                                           #Markers seem to be optional for this operation
      return self.dirdata.get_EntriesIterAll()      #so we iterate all
  
  def markerCounts(self):
    return "%d files/%d items of %d total" % self.dirdata.countMarkedEntries()
  
  def DeleteOutputs(self):
    """kill Output data from Grid for situations without a full reload"""
    for entry in self.dirdata.get_EntriesIterAll():
      entry.DelOutputs()
    self.SortRefresh(None)
  
  def WriteMyFile(self):
    self.dirdata.writeMyFile()
  
  def ActionAnalyse(self, coldesc1,coldesc2):
    self.DeleteOutputs()
    
    fileiter = self.pickMarkIterator()
    for file in fileiter:
      file.ActionAnalyse(coldesc1,coldesc2)
    
    self.SortRefresh(None)

  def ActionColourise(self, coldesc1,coldesc2):
    self.DeleteOutputs()
    
    fileiter = self.pickMarkIterator()
    for file in fileiter:
      file.ActionColourise(coldesc1,coldesc2)
    
    self.SortRefresh(None)

  def ActionTransfer(self, coldesc1,coldesc2):
    self.DeleteOutputs()
    
    fileiter = self.pickMarkIterator()
    for file in fileiter:
      file.ActionTransfer(coldesc1,coldesc2)
    
    #for the harmless OPS 1 and 2 SortRefresh was enough
    #the BIG TRANSFER needs more...
    
    #1.TRANSFER already made the physical changes it could,
    #  eg. stat.st_mtime data might have changed
    
    #2.some TRANSFER target columns may require an additional callback
    if type(coldesc2.posttransfer) != type(True):
      coldesc2.posttransfer()
      #call it as a function, currently used for DirWriteMyFile
    
    #3.when all is set, order a full reload
    MainWin.GotoDirMain(self.dirpath)

#----------------------------------------------------------------------
#TOPLEVEL Window and main Program Loop

class StamperWindow (wx.Frame):
  """the main window, a StamperDirTable GRID with some decoration"""
  
  def __init__(self, pythondir):
    """Constructor: set up the main window"""
    
    #data stored in main: 2 COLUMNS (ColumnDescription) for the main operations
    self.main_fromto = [None,None]
    
    wx.Frame.__init__(self, parent=None, title="TimeStamper GUI", size=(800,600))
    ##NO NEED self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
    self.CreateStatusBar()
    
    #script dir, my icon
    self.pythondir = pythondir
    iconfile = os.path.join(pythondir,"timestamper32.png")
    icon = wx.Icon(iconfile,wx.BITMAP_TYPE_PNG)
    self.SetIcon(icon)
    
    self.SetAutoLayout(True)
    mainsizer = wx.BoxSizer(wx.VERTICAL)
    self.SetSizer(mainsizer)
    
    #convenience macro for simple buttons ;-)
    def buttonMaker(label, callback, sizer, style=0):
      newbutt = wx.Button(self,-1, label, style=style)
      newbutt.Bind(wx.EVT_BUTTON, callback)
      sizer.Add(newbutt, 0, wx.EXPAND)  #EXPAND in the other (non-sizer) direction
      return newbutt
    
    #TOP AREA 1: current directory path and buttons
    topsizer1 = wx.BoxSizer(wx.HORIZONTAL)
    
    global PathLine
    PathLine = wx.TextCtrl(self,-1, "", style=wx.TE_PROCESS_ENTER)
      #single line (not wx.TE_MULTILINE)
      #editable (not wx.TE_READONLY)
      #wx.TE_PROCESS_ENTER => i want an EVT_TEXT_ENTER event
    PathLine.Bind(wx.EVT_TEXT_ENTER, self.PathLineEnter)
    topsizer1.Add(PathLine, 1, wx.EXPAND)
    
    buttonMaker("Refresh", self.ButtRefresh, topsizer1)
    buttonMaker("Go Up",   self.ButtGoUp,    topsizer1)
    
    mainsizer.Add(topsizer1, 0, wx.EXPAND)
    
    #TOP AREA 2: small buttons for mark <- and ->sort
    topsizer2 = wx.BoxSizer(wx.HORIZONTAL)
    
    buttonMaker("  [X]  ", self.ButtMarkAll,  topsizer2, style=wx.BU_EXACTFIT)
    buttonMaker("  [ ]  ", self.ButtMarkNone, topsizer2, style=wx.BU_EXACTFIT)
    buttonMaker("  [/]  ", self.ButtMarkInv,  topsizer2, style=wx.BU_EXACTFIT)
    
    topsizer2.AddStretchSpacer()
    
    global FatLabel
    FatLabel = wx.StaticText(self,-1,"win=?? utc=??")
      ##needs to be the right size, Linux will only measure Static once
    topsizer2.Add(FatLabel, 0, wx.EXPAND)
    
    buttonMaker(" [A..Z] ", self.ButtSortAZ, topsizer2, style=wx.BU_EXACTFIT)
    buttonMaker(" [Z..A] ", self.ButtSortZA, topsizer2, style=wx.BU_EXACTFIT)
    
    mainsizer.Add(topsizer2, 0, wx.EXPAND)
    
    #CENTRAL AREA: THE GRID!
    global TableGrid
    TableGrid = StamperDirTable(self)
    mainsizer.Add(TableGrid, 1, wx.EXPAND)
    
    #BOTTOM AREA: for the transfer operation
    bottomsizer = wx.BoxSizer(wx.HORIZONTAL)
    
    #2 buttons extra for from/to
    minisizer1 = wx.BoxSizer(wx.VERTICAL)
    buttonMaker("both",   self.ButtPrepBoth, minisizer1)
    buttonMaker("swap",   self.ButtPrepSwap, minisizer1)
    bottomsizer.Add(minisizer1, 0, wx.EXPAND)
    
    #2 buttons from/to vertical
    minisizer2 = wx.BoxSizer(wx.VERTICAL)
    buttonMaker("from->", self.ButtPrepFrom, minisizer2)
    buttonMaker("->to ",  self.ButtPrepTo,   minisizer2)
    bottomsizer.Add(minisizer2, 0, wx.EXPAND)
    
    global MainopText
    MainopText = wx.TextCtrl(self,-1, "", style=wx.TE_MULTILINE|wx.TE_READONLY)
    ##MainopText.GetSizeFromText("X\nX\nX") - measures differently here ?
    bottomsizer.Add(MainopText, 1, wx.EXPAND)
    
    self.mainopTextNeedsSize = True	#too early to measure, postpone till first update
    
    #the main operations are preceded by little hints to their use of the 3 big inputs
    bottomsizer.Add( wx.StaticText(self,-1,"?\nX\nX"), 0, wx.EXPAND)
    buttonMaker("Analyse",   self.ButtAnalyse,  bottomsizer)
    
    bottomsizer.Add( wx.StaticText(self,-1,"?\nX\n?"), 0, wx.EXPAND)
    buttonMaker("Colourise", self.ButtColourise,bottomsizer)
    
    bottomsizer.Add( wx.StaticText(self,-1,"X\nX\nX"), 0, wx.EXPAND)
    buttonMaker("Transfer!", self.ButtTransfer, bottomsizer)
    
    mainsizer.Add(bottomsizer, 0, wx.EXPAND)
    
    ##LATER: not need for a MENU yet...
    ##menuBar = wx.MenuBar()
    ##toolBar = self.CreateToolBar( wx.TB_HORIZONTAL|wx.TB_FLAT )
    
    self.Show(True)

  def MainDataReset(self):
    self.main_fromto = [None,None]
    ##@@MUEHSAM self.main_fromto = [ColumnDescriptions[9],ColumnDescriptions[6]]
    self.UpdateMainopText()

  #-------------------------------------------------
  #MAIN ACTIONS
  
  def GotoDirMain(self, dirpath):
    #if we can: go there, and normalize...
    try:
      os.chdir(dirpath)
      dirpath = os.path.abspath('.')
    
    except FileNotFoundError:
      pass      #error display will come from grid
    
    #display the path
    PathLine.SetValue(dirpath)
    
    #goto the dir, Sorting is default
    TableGrid.GotoDirGrid(dirpath, None)
    
    #update the display for the main ops
    self.MainDataReset()
  
  #-------------------------------------------------
  #Helper for EVENTS
  
  def GetOneSelectedColumn(self, count=1):
    ##TRICK: normally One Column, but we can ask for 2 (or more)
    
    cols = TableGrid.GetSelectedCols()
    if not cols:
      LogMessageDialog(MSG_WARNG, "No COLUMN selected.")
      return -1
    
    if len(cols)!=count:
      LogMessageDialog(MSG_WARNG, "Need % (not %d) COLUMNS selected." % (count,len(cols)))
      return -1
    
    ##print ("@@GetColSize:",TableGrid.GetColSize(cols[0]))
    if count==1: return cols[0] #one
    else:        return cols    #many
  
  #-------------------------------------------------
  #EVENTS...
  
  #===== PATH EVENTS: buttons and from text field =====
  def PathLineEnter(self, event):
    "enter key in path line -> GOTO"
    self.GotoDirMain( PathLine.GetValue() )
  
  def ButtRefresh(self, event):
    "Path: Refresh, stay here"
    #redisplay, stay where you are
    TableGrid.GotoDirGrid(None, None)
      ##only the Grid itself, all the main window decoration can stay
    
    #we dont call the full GotoDirMain, so we need to reset that manually
    self.MainDataReset()
  
  def ButtGoUp(self, event):
    "Path: Go Up 1 directory"
    self.GotoDirMain("..")
      ##abspath will do the rest
  
  #===== MARK EVENTS: 3 buttons =====
  def ButtMarkAll(self, event):
    "selected Grid lines -> mark all File objects"
    TableGrid.MarkSelectedRows(1)
  def ButtMarkNone(self, event):
    "selected Grid lines -> unmark all File objects"
    TableGrid.MarkSelectedRows(0)
  def ButtMarkInv(self, event):
    "selected Grid lines -> toggle mark for all File objects"
    TableGrid.MarkSelectedRows(-1)
  
  #===== SORT EVENTS: 2 buttons =====
    ##LATER: instead of GetOneSelectedColumn, could sort by multiple cols
  
  def ButtSortAZ(self, event):
    "selected Column: Sort A-Z"
    col = self.GetOneSelectedColumn()
    if col>=0:
      TableGrid.SortItems(col,False)
  
  def ButtSortZA(self, event):
    "selected Column: Sort Z-A"
    col = self.GetOneSelectedColumn()
    if col>=0:
      TableGrid.SortItems(col,True)

  #===== PREPARE EVENTS: 2 buttons =====
  def SetFromto(self, fromtoidx):
    if fromtoidx==2:
      fromtoidxs = [0,1]
      cols = self.GetOneSelectedColumn(2)
    else:
      fromtoidxs = [fromtoidx]          #just one 0 or 1
      cols = [self.GetOneSelectedColumn()]
    
    change = False
    
    for fromto,col in zip(fromtoidxs,cols):
      if col>=0:                  #pick the right ColumnDescription
        coldesc = ColumnDescriptions[col]
        
        if not coldesc.isstamp:   #only for Timestamps !
          LogMessageDialog(MSG_WARNG, "Not a timestamp Column.")
          coldesc = None
      
      else:                       #else, reset to ---
        coldesc = None
      
      #then put it into from/to
      change = change or (self.main_fromto[fromto] != coldesc)
      self.main_fromto[fromto] = coldesc
    
    if change:
      self.UpdateMainopText()
      TableGrid.DeleteOutputs()
  
  def ButtPrepFrom(self, event):
    "Prep Action: make selected Column 'from'"
    self.SetFromto(0)
  def ButtPrepTo(self, event):
    "Prep Action: make selected Column 'to'"
    self.SetFromto(1)

  def ButtPrepBoth(self, event):
    "Prep Action: make selected Column 'from'"
    self.SetFromto(2)
  
  def ButtPrepSwap(self, event):
    "Prep Action: Swap from and to"
    self.main_fromto.reverse()
    self.UpdateMainopText()
    TableGrid.DeleteOutputs()
  
  
  #-------------------------------------------------
  #EVENTS for THE MAIN FUNCTIONS
  
  def checkInputColdesc(self, inputnum,inputname, coldesc, isrequired):
    if not coldesc:     #missing coldesc -> an error if required
      if isrequired:
        return "Input %d.%s: is missing" % (inputnum,inputname)
    
    else:               #coldesc present, further checks...
      prefix = "Input %d.%s -> %s:" % (inputnum,inputname, coldesc.heading)
      
      #it has to be a timestamp (double-check, the buttons check also)
      if not coldesc.isstamp:
        return "%s is not a Timestamp" % prefix
      
      #special value "TARGET" instead of just True leads to extra Check
      if isrequired=="TARGET" and not coldesc.posttransfer:
        return "%s is not allowed as a Target" % prefix
    
    return ""
  
  def checkMainInputs(self, require_marks, require_col1,require_col2):
    """check all Inputs: Grid markers and 2 coldescs according to OPERATION settings"""
    
    #===== Markers in the Grid
    msg1 = ""
    if require_marks:
      if not TableGrid.hasMarkers():
        msg1 = "No Files marked in Table"
    
    #===== 2 Columns to pick
    coldesc1,coldesc2 = self.main_fromto
    
    #the subfunctions just return any error message
    msg2 = self.checkInputColdesc(1,"from",coldesc1, require_col1)
    msg3 = self.checkInputColdesc(2,"to",  coldesc2, require_col2)
    
    msg4 = ""
    if coldesc1 and coldesc1==coldesc2:
      msg4 = "From and To are the same column"
    
    #the error dialog appears only once (here)
    msg = "\n".join(filter(None, [msg1,msg2,msg3,msg4]))
    if msg:
      LogMessageDialog(MSG_ERROR, msg)
    
    #return errorflag
    return bool(msg)
  
  def UpdateMainopText(self):
    def getheading(fromtoidx):
      coldesc = self.main_fromto[fromtoidx]
      return (coldesc.heading if coldesc else "---")
    
    line1 = "marked:\t%s" % TableGrid.markerCounts()
    line2 = "from:\t%s" % getheading(0)
    line3 = "to:   \t%s" % getheading(1)
    text = "\n".join([line1,line2,line3])
    
    MainopText.SetValue(text)
    
    if self.mainopTextNeedsSize:
      self.mainopTextNeedsSize = False
      
      textheight = MainopText.GetSizeFromText(text).y
      MainopText.SetMinSize((-1,textheight+1))
  
  def ButtAnalyse(self, event):
    "Big Action: Analyse difference between 2 columns"
    
    if self.checkMainInputs(False, True,True): return
      #ANALYSE is harmless, Markers are optional
      #ANALYSE needs 2 columns to compare, neither is optional
    
    TableGrid.ActionAnalyse(*self.main_fromto)
  
  def ButtColourise(self, event):
    "Big Action: Compare from 1 COL to all others, set their Colour"
    
    if self.checkMainInputs(False, True,False): return
      #COLOURISE is harmless, Markers are optional
      #COLOURISE only needs a Source Column, will colour all if Target is missing
    
    TableGrid.ActionColourise(*self.main_fromto)
  
  def ButtTransfer(self, event):
    "Big Action: Transfer from 1 column to another"
    if self.checkMainInputs(True, True,"TARGET"): return
      #TRANSFER is dangerous, works only on Marked Files
      #TRANSFER requires both columns, the TARGET has a special check (which is first seen as True)
      #  assert that it is allowed as target
    
    TableGrid.ActionTransfer(*self.main_fromto)

if __name__ == "__main__":
    #python script directory
  pythondir = os.path.dirname(os.path.abspath(__file__))
    #first argument (after py-name) or None
  startdir = sys.argv[1:2] or ["."]
  
  app = wx.App(False)
    #my own class MyApp(wx.App): is not needed
    #that would be for system wide initialization and such
  
  MainWin = StamperWindow(pythondir)
  MainWin.GotoDirMain(startdir[0])
  app.MainLoop()
