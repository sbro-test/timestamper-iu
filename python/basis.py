"""the base objects and functions that are independent of the GUI,
  for a ##FUTURE command line program flavour"""

import os,sys,re,time,datetime
import calendar                 #the inverse of time.gmtime -> calendar.timegm is here

import config

RUNNING_WIN = None
if   sys.platform.startswith("win"):   RUNNING_WIN = True
elif sys.platform.startswith("linux"): RUNNING_WIN = False
else: assert 0,"Not tested on %s" % sys.platform

  ##NOTE: even on Win7 with PY 3.8, the answer is "win32"

#----------------------------------------------------------------------
#CellObject, the lowest object for one files value for one column (cell)

#===== CLASS 0: THE BASE =====
class CellObject:
  """the root CellObject, an abstract base class"""
  
  #tuple -> colour from the windows library, to be supplied by the main program
  colourMaker = None
  
  #def __init__(self):
  #  pass
  
  def getDisplay(self):
    """format VALUE for GUI display, the wx.grid requires Strings"""
    raise NotImplementedError("CellObject Subclasses must implement getDisplay")
  
  def getSortKey(self):
    """convert VALUE into a key for Sorting (if necessary)"""
    raise NotImplementedError("CellObject Subclasses must implement getSortKey")
  
  #only for TIMESTAMPs !
  def transferGet(self):
    raise NotImplementedError("transferGet should only be called for timestamps (which must implement it)")
  def transferSet(self, input):
    raise NotImplementedError("transferSet should only be called for timestamps (which must implement it)")


#===== CLASS 1: A DUMMY WITH ONLY 2 VALUES =====
class CellObjectDummy (CellObject):
  """a DUMMY CellObject that supplies fixed answers to the normal questions format/sort"""
  
  def __init__(self, dispstring,sortkey):
    self.dispstring = dispstring
    self.sortkey    = sortkey
  
  def getDisplay(self): return self.dispstring
  def getSortKey(self): return self.sortkey
  
  #dummies never give real transfer data, this is the sign for "nothing"
  def transferGet(self): return None
  
  #dummies may also be asked to provide datafile stamps (nothing)
  def getDatafileString(self): return None
  
  #dummies dont know colours, if a colour is set than only during delete, must be None
  def setActionColour(self, colour):
    assert not colour, "CellObjectDummy.setActionColour cant handle real colour: %r" % colour

#3 actual (singleton) dummy objects
"""UNUSED, the subdir's cells simply return None and the PROXY handles it
CODummyDirNum = CellObjectDummy("",-2)          #Columns not relevant for Subdirs, type Number
                                                #(no display, sorting -2 comes before files -1)
CODummyDirStr = CellObjectDummy("","")          #Columns not relevant for Subdirs, type Number
                                                #(no display, sorting as "")
"""

CODummyFileTime = CellObjectDummy(config.GUI_TIMESTAMP_DUMMY, time.gmtime(1))
  #Files that do not have this Timestamp
  #  - display from config
  #  - sortkey must be a struct,
  #    DIRs are 0 seconds and FILEs 1 second after epoch
  #    ~>see "Note on DUMMY VALUES for TIMESTAMPS"
  #      and class CellObjectProxyStamp


#===== CLASS(es) 2: PROXIES WITH NO STORED VALUES but KNOWLEDGE of Column Properties =====
class CellObjectProxy (CellObject):
  """intermediate class to check for descendancy in the GUI
  
  PROXY CellObjects will be applied too many different simple values (ints,strings)
    they do not store any values and require those to be supplied
    to the individual methods
  """
  pass

class CellObjectProxyMarker (CellObjectProxy):
  """a proxy for the MARKER column, the first to return a colour"""
  
  def __init__(self):
    self.mycolour = CellObject.colourMaker(config.GUI_COLOUR_MARK)
  
  def getDisplay(self, value):
    """first time we wish for a colour :-)"""
    if value: return ('*', self.mycolour)
    else:     return ""
  
  def getSortKey(self, value):
    return value

class CellObjectProxyString (CellObjectProxy):
  """a proxy for STRING type columns, very simple conversions"""
  
  #def __init__(self):
  #  pass
  
  def getDisplay(self, value):
    """no need to turn a string into a string, just handle None from Directories"""
    return value or ""
  
  def getSortKey(self, value):
    """like getDisplay"""
    return (value or "").lower()

class CellObjectProxyInt (CellObjectProxy):
  """a proxy for INT type columns, very simple conversions"""
  
  #def __init__(self):
  #  pass
  
  def getDisplay(self, value):
    if value is None: return ""
    return str(value)
  
  def getSortKey(self, value):
    if value is None: return -1
    return value

class CellObjectProxyBytes (CellObjectProxy):
  """a proxy for 'SIZE in Bytes' columns, fancy formatting"""
  
  thousands_sep = config.GUI_BYTES_SEPARATOR
  
  #def __init__(self):
  #  pass
  
  def getDisplay(self, value):
    if value is None: return ""
    return config.GUI_BYTES_FORMAT.format(value).replace(',', self.thousands_sep)
      #can simply replace ',' integers dont have those otherwise
  
  def getSortKey(self, value):
    if value is None: return -1
    return value

class CellObjectProxyOutput (CellObjectProxy):
  """a proxy for the OUTPUT column, outputs are None or Tuples from ANALYSE"""
  
  #def __init__(self):
  #  pass
  
  ##Tuples are colourfulStampCompare return values: (severity, colour, seconds)
  ##  or None initially/if data are missing

  def getDisplay(self, value):
    """directly use colour !"""
    if not value: return ""
    
    severity, colour, seconds = value
    text = "%s:%d" % (severity,seconds)
    return (text, colour)
  
  def getSortKey(self, value):
    """sort by distance means absolute difference !"""
    if not value: return (-1,0)
    
    severity, colour, seconds = value
    severitynum = int(severity[0])
    return (severitynum,abs(seconds))

