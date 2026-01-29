##import ---

  #FILENAME: INI/RC File with Settings for timestamp handling
  #  in this region of the filesystem, should be anywhere
  #  in the tree all the way up to root '/'
MYFILENAME_MEDIAPREFS = ".timestamper.mediaprefs"

  #FILENAME: DATA FILE for permanently storing "freezing" timestamps for the files
  #  to be stored next to the files in every relevant directory
MYFILENAME_DATA = "timestamp-data.txt"

  #TIMESTAMP format for my data files ->MYFILENAME_DATA
  #  a Formatstring for datetime.strptime
  #  this is 'simplified' ISO without Timezone
DATA_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

  #desired GUI representation for all timestamps
  #  currently like DATA file format DATA_TIMESTAMP_FORMAT
GUI_TIMESTAMP_FORMAT = DATA_TIMESTAMP_FORMAT
##DEBUG: GUI_TIMESTAMP_FORMAT = "%H:%M"

  #dummy for columns where some files may not have stamps
  #(for class DummyFileNostamp)
GUI_TIMESTAMP_DUMMY = ""		#just empty.
  ##THINK TWICE before changing this, "empty" is quite useful
  ##  because the wx.Grid Widget has the same bindings
  ##  von Ctrl-Cursorkeys like Excel to jump to next full cell
#GUI_TIMESTAMP_DUMMY = "---"
#GUI_TIMESTAMP_DUMMY = "__-__-__ __:__:__"

  #desired GUI representation for Size in Bytes
  #  a format string for new style "FORMAT".format(value)
  #  this is with thousands separators 111,222,333
GUI_BYTES_FORMAT = "{:,}"
  #  ->will then be changed to '.'
GUI_BYTES_SEPARATOR = "."

  #COLOURS for special entries/columns...
GUI_COLOUR_DIR   = (255,236,145)	#Directory: yellowish, like Icon in Explorer
GUI_COLOUR_OTHER = (200,200,200)	#Other non-File: Grey

GUI_COLOUR_MARK  = (255,160,255)	#Marker Col: Pink

GUI_COLOUR_SEVERITIES = {
  "0:equal":    (160,255,160),	#GREEN
  "1:fat":      (160,255,255),	#CYAN
  "2:secs":     (225,255,160),	#GREEN-YELLOW
  "3:dst":      (255,255,160),	#YELLOW
  "4:hours":    (255,210,160),	#ORANGE
  "5:diff":     (255,170,170),	#RED
}