class CellObjectProxyStamp (CellObjectProxy):
  """a proxy for all TIMESTAMP columns, very fancy formatting !"""
  
  #def __init__(self):
  #  pass
  
  def getDisplay(self, value):
    """all non-zero Values are full objects, only None from DIRs will come here"""
    assert value is None
    return ""
  
  def getSortKey(self, value):
    """all non-zero Values are full objects, only None from DIRs will come here"""
    #DIRs are 0 seconds and FILEs 1 second after epoch (see big comment below)
    assert value is None
    return time.gmtime(0)

  #Note on DUMMY VALUES for TIMESTAMPS
  #! we can't compare ints like -2 and -1 to timestructs;
  #  but we don't want the inefficiency of converting back to ints either
  #
  #! DUMMY Values must therefore be in time.struct_time format;
  #  which means we can't go negative before the epoch
  #=>so for DIRS (which never have timestamps)
  #  to come before FILES (those which do not have this particular stamp)
  #  DIRs are 0 seconds and FILEs 1 second after epoch
  #    (1970-01-01 00:00:00 and :01 on Linux)

  #like dummies, proxies never give real transfer data, this is the sign for "nothing"
  def transferGet(self): return None


#----------------------------------------------------------------------
#TIMESTAMPS are also CellObjects, THEY ARE THE CORE OF THE PROGRAM

def DEBUGTIME(idx, intorstruct):
  if type(intorstruct)==type(123):
    xxhourmin = intorstruct // 60       #cut seconds
    mins = xxhourmin % 60               #mins at the end
    hours = xxhourmin // 60 % 24        #cut mins, hours at the end
    print ("DEBUGTIME %d: %02d:%02d" % (idx, hours,mins))
  
  else:
    classname = getattr(type(intorstruct),"__name__",None)
    
    if classname=="struct_time":
      print ("DEBUGTIME %d: %s" % (idx, time.strftime("%H:%M", intorstruct)) )
    else:
      print ("DEBUGTIME %d: Not int or struct_time: %r" % (idx, intorstruct))

def DEBUGASSERT2STRUCTS(txt_prefix,txt_transop, struct1,struct2):
  ##print ('\n',txt_prefix)
  ##print (struct1)
  ##print (struct2)
  assert struct1==struct2, "%s: why is %r %s %r different ?" % (txt_prefix,struct1,txt_transop,struct2)

#===== CLASS(es) 3: Timestamps are real CellObject with local data for the time structure =====

class CellObjectStamp (CellObject):
  """the core of all TimeStamp classes is to use time.struct_time structures"""
  
  def __init__(self):
    self.my_structtime = None           #set by subclasses !
    self.action_colour = None           #[possibly] set by ActionColourise
  
  def getDisplay(self):
    text = time.strftime( config.GUI_TIMESTAMP_FORMAT, self.my_structtime )
    if self.action_colour:
      return (text,self.action_colour)
    else:
      return text
  
  def getSortKey(self):
    """these timestamps will be compared as time.struct_time,
      DUMMIES must be converted accordingly"""
      ##see 'Note on DUMMY VALUES for TIMESTAMPS'
    return self.my_structtime
  
  def transferGet(self):
    """all transfers will be based on time.struct_time structures"""
    return self.my_structtime
  
  #def transferSet(self, input):
  #  Setting is more difficult, must be done in subclass logic
  
  def setActionColour(self, colour):
    self.action_colour = colour

#...but there is one for the two(/more?) Timestamps
#based on timestamps from os.stat
class CellObjectStampStat (CellObjectStamp):
  """most of the functionality for Timestamps based on os.stat values and 
    time.struct_time structures is the same, only the conversion functions differ
    (and the stamp they are inited with)"""
  
  def __init__(self, fullpath,statkey,statint):
    """take an integer stamp from os.stat and convert it to my 
      internal storage format (time.struct_time)"""
    super().__init__()
    self.fullpath = fullpath    #full path of my file in case to write back stat data
    self.statkey = statkey      #which stat value is it ?
    self.my_structtime = self._int2struct(statint)
  
  #===== transferSet for Linux-style mtime
  def transferSet(self, inputstruct):
    #silently ignore if we are still trying to set ctime, forbidden in GUI
    if self.statkey == "st_ctime": return
    
    #set my struct, of course
    self.my_structtime = inputstruct
    
    #THE REAL CHANGE: but also push the mtime back to the filesystem!
    
    #convert to mtime Integer
    statint = self._struct2int(inputstruct)
    teststruct = self._int2struct(statint)
    DEBUGASSERT2STRUCTS("transferSet PY double check", "_struct2int-> _int2struct->", inputstruct[:6],teststruct[:6])
    
    #SET DATE VALUES (%%internal: like in touchplus.py)
    mystat = os.stat(self.fullpath)
    os.utime(self.fullpath, (mystat.st_atime, statint) ) #keep atime, set new mtime !!
    
    #done. now check again
    mystat = os.stat(self.fullpath)
    teststruct = self._int2struct(mystat.st_mtime)
    DEBUGASSERT2STRUCTS("transferSet PY triple check", "_struct2int-> _int2struct->", inputstruct[:6],teststruct[:6])
  
  #===== CALLBACKS for the 2 subclasses to implement
  def _int2struct(self, statint):
    """turn an int from os.stat into the relevant time.struct_time"""
    raise NotImplementedError("the 2 subclasses of CellObjectStampStat for local/utc will implement _int2struct differently")
  
  def _struct2int(self, structtime):
    """turn an int from os.stat into the relevant time.struct_time"""
    raise NotImplementedError("the 2 subclasses of CellObjectStampStat for local/utc will implement _struct2int differently")

class CellObjectStampLocal (CellObjectStampStat):
  def __init__(self, fullpath,statkey,statint):
    super().__init__(fullpath,statkey,statint)
  
  #===== stat-ints are considered GMT <=> CALLBACKS for local times
  def _int2struct(self, statint):
    return time.localtime(statint)
  
  def _struct2int(self, structtime):
    return int(time.mktime(structtime))

class CellObjectStampGmt (CellObjectStampStat):
  def __init__(self, fullpath,statkey,statint):
    super().__init__(fullpath,statkey,statint)
  
  #===== stat-ints are considered GMT <=> CALLBACKS for structs also in GMT
  def _int2struct(self, statint):
    return time.gmtime(statint)
  
  def _struct2int(self, structtime):
    return int(calendar.timegm(structtime))

class CellObjectStampLinux (CellObjectStamp):
  """Linux View of Timestamps, equals Python View while running Linux,
    and even running Linux but for NTFS media
    only needs to be a Wrapper Object when running Windows for FAT
  """
  
  def __init__(self, fsutc,cellobj_local):
    super().__init__()
    
    assert RUNNING_WIN,"No need for this Wrapper Class when running Linux, use cellobj_local above"
    assert not fsutc,"No need for this Wrapper Class on NTFS, use cellobj_local above"
    
    #TS2 Linux is a small wrapper around TS1 Python CellObjects
    #similar to CellObjectStampWin, but simpler
    self.cellobj_local = cellobj_local
    structtime_local   = cellobj_local.transferGet()
    
    self.my_structtime = self.linux_onwin_fat_formula(structtime_local, inversion=1)
  
  def linux_onwin_fat_formula(self, structtimeinput, inversion):
    """the Localtime from TS1 is already quite close,
      but Linux will think Filesystem time is UTC and apply Country offset a second time
      FORWARD,  inversion=+1: add +1 hour for Germany, for example (for constructor)
      BACKWARD, inversion=-1: subtract                             (for transferSet)
    """
    
    #convert from and to local timestamps
    timestamp = int(time.mktime( structtimeinput ))
    
    timestamp -= time.timezone * inversion
      ##FORWARD (inversion=+1): DE should add 1 hour, but time.timezone is -3600
    
    return time.localtime(timestamp)
  
  def transferSet(self, inputstruct):
    #crazy_windows_formula this time with inversion, input is WIN, we are converting to LINUX/PY
    self.my_structtime = self.linux_onwin_fat_formula(inputstruct, inversion=-1)
    
    teststruct = self.linux_onwin_fat_formula(self.my_structtime, inversion=1)
    DEBUGASSERT2STRUCTS("transferSet LINUX double check", "linux_onwin_fat-1-> linux_onwin_fat+1->", inputstruct[:6],teststruct[:6])
    
    #back to TS1 base timestamp
    self.cellobj_local.transferSet(self.my_structtime)

class CellObjectStampWin (CellObjectStamp):
  """Windows View of Timestamps, both old and new (switched with a flag)
    depends on what is stored in die filesystem stamps
    or rather on what Windows thinks to expect there
    (ini file MYFILENAME_MEDIAPREFS, value timestampmode)
  """
  
  @staticmethod
  def MakeStampWinWrapper(fsutc,dstnow, newwin, cellobj_filesys,cellobj_local):
    """normally, construct a CellObjectStampWin wrapper object,
      but has the choice of returning an unwrapped object 
      if there is no conversion (and thus no need for wrapping)"""
    
    #===== return the source stamp directly if NO CONVERSION is needed =====
      ##ISOMORPHOUS with crazy_windows_formula,
      ##  wherever crazy asserts "Should have used directly,
      ##  this is where this happens ;-)
    if not fsutc:
      if RUNNING_WIN:
        if newwin:
          return cellobj_local
      else:
        if not newwin:
          return cellobj_filesys
    
    else:
      if newwin:
        return cellobj_local
    
    #===== NORMALLY: just call my constructor =====
    return CellObjectStampWin(fsutc,dstnow, newwin, cellobj_filesys,cellobj_local)
  
  def __init__(self, fsutc,dstnow, newwin, cellobj_filesys,cellobj_local):
    super().__init__()
    
      #all the Flags to crazy_windows_formula apply both ways,
      #just the direction of offsets will be inverted (inversion=-1)
    self.fsutc  = fsutc         #from DIR: is the filesystem in UTC ?
    self.dstnow = dstnow        #from DIR: are we on DST now ?
    self.newwin = newwin        #my flavour: new Windows or old ?
    
    #TS3 Win is really a wrapper around TS1 Python CellObjects
    self.cellobj_filesys = cellobj_filesys
    self.cellobj_local   = cellobj_local
    structtime_filesys = cellobj_filesys.transferGet()
    structtime_local   = cellobj_local.transferGet()
    
    #we rely on structtime_local containing dst info (but it does, even on PY 2.7 on WinXP)
    self.dstforfile = structtime_local.tm_isdst
    assert self.dstforfile in [0,1], "structtime_local needs to contain DST information, but is %r" % self.dstforfile
    
    self.my_structtime = self.crazy_windows_formula(structtime_filesys,structtime_local, inversion=1)
  
  def dst_plusFile_minusNow(self, timestamp,inversion):
    """normally +1 add 1 hour for dstforfile, -1 subtract 1 for dstnow
      this is 'forwards' with inversion=1 and towards new Windows
      inversion=-1 means 'backwards' -1 hour and +1 hour towards old Windows
    """
    
    timestamp += 3600 * self.dstforfile * inversion
    ##DEBUG DEBUGTIME(3,timestamp)
    timestamp -= 3600 * self.dstnow * inversion
    ##DEBUG DEBUGTIME(4,timestamp)
    return timestamp
  
  def crazy_windows_formula(self, structtime_filesys,structtime_local, inversion):
    ##DOCU: FIRST INVERSION is +1 or -1
    ##  +1 linux2win: calculate towards windows, for Constructor/Display
    ##  -1 win2linux: opposite offsets, for incoming transferSet
    
    ##no conversion no longer arrive here !
    ##  #the 2x2 matrix of fsutc and newwin has 2 elements with no conversion at all
    ##  retstruct = @@either structtime_filesys,structtime_local
    
    if not self.fsutc:          #OLD filesystem in LOCALTIME (FAT)
      ##RUNNING_WIN: WINDOWS/LINUX is very different for FAT !
      
      if RUNNING_WIN:
        ##RUNNING_WIN: WINDOWS can also use Python for NEWWIN,
        ##  but needs tricks for OLDWIN

        if self.newwin:
          ##running on WIN, even on FAT/NEWWIN is the same as Python
          assert 0,"Should have used TS1/Local directly, the MakeStampWinWrapper knows that"
        
        else:
          #Old Windows from Localtime just like on NTFS below
          timestamp = int(time.mktime( structtime_local ))
          timestamp = self.dst_plusFile_minusNow(timestamp, -inversion)
            #NORMALLY BACKWARD: -1 hour for File DST, +1 hour for Now DST
          retstruct = time.localtime(timestamp)
      
      else:
        ##RUNNING_WIN: on LINUX the gmtime is very usefull
        ##  for getting the low level FAT timestamps
        
        if self.newwin:
          #mktime => localtime FAIL: this is for linux display,
          #does -1 and +2 for summer files in winter
          
          timestamp = int(calendar.timegm( structtime_filesys ))
          ##DEBUG print ("\nNEWIN=",self.newwin)
          ##DEBUG DEBUGTIME(1,structtime_filesys)
          ##DEBUG DEBUGTIME(2,timestamp)
          
          ##SECOND INVERSION, but not here, we are ordering +inversion
          timestamp = self.dst_plusFile_minusNow(timestamp, +inversion)
            #if FORWARD: New Windows thinks like Linux/Python and uses +1 dst offset only 
            #  for files in summer, but we need to subtract current dst (see Docu Table)
          
          newlist = list( time.gmtime(timestamp) )
          newlist[8] = -1           #this destroys .isdst, so it must not claim to know isdst=0
          
          retstruct = time.struct_time(tuple( newlist ))
        
        else:
          ##GMT is already OLDWIN, as long as we are running Linux
          assert 0,"Should have used TS1/Gmt directly, the MakeStampWinWrapper knows that"
    
    else:                       #MODERN filesystem in UTC (NTFS)
      ##RUNNING_WIN: WINDOWS/LINUX does not matter here
      ##  because the TS1 PYTHON base timestamps
      ##  work the same on NTFS when running on win and linux
      
      if self.newwin:
        ##New systems NEWWIN/LINUX/PYTHON have the same opinion of NTFS drives
        assert 0,"Should have used TS1/Local directly, the MakeStampWinWrapper knows that"
      
      else:
        #code must be based on LOCAL, must not hard-wire OFFSET +1 for Germany
        timestamp = int(time.mktime( structtime_local ))
        ##DEBUG print ("\nNEWIN=",self.newwin)
        ##DEBUG DEBUGTIME(1,structtime_local)
        ##DEBUG DEBUGTIME(2,timestamp)
        
        #Old Windows on NTFS is really crazy (and one of the reasons for this program!)
        #  File DST offset is applied when writing, summer files have dst
        #  Everyone gets current DST offset for display, a crappy decision
        timestamp = self.dst_plusFile_minusNow(timestamp, -inversion)
          #NORMALLY BACKWARD: -1 hour if file time is in DST, as Windows will on writing
          #  +1 hour if it is DST now, this is how old windows displays file times (!)
        
        retstruct = time.localtime(timestamp)
    
    ##DEBUG DEBUGTIME(9,retstruct)
    ##DEBUG print ("dst:", retstruct.tm_isdst)
    return retstruct
  
  def transferSet(self, inputstruct):
    #crazy_windows_formula this time with inversion, input is WIN, we are converting to LINUX/PY
    self.my_structtime = self.crazy_windows_formula(inputstruct,inputstruct, inversion=-1)
    
    teststruct = self.crazy_windows_formula(self.my_structtime,self.my_structtime, inversion=1)
    DEBUGASSERT2STRUCTS("transferSet WIN double check", "crazywin-1-> crazywin+1->", inputstruct[:6],teststruct[:6])
    
    #back to gmt or local like in the constructor...
    if not self.fsutc:          #filesystem in LOCALTIME (FAT)
      self.cellobj_filesys.transferSet(self.my_structtime)
    
    else:                       #local times (currently Germany, winter)
      self.cellobj_local.transferSet(self.my_structtime)

_RESTR_NUM6_PURE  = "([0-9]{2})([0-9]{2})([0-9]{2})"
_RESTR_NUM6_MINUS = "([0-9]{2})-([0-9]{2})-([0-9]{2})"
REs_FNAMESTAMP = [
    #yyYYMMDD -_ HHMMSS
  re.compile("(19|20|21)?%s[_-]%s" % ((_RESTR_NUM6_PURE,)*2)),
    #o Samsung Fotos: 20251214_120000.jpg
    #o Samsung Shots: Screenshot_20251214_120000_Program Name.jpg
    #o Foto Rename: phoneprefix-251214-120000 Content description.jpg
  
    #yyYY-MM-DD xxxxxxx HH-MM-SS
  re.compile("(19|20|21)?%s.*%s" % ((_RESTR_NUM6_MINUS,)*2)),
    #o XFCE FX Shot: Screenshot 2026-01-12 at 15-57-36 Startpage.png
    #o XFCE dom0 Shot: Screenshot_2026-01-10_21-57-04.png
]

class CellObjectStampFname (CellObjectStamp):
  """Stamp from the Filename as may be available from modern mobile phones
    ! data source ONLY !
    using this as a transfer target would mean file rename
    which is too dangerous at this point
  """
  
  def __init__(self, fname):
    super().__init__()
    self.fname = fname
    
    #find a matching RE for Stamps in Filenames
    for regex in REs_FNAMESTAMP:
      m = regex.search(fname)
      if m:
        grps = list(m.groups())
        break
    
    else:
      #no match with any re in the list, no timestamp in the filename
      #do not construct a full CellObjectStampFname, use a DUMMY instead
      raise ValueError("NO-TIMESTAMP")

    #match found grps (groups) is a list of 7: example Xmas Lunch 2025
    #  ['20', '25', '12', '14', '12', '00', '00'] or
    #  [None, '25', '12', '14', '12', '00', '00']
    
    century = grps[0] or "20"         #default century is 20xx
    grps[0:2] = [ century+grps[1] ]   #full year with century, now a list of 6
    
    """FAIL, time.struct_time does not fill in the gaps we leave (by filling with -1)
    grps.extend( 3* [-1] )            #don't know the 3 complicated calender values, list of 9
    grps = (int(x) for x in grps)
    self.my_structtime = time.struct_time(grps)
    """
    
    grps = (int(x) for x in grps)       #convert to int
    dt = datetime.datetime(*grps)       #convert to datetime
    self.my_structtime = dt.timetuple() #convert to time.struct_time
    ##DEBUG print (self.my_structtime)
    ##DEBUG print (time.strftime( "%Y-%m-%d %H:%M:%S", my_structtime ))
  
  def transferSet(self, input):
    #should never be called, the ColumnDescriptions says no to me being a TRANSFER target
    raise NotImplementedError("transferSet to CellObjectStampFname would mean file rename, not implemented.")
    
    ##LATER: consider implementing file rename from stamp
    ##  and not just the other way round

class CellObjectStampDatafile (CellObjectStamp):
  """Stamp my private datafile MYFILENAME_DATA
    that has been read by the Directory Object"""
  
  def __init__(self, datafilestamp):
    super().__init__()
    
    if datafilestamp:           #NORMAL MODE
      #@@@ERROR HANDLING in Phase 3 ...
      tstruct = time.strptime(datafilestamp, config.DATA_TIMESTAMP_FORMAT)
      self.my_structtime = tstruct
    
    else:                       #DUMMY MODE
      self.my_structtime = None

  def getDatafileString(self):
    """Special Function only for CellObjectStampDatafile CellObjects"""
    #may be None through DUMMY MODE !
    if not self.my_structtime: return None
    
    return time.strftime( config.DATA_TIMESTAMP_FORMAT, self.my_structtime )

  ##DOCU: for transferSet to go to proper CellObjectStampDatafile,
  ##  the Column col_ts5_datafile must never use Dummies,
  ##  this object therefore has a dummy-mode (self.my_structtime = None)
  
  def getDisplay(self):
    if self.my_structtime: return super().getDisplay()
    else:          return CODummyFileTime.getDisplay()
  def getSortKey(self):
    if self.my_structtime: return super().getSortKey()
    else:          return CODummyFileTime.getSortKey()
    ##LATER: if this pattern is needed more often
    ##  (for new columns t5,t6,...) this could be some meta-functioncall
  
  ##def transferGet(self): only returns my_structtime anyway
  ##def setActionColour(self, colour): doesnt matter if we set the colour

  def transferSet(self, inputstruct):
    #really easy :-) this terminates a possible DUMMY MODE, we have data now
    self.my_structtime = inputstruct


#----------------------------------------------------------------------
#Objects for DIRS (actually just one dir) 
#        and FILES (actually all entry files/subdirs/other therein)

TYP_COLOURMAP = {
  'F':None,
  'D':config.GUI_COLOUR_DIR,
  'x':config.GUI_COLOUR_OTHER,
}

class FileData:
  #this RE is the rule for what column names are considered timestamps,
  #currently col_ts1_... to col_ts4...
  RE_TIMESTAMP_COL = re.compile("^col_ts[1-5]_")
  
  allcolnames   = None          #all col_... members needed for ColumnDescriptions
  allstampnames = None          #all timestamp names: col_ts1_modloc, col_ts1_modgmt, ...
                                #filled in through classmethod
  
  @classmethod
  def SetAllColumnNames(cls, allcolnames):
    #all columns known to ColumnDescriptions in GUI
    cls.allcolnames = [ "col_"+colname for colname in allcolnames ]
    
    #subset: only timestamp columns (who follow 
    cls.allstampnames = [ colname for colname in cls.allcolnames if cls.RE_TIMESTAMP_COL.search(colname) ]
  
  def __init__(self, mydir,os_direntry):
    #prepare colours for later Use
    self.myseveritycolours = {sev:CellObject.colourMaker(col) for sev,col in config.GUI_COLOUR_SEVERITIES.items()}
    
    #Files/Subdirs keep a link to their parent DIR object
    self.mydir = mydir

    #construct my FILE object from os.DirEntry object (but retain that as well)
    self.mydirentry = os_direntry
      ##for DEBUG ?
    
    ##GUIDELINES:
    ##  ! all my COLUMN DATA must have the col_... Prefix
    ##    this is how they will be found by getCellValue
    ##  * COLUMN DATA can be complex (CellObject)
    ##    or simple types that need a CellObjectProxy later
    ##  * COLUMN DATA for FILES must be complete,
    ##    DIR or OTHER may leave gaps where None is returned
    
    #first: for everyone files/dirs/other
    self.col_name = fname = os_direntry.name
      ##CAREFUL: this is not a column name
      ##  but this file's value for the column with the name "name"
    
    #all entries accept markers [x] but DIRs and Special won't do anything with them
    self.col_mark = False
      ##LATER we could easily store UNDO data in self.col_lastmark
    
    #we start of with no OUTPUT stored, of course
    self.col_out = None
    
    #colour for the entire line, None normally
    line_colour = None
    
    if os_direntry.is_file():           #MAIN CONTENTS: Files
      self.col_ftype = 'F'
      self.col_extn  = os.path.splitext(fname)[1].lower()
      
      mystat = os_direntry.stat()
      self.col_bytes = mystat.st_size
      
      if fname==config.MYFILENAME_DATA: #how should we list our very own datafile ?
        ##TS1..TS5: NO STAMPS FOR THIS FILE
        
        #same colour as very special 'x' files
        line_colour = TYP_COLOURMAP['x']
        
        self.col_rawhours = None
        self.col_isdst = None
        
        self.assertAllCellValues(ismyfile=True)
          #ismyfile=True: special case: do not assert but fill the gaps
      
      else:                             #all other files
        #----- TIMESTAMP(s) 1: LINUX -----
        #even THE FIRST TIMESTAMP start off with 4 possible columns
        #  * SOURCE: mtime or ctime (for test purposes)
        #  * TIMEZONE: Local or GMT (for test purposes)
        
          ##ATTENTION, CellObjectStamp need to know the filepath
          ##  for Updates to the STAT data !
        self.col_ts1_modloc = CellObjectStampLocal(os_direntry.path, "st_mtime", mystat.st_mtime)     #<=MAIN COLUMN
        self.col_ts1_modgmt = CellObjectStampGmt  (os_direntry.path, "st_mtime", mystat.st_mtime)
        self.col_ts1_crtloc = CellObjectStampLocal(os_direntry.path, "st_ctime", mystat.st_ctime)
        self.col_ts1_crtgmt = CellObjectStampGmt  (os_direntry.path, "st_ctime", mystat.st_ctime)
        
          ##for DEBUG: <hours> value raw from st_mtime without any conversion
        self.col_rawhours = (int(mystat.st_mtime) // 3600) % 24
          ##for DEBUG: <dst> value from time.localtime
        self.col_isdst = self.col_ts1_modloc.transferGet().tm_isdst
        
        #----- TIMESTAMP(s) 2: LINUX -----
        self.col_ts2_linux = self.col_ts1_modloc
          ##CAN often just use TS1 PYTHON:
          ##  1.if running UNIX: always
          ##  2.on Windows: for NTFS
        
        if RUNNING_WIN:
          if not mydir.fsutc:
            self.col_ts2_linux = CellObjectStampLinux(mydir.fsutc, self.col_ts1_modloc)
            ##only FAT running on WIN need to be wrapped,
            ##localtime in TS1 is still the base
        
        else:           #running on Linux this is exactly TS1,mtime,local
          self.col_ts2_linux = self.col_ts1_modloc
        
        #----- TIMESTAMP(s) 3: WINDOWS -----
        self.col_ts3_winold = CellObjectStampWin.MakeStampWinWrapper(mydir.fsutc,mydir.dstnow, False, self.col_ts1_modgmt, self.col_ts1_modloc)
        self.col_ts3_winnew = CellObjectStampWin.MakeStampWinWrapper(mydir.fsutc,mydir.dstnow, True,  self.col_ts1_modgmt, self.col_ts1_modloc)
        
        #----- TIMESTAMP 4: FILE NAME -----
        #try to find a timestamp in the filename...
        try:
          self.col_ts4_fname = CellObjectStampFname(fname)
        
        #there is a particular ValueError that means: no timestamp found, use DUMMY
        except ValueError as ex:
          if ex.args != ('NO-TIMESTAMP',): raise
          self.col_ts4_fname = CODummyFileTime
        
        #----- TIMESTAMP 5: PRIVATE DATA FILE -----
        
        #ask MY DIRECTORY if there were stampdata in the private file for me
        #  this would still be in string format according to config
        
        ##try:            datafilestamp = self.mydir.mydatafile_dict[fname]
        ##except KeyError:self.col_ts5_datafile = CODummyFileTime
        ##else:           self.col_ts5_datafile = CellObjectStampDatafile(datafilestamp)
        ##  ! NO CODummyFileTime allowed in this column !
        ##    transferSet needs a proper CellObjectStampDatafile
        
        datafilestamp = self.mydir.mydatafile_dict.get(fname, None)
        self.col_ts5_datafile = CellObjectStampDatafile(datafilestamp)
          #if no data => construct in DUMMY MODE
          #  (displayed like a dummy, but takes transferSet input)
        
        self.assertAllCellValues()      #assert that I have all required values
    
    else:                               #other Contents: Subdirs and Other (Sockets, Devices...)
      self.col_ftype = 'D' if os_direntry.is_dir() else 'x'
        #DIRECTORY or 'x' for UNKNOWN, this will sort to the end ;-)
      
      line_colour = TYP_COLOURMAP[self.col_ftype]
      
      ##self.col_bytes = None           getCellValue returns None, than handled by the proxy
      
      #NO self.assertAllCellValues(): non-files do not provide the full list of columns,
      #  None will be returned where missing
    
    self.line_colour = CellObject.colourMaker(line_colour) if line_colour else None
  
  def __repr__(self):
    return "<%s object: %s '%s' ...>" % (self.__class__.__name__, self.col_ftype,self.col_name)

  def assertAllCellValues(self, ismyfile=False):
    if ismyfile:        #SPECIAL for my private file: fill all timestamps with dummies
      #without checking "missing", they are missing anyway
      for stamp in self.allstampnames:
        #for Timestamps 1..4, link the Dummy
        setattr(self,stamp,CODummyFileTime)
    
    #list of all colnames from my dir => anybody missing here ?
    missing = [ colname for colname in self.allcolnames if not hasattr(self,colname) ]
    
    #NORMAL: assertion
    assert not missing, "FileData object '%s' is missing columns: %s" % (self.col_name, ",".join(missing))
  
  def _getCellValueCol(self, colname):
    #the name of the column (eg. bytes) is the lookup for my attribute (col_bytes)
    try: 
      return getattr(self, colname)
    except AttributeError:
      if self.col_ftype=='F':
        #FILES must be complete
        raise AssertionError("FileData object '%s' is missing column '%s'" % (self.col_name, colname))
      else:
        #but not DIRS and OTHER
        return None

  def getCellValue(self, colname):
    #tiny wrapper we need the internal variation where col_ is already present
    return self._getCellValueCol("col_"+colname)

  #convenience: direct access to the main columns/cells
  def getMark(self): return self.col_mark
  def getType(self): return self.col_ftype
  def getName(self): return self.col_name
  
  def ChangeMark(self, markmode):
    if markmode==-1:    #-1 is toggle
      self.col_mark = not self.col_mark
    else:               #set from 0 or 1
      self.col_mark = bool(markmode)
  
  def SetOutput(self, output): self.col_out = output
  
  def DelOutputs(self):
    """kill Output data: output column and colours set in timestamps"""
    if self.col_ftype!='F': return
    
    self.SetOutput(None)
    
    for colname in self.allstampnames:
      stampobj = self._getCellValueCol(colname)
      stampobj.setActionColour(None)
  
  #special access to give Timestamp4 "PRIVATE DATA FILE" to the directory when saving
  def getTs5DatafileStamp(self):
    if self.col_ftype!='F': return None
    return self.col_ts5_datafile.getDatafileString()
  
  #-------------------------------------------------
  #[THE REAL] ACTIONS for THE MAIN FUNCTIONS

  def colourfulStampCompare(self, structtime1,structtime2):
    """the big Comparison Function for to structs: JUST HOW different are they ?
      returns (severity, colour, seconds)
    """
    
    FEWSECONDS_DELTA = 20
    
    #convert to datetime to use the modern delta functionality
    dt1 = datetime.datetime(*structtime1[:6])
    dt2 = datetime.datetime(*structtime2[:6])
    delta_dt  = dt1-dt2
    delta_sec = int( delta_dt.total_seconds() )
    
    def findSeverity():
      #"working value" for seconds where abstractions take place
      worksecs = delta_sec
      severity = None
      
      if worksecs==0: return "0:equal"          #fully equal
      
      #FAT 2s possible Second-delta and correction to apply for abstraction
      fat32delta = { 58:+2, 59:+1, 1:-1,  2:-2 }
      try:
        corr = fat32delta[ worksecs%60 ]        #is there a FAT32 2seconds delta ?
      except KeyError: pass
      else:
        worksecs += corr
        if worksecs==0: return "1:fat"          #FAT offset was enough
      
      #a few seconds difference ?
      #  ->no correction to apply, this does not work in combination with others
      if abs(worksecs) <= FEWSECONDS_DELTA:
        return "2:secs"                         #just a few seconds, the camera took a moment...
      
      #if MIN:SEC are Zero, handle a pure HOURs difference
      #  (after considering FAT corrections)
      if worksecs%3600 == 0:
        hourdelta = (abs(worksecs) // 3600)
        if hourdelta<=2:                        #2h is the maximum DST error (in weird platform combinations)
          return "3:dst"
        else:
          return "4:hours"
      
      #else any other difference
      else:
        return "5:diff"                         #hopeless, just different
    
    severity = findSeverity()
    colour   = self.myseveritycolours[severity]
    
    return (severity, colour, delta_sec)
  
  def ActionAnalyse(self, coldesc1,coldesc2):
    #ACTIONS work only on files
    if self.col_ftype!='F': return
    
    #get BOTH OBJECTS, both COLDESC are present, both COLS are required in the GUI
    stampobj1 = self.getCellValue(coldesc1.name)
    stampobj2 = self.getCellValue(coldesc2.name)
    
    ##NO, 'F'iles all have objects, Dirs and other are already excluded here
    ##.. #either column may be empty for this file
    ##.. if not stampobj1 or not stampobj2:
    ##..   return
    
    #now we can ask for structtime, Dummies will answer None
    structtime1 = stampobj1.transferGet()
    structtime2 = stampobj2.transferGet()
    
    #not all Timestamp Columns have values, may be empty/Dummy
    #so no way to compare then
    if not structtime1 or not structtime2:
      outtuple = None
      ##LATER: another colour (PURPLE ?) would be nice if only one is missing
      ##  but that is difficult for my brother Function COLOURISE
    
    #we have 2 STAMPS => the big comparison
    else:
      outtuple = self.colourfulStampCompare(structtime1,structtime2)
        #=>returns (severity, colour, seconds)
    
    ##DEBUG print ("@@out:=",outtuple)
    self.SetOutput(outtuple)

  def ActionColourise(self, coldesc1,coldesc2):
    #ACTIONS work only on files
    if self.col_ftype!='F': return
    
    #get FIRST OBJECT always, no second OBJ means colour all
      ##DOCU: for explanation of steps getCellValue -> transferGet() -> check None
      ##      see comments in ActionAnalyse above
    stampobj1 = self.getCellValue(coldesc1.name)
    structtime1 = stampobj1.transferGet()
    if not structtime1: return
      #nothing to Colourise if their is no Timestamp
      #in the BASE Column
    
    if coldesc2:                #just that ONE destination column
      stampobj2all = [ self.getCellValue(coldesc2.name) ]
    else:
      #all other Timestamps are destination (except coldesc1, the source)
      stampobj2all = [ self._getCellValueCol(colname) for colname in self.allstampnames if colname!=("col_"+coldesc1.name) ]
    
    for stampobj2 in stampobj2all:
      #ignore also if second column is a dummy/no timestamp
      structtime2 = stampobj2.transferGet()
      if not structtime2: continue
        ##LATER: another colour (PURPLE ?) would be nice but impossible on a Dummy
      
      #we have 2 STAMPS => the big comparison
      outtuple = self.colourfulStampCompare(structtime1,structtime2)
      ##DEBUG print ("@@out:=",outtuple)
        #=>returns (severity, colour, seconds)
      
      stampobj2.setActionColour( outtuple[1] )

  def ActionTransfer(self, coldesc1,coldesc2):
    #ACTIONS work only on files
    if self.col_ftype!='F': return
    
    #get BOTH OBJECTS, both COLDESC are present, both COLS are required in the GUI
    stampobj1 = self.getCellValue(coldesc1.name)
    stampobj2 = self.getCellValue(coldesc2.name)
    
    #now we can ask for structtime, Dummies might answer None here
    structtime1 = stampobj1.transferGet()
    #empty source is normal, ignored silently
    if not structtime1: return
    
    #no DUMMIES allowed in the TARGET COL, would raise NotImplementedError
    stampobj2.transferSet(structtime1)

class DirectoryData:
  """The DIRECTORY currently displayed in the main GRID
    does not need much functionality, 
    the main member is the list of entries (files/subdirs) therein.
    
    ! Currently used only only for a single object,
      the directory displayed in the main grid
    ! this is the MAIN DIRECTORY for grid display purposes,
      SUBDIRECTORIES therein are FileData objects
    """
  
  #a list of FileData objs that are the contents of the directory
  entries = None
  
  #data for the current sort order
  #  1.the name of the column (no real need)
  #  2.this column's proxy object
  sortname  = None
  sortproxy = None
  
  def __init__(self, AllColumnNames):
    #start with empty list, I will first learn of my directory
    #from a call to GotoDir
    self.dirpath = None
    self.entries = []
    FileData.SetAllColumnNames(AllColumnNames)
    
    #settings that are the same for all dir entries
    self.fsutc  = None          #is the filesystem in UTC ?
    self.dstnow = None          #are we on DST now ?
    
    #input about/from my data file
    self.has_mydatafile = False
    self.mydatafile_dict = None
  
  def ReadFromInifile(self, key, defvalue):
    #if we haven't read the distributed ini yet
    if self.inidict is None:
      self.inidict = {}
      dirpath = self.dirpath
      
      #find the ini file up the directory tree
      while True:
        inipath = os.path.join(dirpath, config.MYFILENAME_MEDIAPREFS)
        if os.path.isfile(inipath): break
        
        newdirpath = os.path.dirname(dirpath)
        if newdirpath==dirpath: return defvalue
          #we have reached root without finding anything (empty dict)
        
        dirpath = newdirpath
      
      #ini file found, read it
      with open(inipath,"rt") as inifile:
        for line in inifile:
          #strip spaces, ignore empty lines and comments
          line = line.strip()
          if not line: continue
          if line[0]=='#': continue
          
          key,value = line.split('=')
          self.inidict[key]=value
    
    #with the inidict ready, just get the value
    return self.inidict.get(key, defvalue)
  
  def GotoDir(self, dirpath):
    """Destroy the database and Reload from new directory"""
    
    #double check, can be an assert
    assert os.path.isdir(dirpath)
    self.dirpath = dirpath
    
      #are filesystem stamps in UTC or Local ? (might change with dir navigation)
      #set in INI Files throughout the filesystem (for documented reasons)
    self.inidict = None
    timestampmode = self.ReadFromInifile("timestampmode","utc")
    self.fsutc = timestampmode.lower()=="utc"
    
      #find out if we are on DST now, needs to be done
      #(will change twice a year if we are running then)
    self.dstnow = time.localtime().tm_isdst
    assert self.dstnow in [0,1], "time.localtime() needs to contain DST information, but is %r" % self.dstnow
    
    #the MAIN DIR Object handles my datafiles inside the dir
    self.readMyFile()
    
    ##LATER: possible optimisation
    ##  when Updating the list while staying in the same DIR very little 
    ##  may have changed, this should require less than a full reconstruction
    ##
    ##  - this would require storing the original os.DirEntry data
    ##    in all the FileData and a structure here indexing them by filename
    self.entries = []
    
    #GET ALL DIRECTORY CONTENTS, full os.stat for all entries
    with os.scandir(dirpath) as it:
      #list comprehension: every os.DirEntry object becomes a FileData object
      #  (the constructor will ask me for his entry in self.mydatafile_dict)
      self.entries = [FileData(self, entry) for entry in it]
  
  def ApplySort(self, sortname,sortproxy,sortreverse):
    #2.APPLY SORT ORDER
    self.sortname  = sortname           #keep it, just FYI
    
    def cellKeyFunction(entry):
      """Generic Key Function for sorting entries in this DIR
        iterates trough the entry(ies),
        gets column data from local variables"""
      
      #1.get cell value for the file
      cellvalue = entry.getCellValue(sortname)
      
      #2.get value to use as key
      if isinstance(cellvalue,CellObject):              #a)ask the CellObject
        return cellvalue.getSortKey()
      
      else:                                             #b)give the value to the column's proxyobj
        ##all columns have a proxyobj, as asserted on init
        return sortproxy.getSortKey(cellvalue)
    
    self.entries.sort(key=cellKeyFunction, reverse=sortreverse)

  #access self.entries without handing over the entire list
  def get_EntriesLen(self):     return len(self.entries)
  def get_Entry(self,idx):      return self.entries[idx]

  def get_EntriesIterAll(self):
    """NORMAL: Iterator for all entries"""
    return iter(self.entries)
  
  def get_EntriesIterPick(self, idxpick):
    """PICK: entries according as requested by list of idx"""
    return (self.entries[idx] for idx in idxpick)

  def get_EntriesIterMarked(self):
    """MARKED: only marked entries [x]"""
    return (entry for entry in self.entries if entry.getMark())
  
  def hasMarkedEntries(self):
    """predicate: does the DIR have any marked files at all ?"""
    for _ in self.get_EntriesIterMarked():
      return True               #yes, exit on the first hit
                                #  (this is not inefficient as get_EntriesIterMarked 
    return False                #   is a generator, and not a list)

  def countMarkedEntries(self):
    """3 numbers: marked files, marked anything and grand total ignoring marks"""
    numfile = nummark = 0
    
    for entry in self.get_EntriesIterMarked():
      nummark += 1
      if entry.getType()=='F': numfile += 1
    
    return (numfile, nummark, len(self.entries))

  #the main DIRECTORY handles my data file that may be there
  def readMyFile(self):
    self.mydatafile_dict = {}
    mydatafname = os.path.join(self.dirpath, config.MYFILENAME_DATA)
    exists = os.path.isfile(mydatafname)
    
    self.has_mydatafile = exists
    if exists:
      #read with newline=None: universal newlines are default in PY3,
      #  we always write \n but maybe a windows editor messed it up
      with open(mydatafname, "rt", encoding="utf8") as mydatafile:
        for line in mydatafile:
          line = line.strip()
          if not line: continue         #empty lines (from outside editing...)
          if line[0]=='#': continue     #ignore our comment, this is for different files formats in the future
          
          timestamp, filename = line.split('\t')
          
          #just store it and give it to the FileData objects later
          self.mydatafile_dict[filename] = timestamp
  
  def writeMyFile(self):
    ##NO NEED for the old self.mydatafile...
    
    mydatafname = os.path.join(self.dirpath, config.MYFILENAME_DATA)
    
    #1.sort a copy of my entries strictly according to filename/unicode/lower
    sortedentries = sorted( self.entries, key=lambda entry: entry.getName().lower() )
    
    #always write with UNIX line endings;
    #  Windows line endings are accepted but never written,
    #  this means less source code differences when crossing platforms
    with open(mydatafname, "wt", encoding="utf8", newline='\n') as mydatafile:
      #header comment, fixed to this version
      mydatafile.write("#timestamper data file, fileversion 0.1\n")
      
      for entry in sortedentries:
        #the STAMP that will be written to the file is exactly the TS5/stamp in datafile column
        stamp = entry.getTs5DatafileStamp()
        
        #Dummies and Stamp-Proxies will return None for "nothing"
        if stamp:
          line = "%s\t%s\n" % (stamp, entry.getName())
          mydatafile.write(line)
    
    self.has_mydatafile = "New"         #member not used yet
